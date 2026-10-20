"""Publish a complete reviewed change bundle into a new private archive.

This is artifact export, not checkout application or a workflow COMMIT.
"""
import hashlib,io,json,os,tempfile,zipfile
from pathlib import Path
from .records import RuntimeLog
from .coding_cli import read_launch
from .coding_review import inspect_changes
from .execution import Executor,Grant
from .tool_registry import ToolRegistry

def export_changes(state,destination):
    state=Path(state);destination=Path(destination).absolute()
    # A retained shared lock excludes execution throughout review and copying.
    with RuntimeLog(state/'ledger',read_only=True):
        review=inspect_changes(state)
        if not review['complete_project_patch']:
            raise ValueError('complete immutable project baseline required for export')
        config=read_launch(state)['config']
        resolved=destination.parent.resolve(strict=True)/destination.name
        if resolved.is_relative_to(state.resolve()) or resolved.is_relative_to(Path(config['source']).resolve()):
            raise ValueError('export destination must be outside the project and run state')
        destination=resolved
        ex=Executor(Path(config['source']),state/'world',state/'world/workspace')
        registry=ToolRegistry(ex,Grant((),False));buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,'w',compression=zipfile.ZIP_STORED) as archive:
            archive.writestr('manifest.json',json.dumps(dict(schema=1,format='bw.review-export.v1',review=review),sort_keys=True,ensure_ascii=True))
            stored=set()
            for row in review['changes']:
                raw=ex._read_private_bytes(row['path'])
                if hashlib.sha256(raw).hexdigest()!=row['after_sha256']:
                    raise ValueError('workspace changed during export')
                if row['after_sha256'] not in stored:
                    archive.writestr('payloads/'+row['after_sha256'],raw);stored.add(row['after_sha256'])
        if registry._inventory()!=review['current_inventory']:
            raise ValueError('workspace changed during export')
        payload=buffer.getvalue()
        # Stage -> fsync -> exclusive link publication -> parent fsync. No
        # existing destination is replaced; a crash can leave an owned staging
        # file, but cannot expose an acknowledged partial final archive.
        fd,name=tempfile.mkstemp(prefix='.bw-export-',dir=destination.parent)
        temporary=Path(name)
        try:
            with os.fdopen(fd,'wb') as stream:
                os.fchmod(stream.fileno(),0o600);stream.write(payload);stream.flush();os.fsync(stream.fileno())
            os.link(temporary,destination,follow_symlinks=False)
            directory=os.open(destination.parent,os.O_RDONLY|os.O_DIRECTORY)
            try:os.fsync(directory)
            finally:os.close(directory)
        finally:
            temporary.unlink()
    return dict(status='EXPORTED',path=str(destination),bytes=len(payload),
                sha256=hashlib.sha256(payload).hexdigest(),changed_files=len(review['changes']),
                checkout_modified=False)

def command(state,destination):
    import sys
    try:result=export_changes(state,destination)
    except (OSError,ValueError,RuntimeError,KeyError) as exc:
        print('branchwrite: '+ascii(str(exc)),file=sys.stderr);return 2
    print(json.dumps(result,sort_keys=True));return 0
