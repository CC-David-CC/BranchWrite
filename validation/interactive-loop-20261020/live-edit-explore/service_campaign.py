import json,os,signal,subprocess,time,traceback,urllib.request
from pathlib import Path
out=Path(__file__).parent;trial=out/'server';live=Path('/home/dflanag3/spatial-artifacts/branchwrite-dev29-live-q4-20261020')
oldroot=Path('/home/dflanag3/src/context-cow-client-setup-20261020');newroot=Path('/home/dflanag3/src/context-cow-bw-fast-integration-20261020')
python='/home/dflanag3/src/Strata/.venv/bin/python';deps='/home/dflanag3/spatial-artifacts/grammar-first-20261016-v1/deps'
r=dict(status='RUNNING',pid=os.getpid(),started=time.time());stopped=False;child=None

def save():
 r['updated']=time.time();(out/'service-campaign.json').write_text(json.dumps(r,indent=2)+'\n')
def status(runtime,port):
 req=urllib.request.Request('http://10.0.7.68:'+str(port)+'/cow/status',headers={'Authorization':'Bearer '+(runtime/'api-key.txt').read_text().strip()})
 with urllib.request.urlopen(req,timeout=5) as f:return json.load(f)
def env_for(root,runtime):
 profile=json.loads((runtime/'profile.json').read_text());env=os.environ.copy()
 for k in list(env):
  if k.startswith(('STRATA_','CUDA_','NVIDIA_','GGML_')):env.pop(k)
 env.update(profile['execution']['environment'])
 env['PYTHONPATH']=':'.join(map(str,[root/'experimental/branching_context/src',root/'experimental/branching_context/scripts',root/'tools',root,Path(deps)]));return env

def alive(pid):
 try:return Path('/proc/'+str(pid)+'/stat').read_text().split()[2]!='Z'
 except FileNotFoundError:return False

def stop(pid,native):
 if alive(pid):os.kill(pid,signal.SIGINT)
 until=time.monotonic()+60
 while any(alive(p) for p in (pid,native)):
  if time.monotonic()>until:raise RuntimeError('owned service shutdown timed out')
  time.sleep(.5)

def launch(root,runtime):
 with (runtime/'server.log').open('ab') as log:
  return subprocess.Popen([python,str(runtime/'run_server.py')],cwd=root,env=env_for(root,runtime),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)

def ready(runtime,port,process):
 until=time.monotonic()+180
 while time.monotonic()<until:
  if process.poll() is not None:raise RuntimeError('service process exited '+str(process.returncode))
  try:return status(runtime,port)
  except Exception:time.sleep(3)
 raise TimeoutError('readiness observation expired; do not restart automatically')
try:
 before=status(live,8099);assert not any(before['active_per_gpu'].values()) and before['queued']==0 and before['pending_branches']==0
 old=json.loads((live/'server-pid.json').read_text());assert str(live).encode() in Path('/proc/'+str(old['pid'])+'/cmdline').read_bytes()
 r['before']=before;r['original_pid']=old['pid'];save();stop(old['pid'],before['workers']['0']['pid']);stopped=True
 child=launch(newroot,trial);r['candidate_pid']=child.pid;save();current=ready(trial,18099,child)
 r['candidate_ready']=current;r['phase']='CLIENT_CAMPAIGN';save()
 (out/'ready.json').write_text(json.dumps(dict(pid=child.pid,port=18099,source=str(newroot)))+'\n')
 end=time.monotonic()+3600
 while not (out/'client-finished.json').exists():
  if child.poll() is not None:raise RuntimeError('candidate server exited during client campaign')
  if time.monotonic()>end:raise TimeoutError('bounded client campaign deadline')
  print(json.dumps(dict(phase=r['phase'],pid=child.pid,elapsed=time.time()-r['started'])),flush=True);save();time.sleep(30)
 r['client_result']=json.loads((out/'client-finished.json').read_text());r['status']='PASS' if r['client_result']['status']=='PASS' else 'FAIL'
except BaseException as error:r.update(status='FAIL',error=repr(error),traceback=traceback.format_exc());raise
finally:
 if child is not None and child.poll() is None:
  try:
   current=status(trial,18099);r['candidate_final_status']=current
   stop(child.pid,current['workers']['0']['pid'])
  except Exception as error:r['candidate_cleanup_error']=repr(error)
 if stopped:
  restored=launch(oldroot,live)
  (live/'server-pid.json').write_text(json.dumps(dict(pid=restored.pid,source=str(oldroot),runtime=str(live),timestamp=time.time(),reason='restore unchanged server after combined integration client campaign'),indent=2)+'\n')
  r['restored_pid']=restored.pid
  try:r['original_restored_status']=ready(live,8099,restored);r['original_restored']=True
  except Exception as error:r['original_restore_error']=repr(error)
 r['finished']=time.time();save()
