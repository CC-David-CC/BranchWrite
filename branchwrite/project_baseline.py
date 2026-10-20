"""Derived immutable input inventory stored in the existing RuntimeLog artifacts.

No model history or alternative workflow is introduced. Canonical root inputs
bind the manifest reference. Chunks keep existing codec/container bounds intact.
"""
import os,stat
from pathlib import Path
from .records import Artifact,encode,decode,CorruptLog
from .execution import _relative_path,ToolRejected
BINDING='project-input-manifest'
MAX_ENTRIES=20000
MAX_TOTAL=64*1024**2
CHUNK=512

def reference_text(ref):
    return ref.sha256+':'+str(ref.size_bytes)

def parse_reference(text):
    if type(text) is not str:raise ValueError('project input reference must be text')
    sha,size=text.split(':')
    if not size.isascii() or not size.isdigit():raise ValueError('invalid project input reference')
    return Artifact(sha,int(size))

def capture(log,registry):
    before=registry._inventory();entries=[];total=0
    workspace=registry.executor.workspace
    for directory,dirs,files,fd in os.fwalk(workspace,follow_symlinks=False):
        relative=Path(directory).relative_to(workspace)
        for name in dirs:
            info=os.stat(name,dir_fd=fd,follow_symlinks=False)
            if name=='.git' or not stat.S_ISDIR(info.st_mode):
                raise ToolRejected('unsupported baseline directory/link')
            entries.append(('directory',(relative/name).as_posix(),stat.S_IMODE(info.st_mode)))
        for name in files:
            path=(relative/name).as_posix()
            raw=registry.executor._read_private_bytes(path)
            snapshot=registry._snapshot(path)
            ref=log.put_artifact(raw)
            if ref.sha256!=snapshot[1]:raise ToolRejected('project input changed during capture')
            entries.append(('file',path,snapshot[2],ref.sha256,ref.size_bytes));total+=len(raw)
        if len(entries)>MAX_ENTRIES or total>MAX_TOTAL:raise ToolRejected('project input exceeds inventory bounds')
    if registry._inventory()!=before:raise ToolRejected('project input changed during capture')
    entries.sort(key=lambda row:row[1]);chunks=[]
    for i in range(0,len(entries),CHUNK):
        ref=log.put_artifact(encode(tuple(entries[i:i+CHUNK])))
        chunks.append((ref.sha256,ref.size_bytes))
    return log.put_artifact(encode(dict(schema=1,inventory=before,entries=len(entries),chunks=tuple(chunks))))

def load(log,ref):
    manifest=decode(log.read_artifact(ref))
    if (type(manifest) is not dict or set(manifest)!={'schema','inventory','entries','chunks'}
        or type(manifest['schema']) is not int or manifest['schema']!=1
        or type(manifest['entries']) is not int or not 0<=manifest['entries']<=MAX_ENTRIES
        or type(manifest['chunks']) is not tuple or len(manifest['chunks'])>40):
        raise CorruptLog('invalid project input manifest')
    Artifact(manifest['inventory'],0)
    files={};directories={};seen=set();total=0;previous=None
    for wire in manifest['chunks']:
        rows=decode(log.read_artifact(Artifact(*wire)))
        if type(rows) is not tuple or not 1<=len(rows)<=CHUNK:raise CorruptLog('invalid project input chunk')
        for row in rows:
            if type(row) is not tuple or len(row) not in (3,5):raise CorruptLog('invalid input entry')
            kind,path,mode=row[:3];_relative_path(path)
            if path in seen or previous is not None and path<=previous:raise CorruptLog('noncanonical input paths')
            if type(mode) is not int or not 0<=mode<=0o777:raise CorruptLog('invalid input mode')
            seen.add(path);previous=path
            if kind=='directory' and len(row)==3:directories[path]=mode
            elif kind=='file' and len(row)==5:
                payload=Artifact(row[3],row[4]);raw=log.read_artifact(payload);total+=len(raw)
                if total>MAX_TOTAL:raise CorruptLog('input byte bound exceeded')
                files[path]=dict(mode=mode,sha256=payload.sha256,bytes=raw)
            else:raise CorruptLog('invalid input entry kind')
    if len(seen)!=manifest['entries']:raise CorruptLog('input entry count mismatch')
    for path in seen:
        for parent in Path(path).parents:
            if str(parent)=='.':break
            if parent.as_posix() not in directories:raise CorruptLog('input parent missing')
    return dict(inventory=manifest['inventory'],files=files,directories=directories)
