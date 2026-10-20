"""Host-selected SSH boundary with original-intent/receipt recovery.

The caller must durably dispatch its FrameKernel tool invocation before run().
These sidecars retain transport evidence, not workflow control or a transcript.
An unacknowledged remote effect is never resent. Reading a retained receipt is
local and non-executing. Client death before receipt publication remains unknown:
this prototype needs explicit inspection rather than claiming exactly-once effects.
Ordinary sandboxed shell tools receive neither this capability nor its credentials.
"""
from dataclasses import dataclass,field
from hashlib import sha256
import base64,fcntl,ipaddress,json,math,os,re,shlex,stat,subprocess,tempfile,time
from pathlib import Path
from .execution import Executor
from .terminal import NamedCommand

_ID=re.compile(r'[A-Za-z][A-Za-z0-9_-]{0,127}\Z')
_HEX=re.compile(r'[0-9a-f]{64}\Z')

def _json(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()
def _private(path):
 path=Path(path)
 if not path.is_absolute():raise ValueError('absolute private credential/receipt path required')
 try:fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 except OSError as error:raise ValueError('private regular file required') from error
 with os.fdopen(fd,'rb') as f:
  info=os.fstat(f.fileno())
  if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode&0o077 or info.st_nlink!=1 or info.st_size>8*1024*1024:raise ValueError('private owned regular file required')
  raw=f.read(8*1024*1024+1)
  if len(raw)!=info.st_size or fstat_key(os.fstat(f.fileno()))!=fstat_key(info):raise ValueError('private file changed while reading')
 return raw

def fstat_key(i):return (i.st_dev,i.st_ino,i.st_size,i.st_mtime_ns,i.st_ctime_ns,stat.S_IMODE(i.st_mode))
def _write(path,value):
 fd,name=tempfile.mkstemp(prefix='.remote-',dir=path.parent)
 try:
  with os.fdopen(fd,'wb') as f:os.fchmod(f.fileno(),0o600);f.write(_json(value));f.flush();os.fsync(f.fileno())
  os.replace(name,path);d=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
  try:os.fsync(d)
  finally:os.close(d)
 finally:
  if os.path.exists(name):os.unlink(name)

def _directory(path):
 path=Path(path).absolute();created=not path.exists();path.mkdir(mode=0o700,exist_ok=True);i=path.lstat()
 if not stat.S_ISDIR(i.st_mode) or i.st_uid!=os.getuid() or stat.S_IMODE(i.st_mode)!=0o700:raise ValueError('owned mode0700 remote evidence directory required')
 if created:
  fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
  try:os.fsync(fd)
  finally:os.close(fd)
 return path

def validate_target_fields(name,host,port,user,identity_file,known_hosts_file,timeout):
  if type(name) is not str or not _ID.fullmatch(name):raise ValueError('bounded target alias required')
  if type(host) is not str:raise ValueError('literal target address required')
  try:address=ipaddress.ip_address(host)
  except ValueError as error:raise ValueError('literal target address required') from error
  if str(address)!=host:raise ValueError('canonical literal target address required')
  if type(port) is not int or not 0<port<65536:raise ValueError('target port must be integer1..65535')
  if type(user) is not str or re.fullmatch('[A-Za-z_][A-Za-z0-9_-]{0,31}',user) is None:raise ValueError('exact target user required')
  if type(timeout) not in (int,float) or not math.isfinite(timeout) or not 0<timeout<=600:raise ValueError('bounded target timeout required')
  for path in (identity_file,known_hosts_file):
   if not isinstance(path,(str,Path)) or not Path(path).is_absolute():raise ValueError('absolute credential reference required')

class RemoteIndeterminate(RuntimeError):pass

@dataclass(frozen=True)
class RemoteTarget:
 name:str
 host:str
 port:int
 user:str
 identity_file:Path=field(repr=False)
 known_hosts_file:Path=field(repr=False)
 timeout:float=120.0
 _keys:tuple=field(init=False,repr=False)
 _ssh:object=field(init=False,repr=False)
 identity:str=field(init=False)
 def __post_init__(self):
  validate_target_fields(self.name,self.host,self.port,self.user,self.identity_file,self.known_hosts_file,self.timeout)
  keys=[]
  for key in ('identity_file','known_hosts_file'):
   path=Path(getattr(self,key));body=_private(path);object.__setattr__(self,key,path);keys.append(sha256(body).hexdigest())
  object.__setattr__(self,'_keys',tuple(keys));object.__setattr__(self,'timeout',float(self.timeout))
  ssh=NamedCommand('remote-ssh',('/usr/bin/ssh',),timeout=120);object.__setattr__(self,'_ssh',ssh)
  value=['bw.remote-target.v1',self.name,self.host,self.port,self.user,str(self.identity_file),str(self.known_hosts_file),keys,self.timeout,ssh.binary_sha256]
  object.__setattr__(self,'identity',sha256(_json(value)).hexdigest())
 @property
 def resource_identity(self):
  # Alias, user, credential and timeout changes must not bypass target ownership.
  return sha256(_json(['bw.remote-endpoint.v1',self.host,self.port])).hexdigest()
 def check(self):
  self._ssh.check()
  if tuple(sha256(_private(p)).hexdigest() for p in (self.identity_file,self.known_hosts_file))!=self._keys:raise ValueError('target credential/host identity changed')
 def argv(self,source):
  self.check()
  return ['/usr/bin/ssh','-F','/dev/null','-T','-i',str(self.identity_file),'-p',str(self.port),
   *[item for option in ['BatchMode=yes','IdentitiesOnly=yes','IdentityAgent=none','ForwardAgent=no','ClearAllForwardings=yes','StrictHostKeyChecking=yes','GlobalKnownHostsFile=/dev/null','UserKnownHostsFile='+str(self.known_hosts_file),'ProxyCommand=none','PermitLocalCommand=no','ControlMaster=no','ControlPath=none','ConnectTimeout=5','ServerAliveInterval=5','ServerAliveCountMax=2'] for item in ('-o',option)],
   self.user+'@'+self.host,'exec /usr/bin/python3 -c '+shlex.quote(source)]

@dataclass(frozen=True)
class RemoteResult:
 operation_id:str
 plan_sha256:str
 disposition:str
 exit_code:int|None
 stdout:bytes
 stderr:bytes
 elapsed_seconds:float
 receipt_sha256:str

class RemoteTransport:
 def __init__(self,root,target):
  if not isinstance(target,RemoteTarget):raise ValueError('host RemoteTarget required')
  self.root=_directory(root);self.target=target
  self.helper=Path(__file__).with_name('remote_guest.py').read_text();self.helper_sha256=sha256(self.helper.encode()).hexdigest()
 def intent(self,operation_id,plan_sha256,command,*,stdin=b''):
  if type(operation_id) is not str or not _ID.fullmatch(operation_id):raise ValueError('bounded original operation ID required')
  if type(plan_sha256) is not str or not _HEX.fullmatch(plan_sha256):raise ValueError('exact original plan hash required')
  if type(command) is not str or not command or '\0' in command or len(command.encode())>16384:raise ValueError('bounded remote command required')
  if type(stdin) is not bytes or len(stdin)>4*1024*1024:raise ValueError('bounded exact stdin bytes required')
  value=dict(schema=1,kind='bw.remote-command-intent.v1',operation_id=operation_id,plan_sha256=plan_sha256,target_identity=self.target.identity,helper_sha256=self.helper_sha256,command=command,timeout=self.target.timeout)
  if stdin:value.update(schema=2,kind='bw.remote-command-intent.v2',stdin_b64=base64.b64encode(stdin).decode())
  return value
 def record_intent(self,intent):
  try:expected=self.intent(intent['operation_id'],intent['plan_sha256'],intent['command'],stdin=self._stdin(intent))
  except (TypeError,KeyError) as error:raise ValueError('invalid remote intent') from error
  if expected!=intent:raise ValueError('different remote intent/target')
  folder=_directory(self.root/intent['operation_id']);fd=os.open(folder/'lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
  with os.fdopen(fd,'r+b') as lock:
   i=os.fstat(lock.fileno())
   if not stat.S_ISREG(i.st_mode) or i.st_uid!=os.getuid() or i.st_nlink!=1 or i.st_mode&0o077:raise ValueError('invalid remote intent lock')
   fcntl.flock(lock,fcntl.LOCK_EX);path=folder/'intent.json'
   if path.exists() or path.is_symlink():
    if json.loads(_private(path))!=intent:raise ValueError('operation has different original intent')
    return False
   _write(path,intent);return True
 def _decode(self,intent,response):
  keys={'schema','operation_id','request_sha256','disposition','exit_code','stdout_b64','stderr_b64','elapsed_seconds','command_pid','worker_pid'}
  if type(response) is not dict or set(response)!=keys or type(response['schema']) is not int or response['schema']!=1 or response['operation_id']!=intent['operation_id'] or response['request_sha256']!=sha256(self._request(intent)).hexdigest():raise ValueError('remote acknowledgment has wrong original binding')
  if response['disposition'] not in ('exited','timeout','output_limit','spawn_error'):raise ValueError('invalid remote disposition')
  code=response['exit_code']
  if code is not None and (type(code) is not int or not -255<=code<=255):raise ValueError('remote exit status is not exact')
  if (response['disposition']=='spawn_error')!=(code is None):raise ValueError('inconsistent remote process result')
  for field in ('worker_pid','command_pid'):
   pid=response[field]
   if pid is not None and (type(pid) is not int or pid<=0):raise ValueError('invalid remote process identity')
  if response['worker_pid'] is None or (response['command_pid'] is None)!=(response['disposition']=='spawn_error'):raise ValueError('missing remote process identity')
  elapsed=response['elapsed_seconds']
  if type(elapsed) not in (int,float) or not math.isfinite(elapsed) or elapsed<0:raise ValueError('invalid remote timing')
  stdout=base64.b64decode(response['stdout_b64'],validate=True);stderr=base64.b64decode(response['stderr_b64'],validate=True)
  if max(len(stdout),len(stderr))>1024*1024:raise ValueError('remote output exceeds limit')
  return RemoteResult(intent['operation_id'],intent['plan_sha256'],response['disposition'],code,stdout,stderr,float(elapsed),sha256(_json(response)).hexdigest())
 @staticmethod
 def _stdin(intent):
  value=base64.b64decode(intent.get('stdin_b64',''),validate=True)
  if len(value)>4*1024*1024:raise ValueError('stdin exceeds bound')
  return value
 def _request(self,intent):
  value=dict(schema=intent['schema'],operation_id=intent['operation_id'],command=intent['command'],timeout=intent['timeout'])
  if intent['schema']==2:value['stdin_b64']=intent['stdin_b64']
  return _json(value)
 def read_receipt(self,operation_id,plan_sha256,command,*,stdin=b''):
  intent=self.intent(operation_id,plan_sha256,command,stdin=stdin);folder=self.root/operation_id
  if not (folder/'intent.json').exists():raise RemoteIndeterminate('original remote receipt is absent; no resend')
  if json.loads(_private(folder/'intent.json'))!=intent:raise ValueError('operation has different original intent')
  if not (folder/'receipt.json').exists():raise RemoteIndeterminate('remote effect is unresolved; inspect original operation, no resend')
  try:return self._decode(intent,json.loads(_private(folder/'receipt.json')))
  except Exception as error:raise RemoteIndeterminate('Retained remote outcome is invalid; original effect remains unresolved') from error
 def _ownership(self):
  from .remote_ownership import TargetOwnership
  base=Path.home()/'.local/state/branchwrite'
  base.parent.mkdir(parents=True,exist_ok=True)
  base.mkdir(mode=0o700,exist_ok=True);info=base.lstat()
  if not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode&0o022:raise ValueError('owned non-writable app state container required')
  return TargetOwnership(base/'remote-targets',self.target.resource_identity)
 def _validate_durable_outcome(self,folder,intent):
  expected={'schema','kind','operation_id','plan_sha256','target_identity','helper_sha256','command','timeout'}
  if type(intent) is dict and intent.get('schema')==2:expected=expected|{'stdin_b64'}
  if (type(intent) is not dict or set(intent)!=expected or type(intent['schema']) is not int or intent['schema'] not in (1,2)
      or intent['kind']!='bw.remote-command-intent.v'+str(intent['schema']) or not _ID.fullmatch(intent['operation_id'])
      or any(type(intent[k]) is not str or not _HEX.fullmatch(intent[k]) for k in ('plan_sha256','target_identity','helper_sha256'))):raise ValueError('invalid original transport intent')
  if type(intent['command']) is not str or not intent['command'] or len(intent['command'].encode())>16384:raise ValueError('invalid original command')
  if type(intent['timeout']) not in (int,float) or not math.isfinite(intent['timeout']) or not 0<intent['timeout']<=600:raise ValueError('invalid original timeout')
  self._stdin(intent)
  self._decode(intent,json.loads(_private(folder/'receipt.json')))
  return True
 def run(self,operation_id,plan_sha256,command,*,stdin=b''):
  intent=self.intent(operation_id,plan_sha256,command,stdin=stdin);folder=self.root/operation_id
  # Replaying an existing known receipt is local. An unresolved original intent
  # is never dispatched again, even when the target is currently otherwise idle.
  if (folder/'intent.json').exists():return self.read_receipt(operation_id,plan_sha256,command,stdin=stdin)
  args=self.target.argv(self.helper)
  from .remote_ownership import RemoteTargetBusy
  with self._ownership().hold() as held:
   try:held.check_available(self._validate_durable_outcome)
   except RemoteIndeterminate as error:raise RemoteTargetBusy('Target has an unresolved prior operation; inspect its original receipt before new work') from error
   if not self.record_intent(intent):return self.read_receipt(operation_id,plan_sha256,command,stdin=stdin)
   held.reserve(folder/'intent.json',intent)
   result=self._send(intent,args)
   held.complete(self._validate_durable_outcome)
   return result
 def _send(self,intent,args):
  operation_id=intent['operation_id'];request=self._request(intent);started=time.monotonic()
  try:
   with tempfile.TemporaryFile() as stream:
    stream.write(request);stream.seek(0)
    p=subprocess.Popen(args,stdin=stream,stdout=subprocess.PIPE,stderr=subprocess.PIPE,close_fds=True,start_new_session=True,env=dict(PATH='/usr/bin:/bin',LANG='C.UTF-8',LC_ALL='C.UTF-8',HOME='/nonexistent'))
    stdout,stderr,timed_out,limited,_=Executor._capture(p,started+self.target.timeout+15,4*1024*1024)
   if p.returncode!=0 or timed_out or limited:raise RemoteIndeterminate('SSH did not produce an acknowledged remote outcome; no resend')
   response=json.loads(stdout);result=self._decode(intent,response)
   _write(self.root/operation_id/'receipt.json',response);return result
  except RemoteIndeterminate:raise
  except Exception as error:raise RemoteIndeterminate('original remote operation requires reconciliation; no resend') from error
