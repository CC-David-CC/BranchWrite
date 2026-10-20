"""Production typed run records for the one BranchWrite interpreter.

No model transcript, native state, workflow engine, JSON/pickle or reference
runtime is kept here. The caller retains opaque COW receipts as typed artifacts.
Local Linux single-writer/process-crash scope; power loss remains unqualified.
"""
from dataclasses import dataclass
from decimal import Decimal
import fcntl
import hashlib
import math
import os
from pathlib import Path
import re
import stat
import struct
import tempfile
import threading

MAX_BYTES = 4 * 1024**2
MAX_DEPTH = 40
MAX_ITEMS = 4096
_HEADER = struct.Struct('>QI32s32s')
_MAGIC = b'BWL1\0'
_DOMAIN = b'branchwrite.event.v1\0'
_HEX = re.compile(r'[0-9a-f]{64}\Z')


def encode(value):
    """BWT1 exact typed value: tag + uint32 length + payload, bounded recursively."""
    def pack(value, depth):
        if depth > MAX_DEPTH:
            raise ValueError('typed value depth limit')
        typ = type(value)
        if value is None: tag, data = b'n', b''
        elif typ is bool: tag, data = b'b', bytes([int(value)])
        elif typ is int:
            if value.bit_length() > 12000: raise ValueError('integer bit limit')
            tag, data = b'i', str(value).encode('ascii')
        elif typ is float:
            if not math.isfinite(value): raise ValueError('nonfinite float')
            tag, data = b'f', struct.pack('>d', value)
        elif typ is Decimal:
            if not value.is_finite(): raise ValueError('nonfinite decimal')
            tag, data = b'd', str(value).encode('ascii')
        elif typ is str: tag, data = b'u', value.encode('utf8')
        elif typ is bytes: tag, data = b'x', value
        elif typ in (list, tuple, dict):
            if len(value) > MAX_ITEMS: raise ValueError('container item limit')
            tag = {list:b'l', tuple:b't', dict:b'm'}[typ]
            if typ is dict:
                if any(type(k) is not str for k in value): raise ValueError('record keys must be text')
                children = (item for k in sorted(value) for item in (k, value[k]))
            else: children = iter(value)
            data = bytearray()
            for item in children:
                child = pack(item, depth + 1)
                if len(data) + len(child) > MAX_BYTES - 9: raise ValueError('typed value byte limit')
                data.extend(child)
            data = bytes(data)
        else: raise ValueError('unsupported exact type')
        if len(data) > MAX_BYTES - 9: raise ValueError('typed value byte limit')
        return tag + struct.pack('>I',len(data)) + data
    result = b'BWT\x01' + pack(value,0)
    if len(result) > MAX_BYTES: raise ValueError('typed value byte limit')
    return result


def decode(raw):
    if type(raw) is not bytes or len(raw) > MAX_BYTES or not raw.startswith(b'BWT\x01'):
        raise ValueError('invalid typed record/version')
    def take(at, limit, depth):
        if depth > MAX_DEPTH or at+5 > limit: raise ValueError('truncated/deep typed value')
        tag=raw[at:at+1];length=struct.unpack('>I',raw[at+1:at+5])[0];start=at+5;end=start+length
        if end > limit: raise ValueError('truncated typed payload')
        data=raw[start:end]
        if tag==b'n':
            if data: raise ValueError('invalid null')
            value=None
        elif tag==b'b':
            if data not in (b'\0',b'\1'): raise ValueError('invalid bool')
            value=data==b'\1'
        elif tag==b'i':
            if not re.fullmatch(rb'0|-?[1-9][0-9]*',data) or len(data)>3700: raise ValueError('invalid integer')
            value=int(data)
        elif tag==b'f':
            if len(data)!=8: raise ValueError('invalid float width')
            value=struct.unpack('>d',data)[0]
        elif tag==b'd': value=Decimal(data.decode('ascii'))
        elif tag==b'u': value=data.decode('utf8')
        elif tag==b'x': value=data
        elif tag in (b'l',b't',b'm'):
            values=[];cursor=start
            while cursor<end:
                item,cursor=take(cursor,end,depth+1);values.append(item)
                if len(values) > (MAX_ITEMS*2 if tag==b'm' else MAX_ITEMS): raise ValueError('item limit')
            if tag==b'l': value=values
            elif tag==b't': value=tuple(values)
            else:
                keys=values[::2]
                if len(values)%2 or any(type(k) is not str for k in keys) or keys!=sorted(set(keys)):
                    raise ValueError('noncanonical record keys')
                value=dict(zip(keys,values[1::2]))
        else: raise ValueError('unknown typed tag')
        return value,end
    try:
        value,end=take(4,len(raw),0)
        if end!=len(raw) or encode(value)!=raw: raise ValueError('noncanonical typed record')
        return value
    except (UnicodeError,ArithmeticError,OverflowError) as exc:
        raise ValueError('invalid typed scalar') from exc


class CorruptLog(ValueError): pass
class TornTail(CorruptLog): pass
class MissingArtifact(CorruptLog): pass
class WriterBusy(RuntimeError): pass
class WriterPoisoned(RuntimeError): pass


@dataclass(frozen=True)
class Artifact:
    sha256: str
    size_bytes: int
    def __post_init__(self):
        if (type(self.sha256) is not str or not _HEX.fullmatch(self.sha256)
                or type(self.size_bytes) is not int or not 0<=self.size_bytes<=MAX_BYTES):
            raise ValueError('invalid artifact reference')


@dataclass(frozen=True)
class EventReceipt:
    sequence: int
    sha256: str


def _sync_directory(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC)
    try: os.fsync(fd)
    finally: os.close(fd)


def _write_all(fd,raw):
    view=memoryview(raw)
    while view:
        count=os.write(fd,view)
        if count<=0: raise OSError('short record write')
        view=view[count:]


class RuntimeLog:
    """Owned typed append log and immutable byte artifacts, not another runtime.

    A failed append poisons this writer because the call may have reached disk.
    Reopen/replay and reconcile invocation IDs; never silently rerun its effect.
    Torn tails are preserved and reported; this layer never truncates history.
    """
    def __init__(self,root,*,read_only=False):
        if type(read_only) is not bool:raise TypeError('read_only must be boolean')
        self._read_only=read_only
        self.root=Path(root).absolute();self._owner=threading.current_thread();self._pid=os.getpid()
        self._closed=False;self._poisoned=False;self._frames=[];self._last=bytes(32)
        if read_only:
            if not stat.S_ISDIR(self.root.lstat().st_mode):raise ValueError('run root must be a directory')
        else:self.root.mkdir(mode=0o700,parents=True,exist_ok=True)
        if self.root.is_symlink() or self.root.stat().st_uid!=os.getuid(): raise ValueError('unowned run root')
        self.artifacts=self.root/'artifacts'
        if read_only:
            if not stat.S_ISDIR(self.artifacts.lstat().st_mode):raise ValueError('artifact directory must exist')
        else:self.artifacts.mkdir(mode=0o700,exist_ok=True)
        if self.artifacts.is_symlink(): raise ValueError('artifact directory is a link')
        self._lock=os.open(self.root/'writer.lock',(os.O_RDONLY if read_only else os.O_RDWR|os.O_CREAT)|os.O_NOFOLLOW|os.O_CLOEXEC,0o600)
        try:
            if not stat.S_ISREG(os.fstat(self._lock).st_mode): raise CorruptLog('writer lock is not a regular file')
            try: fcntl.flock(self._lock,(fcntl.LOCK_SH if read_only else fcntl.LOCK_EX)|fcntl.LOCK_NB)
            except BlockingIOError as exc: raise WriterBusy('run is busy; writer or incompatible reader active') from exc
            self._fd=os.open(self.root/'events.bwl',(os.O_RDONLY if read_only else os.O_RDWR|os.O_CREAT|os.O_APPEND)|os.O_NOFOLLOW|os.O_CLOEXEC,0o600)
            try:
                if not stat.S_ISREG(os.fstat(self._fd).st_mode): raise CorruptLog('ledger is not a regular file')
                with os.fdopen(os.dup(self._fd),'rb') as stream: raw=stream.read()
                if not raw and not read_only:
                    _write_all(self._fd,_MAGIC);os.fsync(self._fd);_sync_directory(self.root);raw=_MAGIC
                self._replay(raw)
            except BaseException:
                os.close(self._fd);raise
        except BaseException:
            os.close(self._lock);self._closed=True;raise

    def _check(self,*,write=False):
        if self._closed: raise RuntimeError('run writer is closed')
        if self._pid!=os.getpid() or self._owner is not threading.current_thread():
            raise RuntimeError('run writer belongs to its original process/thread')
        if write and self._read_only:raise PermissionError('read-only ledger cannot publish artifacts or events')

    def _replay(self,raw):
        if not raw.startswith(_MAGIC): raise CorruptLog('bad ledger version/header')
        cursor=len(_MAGIC)
        while cursor<len(raw):
            start=cursor
            if cursor+_HEADER.size+32>len(raw): raise TornTail('incomplete frame header at '+str(start))
            header=raw[cursor:cursor+_HEADER.size]
            header_digest=raw[cursor+_HEADER.size:cursor+_HEADER.size+32]
            if header_digest!=hashlib.sha256(b'branchwrite.header.v1\0'+header).digest():
                raise CorruptLog('committed frame header checksum mismatch at '+str(start))
            seq,size,previous,digest=_HEADER.unpack(header);cursor+=_HEADER.size+32
            if seq!=len(self._frames) or previous!=self._last or size>MAX_BYTES:
                raise CorruptLog('broken sequence/chain/length at '+str(start))
            if cursor+size>len(raw): raise TornTail('incomplete frame payload at '+str(start))
            payload=raw[cursor:cursor+size];cursor+=size
            expected=hashlib.sha256(_DOMAIN+struct.pack('>Q',seq)+previous+payload).digest()
            if digest!=expected: raise CorruptLog('committed frame checksum mismatch at '+str(start))
            try:
                value=decode(payload)
                if type(value) is not dict or set(value)!={'event','artifacts'} or type(value['event']) is not dict or type(value['artifacts']) is not tuple:
                    raise ValueError('invalid event shape')
                for item in value['artifacts']:
                    if type(item) is not tuple or len(item)!=2: raise ValueError('invalid artifact shape')
                    self.read_artifact(Artifact(*item))
            except CorruptLog: raise
            except (ValueError,TypeError) as exc: raise CorruptLog('invalid typed frame') from exc
            self._frames.append(payload);self._last=digest

    @property
    def event_count(self):
        self._check()
        if self._poisoned: raise WriterPoisoned('reopen uncertain writer')
        return len(self._frames)

    @property
    def events(self):
        self._check()
        if self._poisoned: raise WriterPoisoned('reopen uncertain writer')
        return tuple(decode(raw) for raw in self._frames)

    def read_artifact(self,ref):
        return self._artifact(ref,durable=False)

    def _artifact(self,ref,*,durable):
        self._check()
        if not isinstance(ref,Artifact): raise TypeError('typed artifact required')
        try: fd=os.open(self.artifacts/ref.sha256,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC|os.O_NONBLOCK)
        except FileNotFoundError as exc: raise MissingArtifact(ref.sha256) from exc
        with os.fdopen(fd,'rb') as stream:
            info=os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size!=ref.size_bytes: raise CorruptLog('artifact size/type mismatch')
            raw=stream.read(MAX_BYTES+1)
            if durable: os.fsync(stream.fileno())
        if len(raw)!=ref.size_bytes or hashlib.sha256(raw).hexdigest()!=ref.sha256: raise CorruptLog('artifact checksum mismatch')
        return raw

    def put_artifact(self,raw):
        self._check(write=True)
        if self._poisoned: raise WriterPoisoned('reopen uncertain writer')
        if type(raw) is not bytes or len(raw)>MAX_BYTES: raise ValueError('artifact byte limit/type')
        ref=Artifact(hashlib.sha256(raw).hexdigest(),len(raw));path=self.artifacts/ref.sha256
        fd,temp=tempfile.mkstemp(prefix='.artifact-',dir=self.root)
        try:
            try:
                _write_all(fd,raw);os.fchmod(fd,0o400);os.fsync(fd)
            finally: os.close(fd)
            try: os.link(temp,path,follow_symlinks=False)
            except FileExistsError: self.read_artifact(ref)
            _sync_directory(self.artifacts)
        finally: os.unlink(temp)
        return ref

    def append(self,event,*,artifacts=()):
        self._check(write=True)
        if self._poisoned: raise WriterPoisoned('reopen uncertain writer')
        if type(event) is not dict or type(artifacts) is not tuple: raise ValueError('typed event/tuple references required')
        for ref in artifacts:self._artifact(ref,durable=True)
        if artifacts: _sync_directory(self.artifacts)
        payload=encode(dict(event=event,artifacts=tuple((a.sha256,a.size_bytes) for a in artifacts)))
        seq=len(self._frames);digest=hashlib.sha256(_DOMAIN+struct.pack('>Q',seq)+self._last+payload).digest()
        try:
            header=_HEADER.pack(seq,len(payload),self._last,digest)
            header_digest=hashlib.sha256(b'branchwrite.header.v1\0'+header).digest()
            _write_all(self._fd,header+header_digest+payload);os.fsync(self._fd)
        except BaseException:
            self._poisoned=True;raise
        self._frames.append(payload);self._last=digest
        return EventReceipt(seq,digest.hex())

    def close(self):
        self._check();self._closed=True
        try: os.close(self._fd)
        finally: os.close(self._lock)
    def __enter__(self): self._check();return self
    def __exit__(self,*args): self.close()
