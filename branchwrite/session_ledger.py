"""Interactive intents on FrameKernel; native conversation remains in COW.

The inbox contains unsent UI input only. Once admitted, its original bytes and
source references live in the existing canonical runtime record. UI threads
never mutate that record. One worker owns it and delegates each coding turn to
the existing Interpreter; uncertain calls retain their IDs across restart.
"""
from contextlib import contextmanager
from hashlib import sha256
import fcntl
import os
from pathlib import Path
import re
import stat
from .kernel import FrameKernel, CallSpec, ResultContract
from .records import RuntimeLog, Artifact, encode, decode
from .workspace_versions import _save, _load

_MODES = {"work", "plan", "chat", "aside", "edit", "explore", "select", "continue"}
_KINDS = {"send", "steer", "queue"}
_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,127}\Z")

class Inbox:
    def __init__(self, state):
        self.state=Path(state).absolute();self.state.mkdir(parents=True,exist_ok=True,mode=0o700)
        info=self.state.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode & 0o077:
            raise ValueError("session must be a private owned directory")
        self.path=self.state/'inbox.json'
    @contextmanager
    def locked(self):
        fd=os.open(self.state/'inbox.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'rb+') as stream:
            info=os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or info.st_nlink!=1:
                raise ValueError("invalid inbox lock")
            fcntl.flock(stream.fileno(),fcntl.LOCK_EX);yield
    def _rows(self):
        if not self.path.exists():return []
        rows=_load(self.path)
        if type(rows) is not list or len(rows)>256:raise ValueError("invalid inbox")
        for row in rows:self._validate(row)
        if len({r['id'] for r in rows})!=len(rows):raise ValueError("duplicate inbox identity")
        return rows
    @staticmethod
    def _validate(row):
        if type(row) is not dict or set(row) not in ({'id','message','mode','kind'}, {'id','message','mode','kind','target'}):
            raise ValueError("invalid inbox item")
        if type(row['id']) is not str or not _NAME.fullmatch(row['id']):raise ValueError("invalid input identity")
        if row['mode'] not in _MODES or row['kind'] not in _KINDS:raise ValueError("unknown session mode or input kind")
        if type(row['message']) is not str or not row['message'].strip() or len(row['message'].encode())>262144:
            raise ValueError("nonempty input up to 256 KiB required")
        from .session_controls import CONTROL_MODES
        if row['mode'] in CONTROL_MODES:
            if type(row.get('target')) is not str or not _NAME.fullmatch(row['target']):
                raise ValueError("saved control target must be pinned before admission")
        elif 'target' in row:raise ValueError("only branch controls accept a saved target")
    def rows(self):
        with self.locked():return self._rows()
    def put(self, identity, message, *, mode, kind, target=None):
        row=dict(id=identity,message=message,mode=mode,kind=kind)
        if target is not None:row['target']=target
        self._validate(row)
        with self.locked():
            rows=self._rows()
            existing=next((v for v in rows if v['id']==identity),None)
            if existing is not None:
                if existing!=row:raise ValueError("input ID belongs to different work")
                return row
            if len(rows)>=256 or sum(len(r['message'].encode()) for r in rows)+len(message.encode())>1048576:
                raise ValueError("queued input capacity reached; current drafts are retained")
            _save(self.path,[*rows,row])
        return row

class SessionLedger:
    def __init__(self,project,state,connection):
        self.project=Path(project).resolve(strict=True);self.state=Path(state).absolute()
        self.inbox=Inbox(self.state);self.connection=dict(connection)
    def __enter__(self):
        self.log=RuntimeLog(self.state/'ledger');self.log.__enter__()
        try:
            self.kernel=FrameKernel(self.log)
            identity=dict(schema=1,project=str(self.project),connection=self.connection)
            definition=self.log.put_artifact(b'branchwrite.interactive-session.v1')
            inputs=self.log.put_artifact(encode(identity))
            if self.kernel.frames():
                root=self.kernel.frame('session')
                if root['definition']!=(definition.sha256,definition.size_bytes) or root['inputs']!=(inputs.sha256,inputs.size_bytes):
                    raise ValueError("session belongs to a different project or connection")
            else:self.kernel.create_root('session','session-attempt',definition,inputs,ResultContract('SessionResult','record'))
            self._join();self._discard_admitted()
            return self
        except BaseException:
            self.log.__exit__(None,None,None);raise
    def __exit__(self,*args):return self.log.__exit__(*args)
    def _input(self,frame):return decode(self.log.read_artifact(Artifact(*frame['inputs'])))
    def _result(self,frame):return decode(self.log.read_artifact(Artifact(*frame['result'])))[2]
    def _turns(self):return sorted((f for f in self.kernel.frames() if f['parent']=='session'),key=lambda f:f['parent_epoch'])
    def _join(self):
        root=self.kernel.frame('session')
        if root['state']=='Waiting':
            current=[f for f in self._turns() if f['parent_epoch']==root['epoch']]
            if current and all(f['state']=='Closed' for f in current):self.kernel.resume('session',root['epoch'])
    def _discard_admitted(self):
        admitted={row['id']:row for frame in self._turns() for row in self._input(frame)['items']}
        with self.inbox.locked():
            rows=self.inbox._rows()
            for row in rows:
                if row['id'] in admitted and row!=admitted[row['id']]:raise ValueError("queued identity differs from admitted input")
            keep=[r for r in rows if r['id'] not in admitted]
            if keep!=rows:_save(self.inbox.path,keep)
    def pending(self):
        self._join()
        frames=[f for f in self._turns() if f['state']!='Closed']
        if not frames:return None
        if len(frames)!=1:raise ValueError("multiple active turns in serial session")
        frame=frames[0]
        if frame['dispatch'] is None:
            self.kernel.dispatch(frame['id'],'effect-'+frame['id'],Artifact(*frame['inputs']))
        return dict(id=frame['id'],input=self._input(frame))
    def admit(self):
        self._join();self._discard_admitted()
        if self.pending() is not None:raise ValueError("session has a pending turn; recover it first")
        rows=self.inbox.rows()
        if not rows:return None
        selected=[];size=0
        for row in rows:
            if row['mode']!=rows[0]['mode']:break
            if selected and rows[0]['mode'] not in ('work','plan','chat'):break
            added=len(row['message'].encode())+(2 if selected else 0)
            if size+added>262144:break
            selected.append(row);size+=added
        data=dict(schema=1,mode=selected[0]['mode'],message='\n\n'.join(row['message'] for row in selected),
            item_ids=[row['id'] for row in selected],items=selected,source=self.current())
        if 'target' in selected[0]:
            from .session_controls import control_target
            control_target(self.history(),data['message'],data['mode'],pinned=selected[0]['target'])
            data['target']=selected[0]['target']
        root=self.kernel.frame('session');epoch=root['epoch']+1
        identifier='turn-'+str(epoch)+'-'+sha256(encode(data)).hexdigest()[:16]
        inputs=self.log.put_artifact(encode(data));definition=self.log.put_artifact(b'bw.interactive-turn.v1')
        self.kernel.spawn('session',expected_epoch=root['epoch'],calls=(CallSpec(identifier,'attempt-'+identifier,
            'turn','FLOW',definition,inputs,ResultContract('InteractiveTurnResult','record')),),next_pc=epoch)
        self._discard_admitted()
        return self.pending()
    def finish(self,identifier,result):
        frame=self.kernel.frame(identifier)
        if frame['parent']!='session':raise ValueError("not a session turn")
        if type(result) is not dict or result.get('status') not in ('finished','interrupted','blocked','failed','waiting'):
            raise ValueError("explicit turn disposition required")
        self.kernel.record_result(identifier,'effect-'+identifier,result)
        self._join()
    def current(self):
        current=dict(context=None,file_commit=None,workdir=str(self.project),mode='work',turn=None)
        root=self.kernel.frame('session')
        for frame in self._turns():
            if frame['state']!='Closed' or frame['parent_epoch']>root['pc']:continue
            if self._input(frame)['mode']=='aside':continue
            result=self._result(frame)
            for key in ('context','file_commit','workdir','mode'):
                if key in result:current[key]=result[key]
            current['turn']=frame['id']
        return current
    def history(self):
        return [dict(id=f['id'],input=self._input(f),result=None if f['state']!='Closed' else self._result(f)) for f in self._turns()]
    def search(self,text):
        if type(text) is not str:raise ValueError("search text required")
        needle=text.casefold()
        return [row for row in self.history() if needle in row['input']['message'].casefold()]
