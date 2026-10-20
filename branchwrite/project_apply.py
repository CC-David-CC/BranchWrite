"""Guarded application into a new owned project copy on Linux.

Never mutates the source checkout. Hash pinning selects the reviewed archive;
inventory/preimage checks reject stale inputs. No in-place atomicity claim.
"""
import ctypes,errno,hashlib,io,json,os,re,shutil,stat,tempfile,zipfile
from pathlib import Path
from .execution import Executor,Grant,_relative_path
from .tool_registry import ToolRegistry
HEX=re.compile('[0-9a-f]{64}')
MAX_ARCHIVE=256*1024**2

def _read_bundle_unchecked(path,expected):
    if type(expected) is not str or HEX.fullmatch(expected) is None:
        raise ValueError('explicit archive SHA256 hash required')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as f:
        info=os.fstat(f.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size>MAX_ARCHIVE:raise ValueError('bounded regular archive required')
        raw=f.read(MAX_ARCHIVE+1)
    if len(raw)>MAX_ARCHIVE or hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('archive hash mismatch')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        entries=z.infolist();names=[x.filename for x in entries]
        if len(names)!=len(set(names)) or len(names)>20001:raise ValueError('duplicate/excess archive entries')
        if 'manifest.json' not in names:raise ValueError('manifest missing')
        if any(x.file_size>128*1024**2 for x in entries) or sum(x.file_size for x in entries)>MAX_ARCHIVE:
            raise ValueError('archive expansion exceeds bound')
        manifest=json.loads(z.read('manifest.json'))
        if type(manifest) is not dict or type(manifest.get('schema')) is not int or manifest['schema']!=1 or manifest.get('format')!='bw.review-export.v1':
            raise ValueError('unsupported export format')
        review=manifest['review']
        if type(review) is not dict:raise ValueError('invalid review manifest')
        if review.get('complete_project_patch') is not True or review.get('coverage')!='complete-project':
            raise ValueError('complete project review required')
        changes=review['changes'];payloads={};paths=set()
        if type(changes) is not list or len(changes)>20000:raise ValueError('invalid changes')
        for row in changes:
            if type(row) is not dict:raise ValueError('invalid change row')
            path=row['path'];_relative_path(path)
            if path in paths:raise ValueError('duplicate changed path')
            paths.add(path)
            sha=row['after_sha256']
            if type(sha) is not str or HEX.fullmatch(sha) is None:raise ValueError('invalid payload hash')
            raw=z.read('payloads/'+sha)
            if len(raw)>4*1024**2 or len(raw)!=row['after_bytes'] or hashlib.sha256(raw).hexdigest()!=sha:
                raise ValueError('payload size/hash mismatch')
            for mode in [row['after_mode']]:
                if type(mode) is not int or not 0<=mode<=0o777:raise ValueError('invalid mode')
            payloads[sha]=raw
        if set(names)!={'manifest.json'}|{'payloads/'+sha for sha in payloads}:
            raise ValueError('unexpected archive member')
    return review,payloads

def _read_bundle(path,expected):
    try:return _read_bundle_unchecked(path,expected)
    except (KeyError,TypeError,AttributeError,zipfile.BadZipFile) as exc:
        raise ValueError('invalid export manifest or ZIP') from exc

def _rename_new(source,destination):
    # os.rename may replace an existing empty directory. Require the Linux
    # no-replace primitive rather than checking existence and racing rename.
    libc=ctypes.CDLL(None,use_errno=True);rename=getattr(libc,'renameat2',None)
    if rename is None:raise RuntimeError('Linux renameat2 required for exclusive directory publication')
    rename.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint]
    rename.restype=ctypes.c_int
    if rename(-100,os.fsencode(source),-100,os.fsencode(destination),1):
        code=ctypes.get_errno();raise OSError(code,os.strerror(code),str(destination))

def _sync_tree(root):
    for directory,dirs,files in os.walk(root,topdown=False,followlinks=False):
        for name in files:
            fd=os.open(Path(directory)/name,os.O_RDONLY|os.O_NOFOLLOW)
            try:os.fsync(fd)
            finally:os.close(fd)
        fd=os.open(directory,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:os.fsync(fd)
        finally:os.close(fd)


_RECEIPT='user.branchwrite.apply.v1'

def _intent(archive_sha,source,dest,operation_id):
    value=dict(schema=1,archive_sha256=archive_sha,source=str(source),destination=str(dest))
    if operation_id is None:
        operation_id='bwapply-'+hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()[:40]
    if type(operation_id) is not str or re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}',operation_id) is None:
        raise ValueError('bounded host operation identity required')
    return dict(value,operation_id=operation_id)

def _result(intent,inventory):
    return dict(status='APPLIED_NEW_COPY',path=intent['destination'],archive_sha256=intent['archive_sha256'],
                inventory=inventory,operation_id=intent['operation_id'],original_checkout_modified=False)

def _sync_parent(dest):
    parent=os.open(dest.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(parent)
    finally:os.close(parent)

def _reconcile(dest,intent,inventory):
    info=dest.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.getuid():
        raise FileExistsError('destination is not an owned published directory')
    try:raw=os.getxattr(dest,_RECEIPT,follow_symlinks=False)
    except OSError as exc:
        if exc.errno in (errno.ENODATA,errno.ENOTSUP):
            raise FileExistsError('existing destination has no owned publication receipt') from exc
        raise
    if len(raw)>4096:raise ValueError('invalid apply receipt')
    receipt=json.loads(raw)
    if type(receipt) is not dict:raise ValueError('invalid apply receipt')
    if receipt.get('intent')!=intent:raise ValueError('different operation owns this destination')
    if receipt.get('identity')!=[info.st_dev,info.st_ino]:
        raise ValueError('publication directory identity changed')
    if receipt.get('inventory')!=inventory:raise ValueError('receipt inventory mismatch')
    ex=Executor(Path(intent['source']),dest.parent,dest)
    if ToolRegistry(ex,Grant((),False))._inventory()!=inventory:
        raise ValueError('published result inventory changed')
    # A prior attempt may have lost its parent-fsync acknowledgment. Verify the
    # exact owned tree, repeat the durability boundary, then return SAME receipt.
    _sync_tree(dest);_sync_parent(dest)
    return _result(intent,inventory)

def apply_export(archive,source,destination,*,expected_sha256,operation_id=None):
    review,payloads=_read_bundle(archive,expected_sha256)
    source=Path(source).absolute();dest=Path(destination).absolute()
    dest=dest.parent.resolve(strict=True)/dest.name
    original=source.resolve(strict=False)
    if dest.is_relative_to(original) or original.is_relative_to(dest):
        raise ValueError('destination must be outside the source')
    intent=_intent(expected_sha256,original,dest,operation_id)
    if dest.exists() or dest.is_symlink():return _reconcile(dest,intent,review['current_inventory'])
    stage=Path(tempfile.mkdtemp(prefix='.bw-apply-',dir=dest.parent))
    try:
        ex=Executor.create(source,stage/'world',project_input=True)
        registry=ToolRegistry(ex,Grant((),False))
        if registry._inventory()!=review['baseline_inventory']:
            raise ValueError('source no longer matches the immutable project baseline')
        for row in review['changes']:
            path=row['path'];snapshot=registry._snapshot(path)
            if snapshot!=(path,row['before_sha256'],row['before_mode']):
                raise ValueError('destination preimage mismatch: '+ascii(path))
        for row in review['changes']:
            path=row['path']
            with ex._parent_directory(path,create_missing=True) as (parent,name):
                flags=os.O_WRONLY|os.O_NOFOLLOW
                flags|=os.O_CREAT|os.O_EXCL if row['before_sha256'] is None else os.O_TRUNC
                fd=os.open(name,flags,0o600,dir_fd=parent)
                with os.fdopen(fd,'wb') as f:
                    f.write(payloads[row['after_sha256']]);os.fchmod(f.fileno(),row['after_mode'])
                    f.flush();os.fsync(f.fileno())
        for row in review.get('created_directories',[]):
            _relative_path(row['path']);mode=row['mode']
            if type(mode) is not int or not 0<=mode<=0o777:raise ValueError('invalid directory mode')
            directory=ex.workspace/row['path']
            directory.mkdir(parents=True,exist_ok=True);os.chmod(directory,mode,follow_symlinks=False)
        if registry._inventory()!=review['current_inventory']:
            raise ValueError('applied project inventory mismatch')
        info=ex.workspace.stat()
        receipt=dict(intent=intent,identity=[info.st_dev,info.st_ino],inventory=review['current_inventory'])
        raw=json.dumps(receipt,sort_keys=True,separators=(',',':')).encode()
        if len(raw)>4096:raise ValueError('apply receipt exceeds filesystem metadata bound')
        # Co-publish ownership with the directory itself. No sidecar/project file
        # or separate workflow ledger; unsupported xattrs fail before publication.
        os.setxattr(ex.workspace,_RECEIPT,raw,flags=os.XATTR_CREATE,follow_symlinks=False)
        _sync_tree(ex.workspace)
        _rename_new(ex.workspace,dest)
        _sync_parent(dest)
    finally:
        # This exact task-owned staging root never contains the published tree.
        # A published result is never rolled back after a later failure.
        shutil.rmtree(stage)
    return _result(intent,review['current_inventory'])

def command(archive,source,destination,expected,operation_id=None):
    import sys
    try:result=apply_export(archive,source,destination,expected_sha256=expected,operation_id=operation_id)
    except (OSError,ValueError,RuntimeError,KeyError,zipfile.BadZipFile) as exc:
        print('branchwrite: '+ascii(str(exc)),file=sys.stderr);return 2
    print(json.dumps(result,sort_keys=True));return 0
