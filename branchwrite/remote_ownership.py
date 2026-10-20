"""Shared host-local ownership of one declared remote endpoint.

A process lock prevents overlap; the durable reservation survives process death.
Only validated original receipts release it. Lock release or a dead PID is not
proof that remote effects ended. This is target ownership, not workflow history.
The initial VM capability is owned by one client host; this is not cross-host
fleet locking and must not be advertised as such.
"""
from contextlib import contextmanager
from hashlib import sha256
import fcntl,json,os,stat,threading
from pathlib import Path
from .remote_execution import _directory,_private,_write,_json,_HEX,_ID,RemoteIndeterminate

class RemoteTargetBusy(ValueError):pass

class TargetOwnership:
 def __init__(self,root,resource_id):
  if type(resource_id) is not str or not _HEX.fullmatch(resource_id):raise ValueError('exact remote resource identity required')
  self.root=_directory(root);self.resource_id=resource_id;self.marker=self.root/(resource_id+'.active.json');self.latest=self.root/(resource_id+'.latest.json')
 def latest_intent(self):
  # This is a source-bound resource reference, not another history or a promise
  # about uncoordinated external edits. An active/unknown call makes it ineligible.
  with self.hold():
   if self.marker.exists() or self.marker.is_symlink():raise RemoteIndeterminate('Remote target has active or unresolved work')
   if not self.latest.exists() and not self.latest.is_symlink():return None
   value=json.loads(_private(self.latest))
   if (type(value) is not dict or set(value)!={'schema','resource_id','intent_sha256'}
       or type(value['schema']) is not int or value['schema']!=1 or value['resource_id']!=self.resource_id
       or type(value['intent_sha256']) is not str or not _HEX.fullmatch(value['intent_sha256'])):raise RemoteIndeterminate('Remote settled-call identity is invalid')
   return value['intent_sha256']
 @contextmanager
 def hold(self):
  fd=os.open(self.root/(self.resource_id+'.lock'),os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
  with os.fdopen(fd,'r+b') as lock:
   info=os.fstat(lock.fileno())
   if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or info.st_nlink!=1 or info.st_mode&0o077:raise ValueError('invalid remote ownership lock')
   try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
   except BlockingIOError as error:raise RemoteTargetBusy('Remote target is busy with another client operation') from error
   held=_Reservation(self)
   try:yield held
   finally:held.active=False

class _Reservation:
 def __init__(self,owner):self.owner=owner;self.thread=threading.get_ident();self.active=True
 def _check(self):
  if not self.active or self.thread!=threading.get_ident():raise ValueError('remote ownership is stale or belongs to another thread')
 def reserve(self,path,intent):
  self._check();path=Path(path)
  if self.owner.marker.exists() or self.owner.marker.is_symlink():raise RemoteIndeterminate('Prior remote reservation is unresolved; no new dispatch')
  if (type(intent) is not dict or type(intent.get('operation_id')) is not str or not _ID.fullmatch(intent['operation_id'])
      or type(intent.get('plan_sha256')) is not str or not _HEX.fullmatch(intent['plan_sha256'])):raise ValueError('exact original remote intent required')
  raw=_private(path)
  if raw!=_json(intent):raise ValueError('reservation must bind the exact durable intent')
  _write(self.owner.marker,dict(schema=1,resource_id=self.owner.resource_id,intent_path=str(path),intent_sha256=sha256(raw).hexdigest(),operation_id=intent['operation_id'],plan_sha256=intent['plan_sha256']))
 def check_available(self,validate_receipt):
  self._check();path=self.owner.marker
  if not path.exists() and not path.is_symlink():return
  try:
   marker=json.loads(_private(path))
   if (type(marker) is not dict or set(marker)!={'schema','resource_id','intent_path','intent_sha256','operation_id','plan_sha256'}
       or type(marker['schema']) is not int or marker['schema']!=1 or marker['resource_id']!=self.owner.resource_id):raise ValueError('invalid reservation schema/identity')
   original=Path(marker['intent_path']);raw=_private(original);intent=json.loads(raw)
   if (sha256(raw).hexdigest()!=marker['intent_sha256'] or intent['operation_id']!=marker['operation_id'] or intent['plan_sha256']!=marker['plan_sha256']):raise ValueError('reservation original intent changed')
   if validate_receipt(original.parent,intent) is not True:raise ValueError('original receipt remains absent/invalid')
  except Exception as error:raise RemoteIndeterminate('Remote target has an unresolved original operation; no new dispatch') from error
  _write(self.owner.latest,dict(schema=1,resource_id=self.owner.resource_id,intent_sha256=marker['intent_sha256']))
  path.unlink();fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
  try:os.fsync(fd)
  finally:os.close(fd)
 def complete(self,validate_receipt):
  self._check()
  if not self.owner.marker.exists():raise RemoteIndeterminate('Remote reservation disappeared; completion is unproven')
  self.check_available(validate_receipt)
