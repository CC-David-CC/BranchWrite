"""Bounded private command outputs;the existing RuntimeLog owns their receipts.

Only explicit leaves can be published after namespace retirement. This module
does not schedule commands,define model actions,or create another workflow log.
"""
import base64,hashlib,os,stat
from pathlib import Path,PurePosixPath
from .execution import Grant,ToolRejected,_relative_path,_MAX_FILE_BYTES

OUTPUT_LIMIT=8*1024**2
OUTPUT_FILES=64

def validate_paths(paths,read_paths):
    if (type(paths) is not tuple or not 1<=len(paths)<=OUTPUT_FILES
            or len(set(paths))!=len(paths) or sum(len(v.encode()) for v in paths)>16384):
        raise ToolRejected("bounded unique command-output paths required")
    for path in paths:
        _relative_path(path)
        if path not in read_paths:raise ToolRejected("outputs require readback grants")
        if any(other!=path and PurePosixPath(other).is_relative_to(path) for other in paths):
            raise ToolRejected("output leaves cannot be each other's parents")

def roots(paths):
    parents=sorted({str(PurePosixPath(p).parent) for p in paths},key=lambda p:(len(PurePosixPath(p).parts),p))
    result=[]
    for parent in parents:
        if not any(root=='.' or PurePosixPath(parent).is_relative_to(root) for root in result):
            result.append(parent)
    return tuple(result)

def initial_state(executor,paths):
    rows=[]
    for path in paths:
        try:
            target=executor._workspace_file(path);info=target.stat(follow_symlinks=False)
        except FileNotFoundError:
            rows.append((path,None,None));continue
        body=executor._read_private_bytes(path)
        rows.append((path,hashlib.sha256(body).hexdigest(),stat.S_IMODE(info.st_mode)))
    return tuple(rows)

def configure_namespace(argv,projection,workspace,paths):
    """Overlay private tmpfs parents,then pin other inputs read-only again."""
    groups=roots(paths);base={}
    for group in groups:
        total=sum((projection/p).stat().st_size for p in paths
            if (group=='.' or PurePosixPath(p).is_relative_to(group)) and (projection/p).is_file())
        base[group]=max(65536,((total+65536+4095)//4096)*4096)
    if sum(base.values())>OUTPUT_LIMIT:raise ToolRejected("initial outputs exceed private output capacity")
    share=((OUTPUT_LIMIT-sum(base.values()))//len(groups)//4096)*4096
    argv+=['--ro-bind',str(projection),'/bw-input']
    for group in groups:
        destination=projection/group;destination.mkdir(parents=True,exist_ok=True)
        argv+=['--size',str(base[group]+share),'--tmpfs',str(workspace/group)]
        directories={str(PurePosixPath(p).parent) for p in paths
            if group=='.' or PurePosixPath(p).is_relative_to(group)}
        protected=[]
        for file in projection.rglob('*'):
            relative=file.relative_to(projection).as_posix()
            if file.is_file() and relative not in paths and (group=='.' or PurePosixPath(relative).is_relative_to(group)):
                protected.append(relative);directories.add(str(PurePosixPath(relative).parent))
        for folder in sorted(directories,key=lambda p:len(PurePosixPath(p).parts)):
            argv+=['--dir',str(workspace/folder)]
        for relative in protected:
            argv+=['--ro-bind',str(projection/relative),str(workspace/relative)]
    return {group:base[group]+share for group in groups}

def initialize_private(paths):
    source=Path('/bw-input');workspace=Path.cwd()
    for path in paths:
        original=source/path
        if original.exists():
            info=original.stat(follow_symlinks=False)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1:raise ValueError("unsafe initial output")
            body=original.read_bytes()
            if len(body)>_MAX_FILE_BYTES:raise ValueError("initial output exceeds file bound")
            target=workspace/path;target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(body);target.chmod(stat.S_IMODE(info.st_mode)&0o777)

    directories={'.'}
    for path in paths:
        directories.update(str(parent) for parent in PurePosixPath(path).parents)
    for original in source.rglob('*'):
        if original.is_file():
            directories.update(str(parent) for parent in PurePosixPath(original.relative_to(source).as_posix()).parents)
    return {directory:stat.S_IMODE((workspace/directory).lstat().st_mode) for directory in directories}

def _live_children():
    # Observation only:never signal a host/global PID from the worker.
    ancestors={os.getpid()};current=os.getpid()
    while current>1:
        try:parent=int(Path('/proc',str(current),'stat').read_text().rsplit(')',1)[1].split()[1])
        except (FileNotFoundError,ValueError):break
        if parent in ancestors:break
        ancestors.add(parent);current=parent
    result=[]
    for entry in Path('/proc').iterdir():
        if entry.name.isdecimal() and int(entry.name)>1 and int(entry.name) not in ancestors:
            try:
                state=(entry/'stat').read_text().rsplit(')',1)[1].split()[0]
                if state not in ('Z','X'):result.append(int(entry.name))
            except FileNotFoundError:pass
    return result

def collect_private(paths,directory_modes):
    """Capture a stable private result;host publishes only after worker retirement."""
    if _live_children():raise ValueError("command descendants remain at output capture")
    source=Path('/bw-input');workspace=Path.cwd();allowed=set(paths)
    for directory,mode in directory_modes.items():
        info=(workspace/directory).lstat()
        if not stat.S_ISDIR(info.st_mode) or stat.S_IMODE(info.st_mode)!=mode:
            raise ValueError("command changed output-directory permissions or type")

    protected={p.relative_to(source).as_posix() for p in source.rglob('*') if p.is_file()}-allowed
    directories={'.'}
    for path in allowed|protected:
        directories.update(str(p) for p in PurePosixPath(path).parents)
    seen=0
    for group in roots(paths):
        for directory,folders,files in os.walk(workspace/group,followlinks=False,onerror=lambda error:(_ for _ in ()).throw(error)):
            for name in folders+files:
                seen+=1
                if seen>20064:raise ValueError("command output entry bound exceeded")
                p=Path(directory)/name;relative=p.relative_to(workspace).as_posix();info=p.lstat()
                if stat.S_ISDIR(info.st_mode):
                    if relative not in directories:raise ValueError("unexpected output directory")
                elif not stat.S_ISREG(info.st_mode) or info.st_nlink!=1:
                    raise ValueError("output links or special files rejected")
                elif relative not in allowed and relative not in protected:
                    raise ValueError("command produced an undeclared output")
    for path in protected:
        old=source/path;actual=workspace/path
        if actual.read_bytes()!=old.read_bytes() or stat.S_IMODE(actual.stat().st_mode)!=stat.S_IMODE(old.stat().st_mode):
            raise ValueError("protected input changed in command view")
    rows=[];total=0
    for path in paths:
        p=workspace/path
        if not p.exists():
            if (source/path).exists():
                rows.append(dict(path=path,deleted=True,bytes=0,data=None,sha256=None,mode=None))
            continue
        before=p.lstat()
        if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or before.st_size>_MAX_FILE_BYTES:
            raise ValueError("output is not a bounded private regular file")
        with p.open('rb') as f:body=f.read(_MAX_FILE_BYTES+1);after=os.fstat(f.fileno())
        keys=('st_dev','st_ino','st_size','st_mtime_ns','st_ctime_ns','st_mode','st_nlink')
        if len(body)!=before.st_size or any(getattr(before,k)!=getattr(after,k) for k in keys):
            raise ValueError("output changed during capture")
        total+=len(body)
        if total>OUTPUT_LIMIT:raise ValueError("command output byte bound exceeded")
        rows.append(dict(path=path,deleted=False,bytes=len(body),data=base64.b64encode(body).decode(),
            sha256=hashlib.sha256(body).hexdigest(),mode=format(stat.S_IMODE(before.st_mode),'04o')))
    return rows

def publish(executor,paths,before,rows,operation_id):
    """Validate all payloads/preimages,then reuse existing granted file mutations.

    There is no atomic multi-file transaction. Failure after a mutation remains
    indeterminate in ToolRegistry;the original operation must not be resent.
    """
    if type(rows) is not list or len(rows)>len(paths):raise ValueError("invalid output receipt list")
    decoded=[];seen=set();total=0
    for row in rows:
        if type(row) is not dict or set(row)!={'path','deleted','bytes','data','sha256','mode'}:
            raise ValueError("invalid output receipt fields")
        path=row['path']
        if path not in paths or path in seen or type(row['deleted']) is not bool or type(row['bytes']) is not int:
            raise ValueError("output receipt exceeds grant")
        seen.add(path)
        if row['deleted']:
            if (row['bytes'],row['data'],row['sha256'],row['mode'])!=(0,None,None,None):
                raise ValueError("invalid deleted-output receipt")
            decoded.append((row,None));continue
        mode=row['mode']
        if (type(mode) is not str or len(mode)!=4 or mode[0]!='0'
                or any(c not in '01234567' for c in mode) or type(row['data']) is not str
                or not 0<=row['bytes']<=_MAX_FILE_BYTES):
            raise ValueError("invalid bounded output payload")
        body=base64.b64decode(row['data'],validate=True);total+=len(body)
        if len(body)!=row['bytes'] or hashlib.sha256(body).hexdigest()!=row['sha256'] or total>OUTPUT_LIMIT:
            raise ValueError("output payload integrity/bound failure")
        decoded.append((row,body))
    if initial_state(executor,paths)!=before:raise ToolRejected("command-output preimages changed before publication")
    mutation_grant=Grant(tuple(paths),False,create_paths=tuple(paths),read_paths=tuple(paths),
        mode_paths=tuple(paths),mode_mask=0o777)
    prior={p:(digest,mode) for p,digest,mode in before};assets=[];receipts=[]
    # Root immutable bytes before their associated visible filesystem effects.
    for row,body in decoded:
        path=row['path'];old_sha,old_mode=prior[path]
        if row['deleted']:
            if old_sha is None:raise ValueError("deletion has no original output")
            old=executor._read_private_bytes(path);assets.append(executor._artifact(old))
            with executor._parent_directory(path) as (parent,name):
                info=os.stat(name,dir_fd=parent,follow_symlinks=False)
                if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1:raise ToolRejected("unsafe output deletion")
                os.unlink(name,dir_fd=parent);os.fsync(parent)
            receipts.append(dict(path=path,deleted=True,changed=True,before_sha256=old_sha,sha256=None,bytes=0,mode=None))
            continue
        artifact=executor._artifact(body);assets.append(artifact)
        suffix='-output-'+str(len(receipts))
        if old_sha is None:
            executor.create_file(operation_id[:80]+suffix,mutation_grant,path,body)
        elif old_sha!=row['sha256']:
            executor.replace_file(operation_id[:80]+suffix,mutation_grant,path,old_sha,body)
        changed=old_sha!=row['sha256'] or old_mode!=int(row['mode'],8)
        if changed:executor.set_mode(operation_id[:80]+suffix+'-mode',mutation_grant,path,row['sha256'],row['mode'])
        receipts.append(dict(path=path,deleted=False,changed=changed,before_sha256=old_sha,sha256=artifact.sha256,
            bytes=artifact.size_bytes,mode=row['mode'],artifact=(artifact.sha256,artifact.size_bytes)))
    return receipts,tuple(assets)
