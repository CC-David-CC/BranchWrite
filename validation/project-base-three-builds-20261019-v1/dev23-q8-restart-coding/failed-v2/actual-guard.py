import atexit,importlib.abc,json,os,sys
from pathlib import Path
blocked={'context_time_travel','serve','torch','llama_cpp'}
blocked_paths=('/home/dflanag3/models','/home/dflanag3/src/Strata','/home/dflanag3/spatial-artifacts/cow-vision-20261016-v1','/dev/nvidia','/dev/dri','/home/dflanag3/src/branchwrite-shell-admission-20261019','/home/dflanag3/src/branchwrite-real-repository-20261019','/home/dflanag3/src/branchwrite-prefix-admission-20261019','/home/dflanag3/src/branchwrite-project-admission-20261019','/home/dflanag3/src/branchwrite-inline-task-20261019','/home/dflanag3/src/branchwrite-client-package-20261019','/home/dflanag3/src/branchwrite-coding-entrypoint-20261019','/home/dflanag3/src/branchwrite-grammar-client-20261019')
violations=[]
class NoNative(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.split('.')[0] in blocked:
   violations.append(dict(kind='import',name=fullname));raise ImportError('server/native implementation forbidden on client: '+fullname)
sys.meta_path.insert(0,NoNative())
def audit(event,args):
 if event in ('open','os.listdir','os.scandir') and args and isinstance(args[0],(str,bytes)):
  path=os.path.abspath(os.fsdecode(args[0]))
  if any(path==prefix or path.startswith(prefix+'/') or (prefix=='/dev/nvidia' and path.startswith(prefix)) for prefix in blocked_paths):
   violations.append(dict(kind='file',path=path));raise PermissionError('model/server/GPU file access forbidden on client')
 if event=='subprocess.Popen':
  path=str(Path(os.fsdecode(args[0])).resolve())
  if path not in {str(Path(sys.executable).resolve()),'/usr/bin/prlimit','/usr/bin/bwrap'}:
   violations.append(dict(kind='process',path=path));raise PermissionError('unregistered client subprocess executable')
sys.addaudithook(audit)
def done():
 result=dict(schema=1,layout='trusted-host-cli-with-audit-and-isolated-tools',hostname=os.uname().nodename,python=sys.version.split()[0],native_modules_loaded=sorted(blocked.intersection(sys.modules)),native_file_and_process_audit=True,violations=violations,branchwrite_modules={k:str(getattr(v,'__file__','')) for k,v in sys.modules.items() if k=='branchwrite' or k.startswith('branchwrite.')},sys_path=list(sys.path),scope='Python audit of trusted CLI; not an adversarial OS security proof. Browser/candidate execution retains its separate OS sandbox.')
 Path(os.environ['BW_CLIENT_PROOF']).write_text(json.dumps(result,indent=2)+'\n')
atexit.register(done)

BW_AUDIT_ACTIVE=True

if os.environ.get('BW_ROOT_REPLY_FAULT')=='1':
 from branchwrite.cow_client import HTTPTransport
 original_request=HTTPTransport.request
 def lose_root(self,method,path,body=None,**kw):
  response=original_request(self,method,path,body,**kw)
  if method=='POST' and path=='/cow/text/context':
   events=list(response.events);complete=[e for e in events if e.get('event')=='complete']
   assert len(complete)==1
   Path(os.environ['BW_ROOT_OBSERVED']).write_text(json.dumps(complete[0],indent=2)+'\n')
   done()
   os._exit(92)
  return response
 HTTPTransport.request=lose_root
