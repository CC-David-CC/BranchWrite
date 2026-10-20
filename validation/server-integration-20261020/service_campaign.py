"""Owned single-GPU trial. Observation timeout never settles or kills work."""
from pathlib import Path
import json,os,signal,subprocess,time,traceback,urllib.request,hashlib
out=Path(__file__).parent;trial=out/'server';live=Path('/home/dflanag3/spatial-artifacts/branchwrite-dev29-live-q4-20261020')
oldroot=Path('/home/dflanag3/src/context-cow-client-setup-20261020');newroot=Path('/home/dflanag3/src/context-cow-consumed-pause-20261020')
python='/home/dflanag3/src/Strata/.venv/bin/python';deps='/home/dflanag3/spatial-artifacts/grammar-first-20261016-v1/deps'
r=dict(status='RUNNING',phase='PREFLIGHT',controller_pid=os.getpid(),started=time.time(),original_stopped=False)
def save():
 r['updated']=time.time();temp=out/'service-result.tmp';temp.write_text(json.dumps(r,indent=2)+'\n');os.replace(temp,out/'service-result.json')
def status(runtime,port):
 request=urllib.request.Request('http://10.0.7.68:'+str(port)+'/cow/status',headers={'Authorization':'Bearer '+(runtime/'api-key.txt').read_text().strip()})
 with urllib.request.urlopen(request,timeout=5) as f:return json.load(f)
def alive(pid):
 try:return Path('/proc/'+str(pid)+'/stat').read_text().split()[2]!='Z'
 except FileNotFoundError:return False
def quiet(row):return not any(row['active_per_gpu'].values()) and row['queued']==0 and row['pending_branches']==0
def environment(root,runtime):
 profile=json.loads((runtime/'profile.json').read_text());env=os.environ.copy()
 for key in list(env):
  if key.startswith(('STRATA_','CUDA_','NVIDIA_','GGML_')):env.pop(key)
 env.update(profile['execution']['environment']);env['PYTHONPATH']=':'.join(map(str,[root/'experimental/branching_context/src',root/'experimental/branching_context/scripts',root/'tools',root,Path(deps)]))
 env['PYTHONDONTWRITEBYTECODE']='1';env['BW_OWNED_SERVICE_CAMPAIGN']=str(out);return env
def launch(root,runtime):
 with (runtime/'server.log').open('ab') as log:return subprocess.Popen([python,str(runtime/'run_server.py')],cwd=root,env=environment(root,runtime),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
def stop_owned(pid,native,runtime,port):
 assert quiet(status(runtime,port)),'active requests must settle before service shutdown'
 command=Path('/proc/'+str(pid)+'/cmdline').read_bytes();assert str(runtime/'run_server.py').encode() in command,'service ownership changed'
 os.kill(pid,signal.SIGINT);started=time.monotonic()
 while alive(pid) or alive(native):
  if time.monotonic()-started>60:raise TimeoutError('owned shutdown still unsettled; inspect original handles, no automatic replacement')
  time.sleep(.5)
def ready(root,runtime,port,process):
 started=time.monotonic();last=started
 while True:
  if process.poll() is not None:raise RuntimeError('owned service exited '+str(process.returncode))
  try:return status(runtime,port)
  except (OSError,ValueError):pass
  if time.monotonic()-last>=30:
   print(json.dumps(dict(phase='waiting-for-service',port=port,pid=process.pid,elapsed=time.monotonic()-started)),flush=True);last=time.monotonic();save()
  if time.monotonic()-started>180:r['observation_deadline_exceeded']=True;save() # remain on the same live handle
  time.sleep(2)
save()
try:
 before=status(live,8099);assert quiet(before);assert before['ram']['dirty_bytes']==0
 old=json.loads((live/'server-pid.json').read_text());native=before['workers']['0']['pid']
 assert hashlib.sha256(Path('/proc/'+str(native)+'/exe').read_bytes()).hexdigest()=='ae62045f75a8e11ba9d01b4da301d3bb87fe4ff342bab0ea7edc57276377824e'
 r.update(original_pid=old['pid'],original_native_pid=native,before=before,phase='STOPPING_ORIGINAL');save()
 stop_owned(old['pid'],native,live,8099);r.update(original_stopped=True,phase='STARTING_CANDIDATE');save()
 child=launch(newroot,trial);r['candidate_pid']=child.pid;save();current=ready(newroot,trial,18099,child)
 assert current['workers']['0']['health']=='healthy' and quiet(current)
 r.update(candidate_ready=current,phase='CLIENT_CAMPAIGN');save()
 (out/'ready.json').write_text(json.dumps(dict(pid=child.pid,port=18099,source=str(newroot),profile_id=json.loads((trial/'profile.json').read_text())['execution_profile_id']))+'\n')
 while not (out/'client-finished.json').exists():
  if child.poll() is not None:raise RuntimeError('candidate service exited during original client campaign')
  print(json.dumps(dict(phase='CLIENT_CAMPAIGN',pid=child.pid,elapsed=time.time()-r['started'])),flush=True);save();time.sleep(30)
 final=json.loads((out/'client-finished.json').read_text());assert final.get('all_original_clients_exited') is True,'explicit original client exit evidence required'
 current=status(trial,18099);assert quiet(current),'candidate work remains unsettled'
 r.update(client_result=final,candidate_final_status=current,phase='STOPPING_CANDIDATE');save()
 stop_owned(child.pid,current['workers']['0']['pid'],trial,18099)
 restored=launch(oldroot,live)
 (live/'server-pid.json').write_text(json.dumps(dict(pid=restored.pid,source=str(oldroot),runtime=str(live),timestamp=time.time(),reason='restore unchanged service after checked CLI candidate campaign'),indent=2)+'\n')
 original=ready(oldroot,live,8099,restored);assert quiet(original)
 r.update(original_restored=True,original_restored_pid=restored.pid,original_restored_status=original,phase='COMPLETE',status='PASS' if final['status']=='PASS' else 'FAIL');save()
except BaseException as error:
 r.update(status='NEEDS_INSPECTION',error=repr(error),traceback=traceback.format_exc());save()
 # Leave a live/unknown service on its same identity. No blind finally restart.
 raise
