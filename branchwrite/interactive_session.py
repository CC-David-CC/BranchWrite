"""One terminal worker composes the existing Interpreter, FrameKernel and COW.

Unsent input is durable before acknowledgement. The worker exclusively owns the
workflow. Presentation threads never execute tools or move native references.
File publication uses captured preimages and original operation identities.
"""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import threading
import uuid
from . import coding_cli
from .run_report import read_report, continuation_context, continuation_projection, initial_context
from .session_ledger import SessionLedger, Inbox
from .workspace_versions import WorkspaceVersions
from .session_controls import CONTROL_MODES, control_target, unfinished_task


def run_workflow(state, launch, connection, control, progress):
    coding_cli.save_launch(state, launch)
    _, result = coding_cli.run_saved(state, control=control, progress=progress, model_pause=control)
    report = read_report(state)
    # Refuse to publish a new continuation while any effect remains unresolved.
    projection = continuation_projection(state, connection)
    context = projection['context']
    status = ('finished' if report['status']=='finished' else
              'interrupted' if result['status']=='interrupted' else 'waiting')
    return dict(status=status, context=context, answer=report['answer'],
                checks_passed=report['checks_passed'], workspace=str(state/'world/workspace'),
                unfinished_request=not projection['contains_request'],exports=result.get('exports',[]))


class SessionService:
    def __init__(self, project, state, connection, *, runner=None,remotes=None,sampler="greedy",cad=None,blender=None):
        from .coding_defaults import generation_profile
        generation_profile(sampler)
        self.sampler=sampler
        if cad is not None and blender is not None:raise ValueError('choose one fixed domain per session')
        from .cad_config import validate_cad_config
        from .blender_tools import validate_blender_config
        self.cad=None if cad is None else deepcopy(validate_cad_config(cad))
        self.blender=None if blender is None else deepcopy(validate_blender_config(blender))
        from .remote_config import validate_targets
        self.remotes=validate_targets({} if remotes is None else remotes)
        self.project=Path(project).resolve(strict=True)
        self.state=Path(state).absolute();self.connection=dict(connection)
        if self.state.resolve().is_relative_to(self.project):
            raise ValueError('Session state must be outside the project')
        self.inbox=Inbox(self.state);self.runner=runner or run_workflow
        self._lock=threading.RLock();self._wake=threading.Event()
        self._thread=None;self._running=False;self._closing=False
        self._hold=False;self._interrupt=0;self._needs_recovery=False;self._worker_error=None
        self._snapshot=dict(status='starting',history=[],current={},needs_recovery=False)
        self._emit=lambda text:None
    @property
    def running(self):
        with self._lock:return self._running
    @property
    def snapshot(self):
        with self._lock:return deepcopy(self._snapshot)
    def start(self, emit):
        with self._lock:
            if self._thread is not None:raise ValueError('Session worker already started')
            self._emit=emit
            self._thread=threading.Thread(target=self._worker,name='branchwrite-session',daemon=False)
            self._thread.start()
    def submit(self, message, *, mode, kind):
        if mode not in ('work','plan','chat','aside','continue',*CONTROL_MODES):
            raise ValueError('This control is still being connected; your request was not sent')
        with self._lock:
            if self._closing:raise ValueError('Session is closing')
            if self._worker_error is not None:
                raise ValueError('Fix the session error, then reopen it: '+self._worker_error)
            if self._needs_recovery:
                if mode!='continue':raise ValueError('Recover the original operation with /continue before new work')
                self._hold=False;self._wake.set();return 'recover-original-operation'
            if mode=='continue':
                if self._running:raise ValueError('The current turn is already working')
                current=self._snapshot['current'].get('turn')
                previous=next((row for row in self._snapshot['history'] if row['id']==current),None)
                if previous is None or (previous.get('result') or {}).get('status') not in ('interrupted','waiting'):
                    raise ValueError('There is no paused workflow to continue')
                if any(row['mode']=='continue' for row in self.inbox.rows()):
                    raise ValueError('A continuation is already queued')
            target={}
            if mode in CONTROL_MODES:
                if self._running or self.inbox.rows():
                    raise ValueError('Stop current work and let it settle before changing saved versions')
                row,_=control_target(self._snapshot['history'],message,mode)
                target['target']=row['id']
            identity='input-'+uuid.uuid4().hex
            self.inbox.put(identity,message,mode=mode,kind=kind,**target)
            if kind=='steer':self._interrupt+=1
            if mode=='continue' or kind!='queue' or not self._hold:self._hold=False
            self._wake.set()
            return identity
    def stop(self):
        with self._lock:
            self._interrupt+=1;self._hold=True;self._wake.set()
    def close(self):
        with self._lock:
            if self._closing:return
            self._closing=True;self._interrupt+=1;self._wake.set()
        if self._thread is not None:self._thread.join()
    def _refresh(self, ledger, status):
        view=dict(status=status,history=ledger.history(),current=ledger.current(),
                  needs_recovery=self._needs_recovery)
        with self._lock:self._snapshot=view
    def _worker(self):
        try:
            with SessionLedger(self.project,self.state,self.connection) as ledger:
                versions=WorkspaceVersions(self.project,self.state/'files')
                if ledger.pending() is not None:
                    with self._lock:self._hold=True;self._needs_recovery=True
                    self._emit('An earlier turn is unsettled. /continue reconciles its original saved work.')
                self._refresh(ledger,'recovery needed' if self._needs_recovery else 'ready')
                while True:
                    self._wake.wait(.25);self._wake.clear()
                    with self._lock:
                        if self._closing:return
                        if self._hold:continue
                        ticket=self._interrupt
                        turn=ledger.pending() or ledger.admit()
                        if turn is None:continue
                        self._running=True
                    self._refresh(ledger,'working')
                    try:
                        result=self._turn(ledger,versions,turn,
                            lambda:self._closing or self._interrupt!=ticket)
                        ledger.finish(turn['id'],result)
                        with self._lock:self._needs_recovery=False
                        if result.get('answer'):self._emit(result['answer'])
                        if result.get('action')=='select':pass
                        elif result['status']=='finished' and result['mode'] in ('plan','chat','aside'):
                            self._emit('Read-only turn saved; project files were unchanged.')
                        elif result['status']=='finished':
                            self._emit('Chosen checks passed; review the result.' if result.get('checks_passed') else 'The turn ended; its checks have not established success.')
                        else:self._emit('Saved at a safe boundary. /continue resumes this workflow, or send a new request.')
                        for item in result.get('exports',[]):
                            self._emit('Saved output '+item['name']+': '+item['path'])
                        if result.get('paths'):
                            self._emit('Updated in '+result['workdir']+': '+', '.join(result['paths']))
                    except Exception as error:
                        # Preserve the admitted frame and original launch. A UI
                        # retry cannot invent a new model/tool operation identity.
                        with self._lock:self._hold=True;self._needs_recovery=True
                        self._emit('Needs recovery: '+str(error)+'. Original work is retained; /continue retries its recorded boundary.')
                    finally:
                        with self._lock:self._running=False
                        self._refresh(ledger,'recovery needed' if self._needs_recovery else 'paused' if self._hold else 'ready')
                    self._wake.set()
        except Exception as error:
            with self._lock:
                self._running=False;self._hold=True;self._needs_recovery=True
                self._worker_error=str(error)
                self._snapshot.update(status='Could not open session: '+str(error),needs_recovery=True)
            self._emit(self._snapshot['status'])
    def _progress(self,event):
        from .tool_progress import detail_message
        detail=detail_message(event)
        if detail is not None:
            self._emit(detail);return
        messages={'model_started':'Thinking about the next step...',
            'model_step_returned':'Model step saved.',
            'tool_returned':'Tool result saved.'}
        if event.startswith('pause:'):self._emit(event[len('pause:'):])
        elif event in messages:self._emit(messages[event])
    def _capture(self, versions, name, *, context, parent, source, workflow=None):
        saved=versions.named(name)
        if saved is not None:return saved
        return versions.capture(name,context=context,parent=parent,source=source,workflow=workflow)['commit']
    def _select(self, ledger, versions, turn, target):
        identity=turn['id'];source=turn['input']['source'];selected=target['result']
        before=self._capture(versions,'pre-'+identity,context=source['context'],
            parent=source['file_commit'],source=Path(source['workdir']),workflow={'turn':identity})
        destination=Path(selected['workdir'])
        # Use the last known files for this destination as the guarded preimage.
        # Unrelated new files remain untouched; conflicting user edits are retained.
        latest=next((row['result'] for row in reversed(ledger.history())
            if row.get('result') and row['input']['mode']!='aside'
            and row['result'].get('workdir')==str(destination)
            and row['result'].get('file_commit')),selected)
        self._capture(versions,'observed-'+identity,context=latest['context'],
            parent=latest['file_commit'],source=destination)
        receipt=versions.publish('select-'+identity,latest['file_commit'],selected['file_commit'],target=destination)
        return dict(status='finished',context=selected['context'],file_commit=selected['file_commit'],
            workdir=str(destination),mode=selected['mode'],before=before,workflow=None,
            exports=selected.get('exports',[]),action='select',answer='Selected saved turn '+target['id']+' in '+str(destination)+'.',
            checks_passed=None,paths=receipt['intent']['paths'],acceptance='not_independently_established')
    def _turn(self, ledger, versions, turn, control):
        identity=turn['id'];data=turn['input'];source=data['source'];mode=data['mode']
        workdir=Path(source['workdir']);context=source['context'];task=data['message']
        if mode in ('work','plan','chat'):
            task=unfinished_task(ledger.history(),source,task)
        target=None
        if mode in CONTROL_MODES:
            target,task=control_target(ledger.history(),task,mode,pinned=data['target'])
            if mode=='select':return self._select(ledger,versions,turn,target)
        if mode=='continue':
            previous=next((row for row in ledger.history() if row['id']==source['turn']),None)
            if previous is None or previous['result']['status'] not in ('interrupted','waiting'):
                raise ValueError('There is no paused workflow to continue')
            original=previous['result'];runstate=Path(original['workflow'])
            before=original['file_commit'];publication_before=before;mode=original['mode']
            launch=coding_cli.read_launch(runstate)
        else:
            if mode in ('edit','explore'):
                observed=self._capture(versions,'observed-'+identity,context=context,
                    parent=source['file_commit'],source=workdir)
                selected=target['result']
                if mode=='edit':
                    before=selected['before'];context=versions.read(before)['context']
                    original=Path(selected['workflow'])
                    if context is None and (original/'ledger/events.bwl').exists():
                        context=initial_context(original,self.connection)
                        if context is not None:
                            basis=self.state/'bases'/identity;basis.parent.mkdir(mode=0o700,exist_ok=True)
                            versions.explore('edit-base-'+identity,context_commit=before,files_commit=before,destination=basis)
                            before=self._capture(versions,'pre-'+identity,context=context,parent=before,
                                source=basis,workflow={'turn':identity})
                    publication_before=source['file_commit']
                else:
                    workdir=self.state/'alternatives'/identity
                    workdir.parent.mkdir(mode=0o700,exist_ok=True)
                    versions.explore('alternative-'+identity,context_commit=selected['file_commit'],
                        files_commit=observed,destination=workdir)
                    context=selected['context']
                    before=self._capture(versions,'pre-'+identity,context=context,
                        parent=observed,source=workdir,workflow={'turn':identity})
                    publication_before=before
                mode='work'
            else:
                before=self._capture(versions,'pre-'+identity,context=context,
                    parent=source['file_commit'],source=workdir,workflow={'turn':identity})
                publication_before=before
            frozen=self.state/'inputs'/identity;frozen.parent.mkdir(mode=0o700,exist_ok=True)
            versions.explore('input-'+identity,context_commit=before,files_commit=before,destination=frozen)
            runstate=self.state/'turns'/identity;runstate.parent.mkdir(mode=0o700,exist_ok=True)
            runstate.mkdir(mode=0o700,exist_ok=True)
            if (runstate/'coding-launch.json').exists():launch=coding_cli.read_launch(runstate)
            else:
                manifest=versions.read(before)
                inventory=[dict(path=path,sha256=value['sha256']) for path,value in list(manifest['files'].items())[:128]]
                facts=('The current files are a fresh snapshot. Older context may describe older versions. '
                       'Read relevant files again before editing. Current file inventory (at most 128 shown): '+json.dumps(inventory)+'\n\n')
                origin={}
                if context is not None:
                    origin['from_prefix' if context.get('mode')=='ask' else 'from_branch']=context['branch']
                    origin['from_snapshot']=context['tip']
                branch='bw-session-'+sha256((str(self.state)+identity).encode()).hexdigest()[:40]
                launch=coding_cli.build_launch(frozen,facts+task,self.connection,
                    branch=branch,project_files=mode=='work',mode=mode,remotes=self.remotes,sampler=self.sampler,
                    cad=self.cad if mode=='work' else None,blender=self.blender if mode=='work' else None,**origin)
                coding_cli.save_launch(runstate,launch)
        after=versions.named('post-'+identity)
        if after is None:
            result=self.runner(runstate,launch,self.connection,control,self._progress)
            context=result['context']
            after=versions.capture('post-'+identity,context=context,parent=before,
                source=Path(result['workspace']),workflow=dict(state=str(runstate),status=result['status'],
                    answer=result.get('answer'),checks_passed=result.get('checks_passed'),
                    unfinished_request=result.get('unfinished_request'),exports=result.get('exports',[])))['commit']
        saved=versions.read(after);facts=saved['workflow'];context=saved['context']
        paths=[]
        if mode=='work':
            receipt=versions.publish('publish-'+identity,publication_before,after,target=workdir)
            paths=receipt['intent']['paths']
        elif saved['files']!=versions.read(before)['files']:
            raise ValueError('Read-only turn changed its files; nothing was published')
        return dict(status=facts['status'],context=context,file_commit=after,workdir=str(workdir),
            unfinished_request=facts.get('unfinished_request'),
            mode=mode,before=before,workflow=str(runstate),answer=facts['answer'],action=data['mode'],
            checks_passed=facts['checks_passed'],paths=paths,exports=facts.get('exports',[]),
            acceptance='not_independently_established')
