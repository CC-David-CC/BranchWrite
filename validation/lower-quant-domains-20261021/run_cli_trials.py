
"""Run actual installed BW CLI trials; never import the inference backend.

Same public prompts and fixed acceptance rules as Q4. Each trial is a fresh
owned project. A CLI completion is provisional until artifact/vision audits.
Keys are provided through the child environment, never command lines/results.
An interrupted original operation is retained, never resent with a new ID.
"""
from pathlib import Path
import argparse,hashlib,json,os,signal,subprocess,time,urllib.request,traceback

def write(path,value):
 temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n');os.replace(temp,path)

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);parser.add_argument('--source',type=Path,required=True);parser.add_argument('--variant',choices=['iq2','iq3'],required=True);parser.add_argument('--server',type=Path,required=True);parser.add_argument('--domains',nargs='+',default=['cad','pdf','blender','code']);args=parser.parse_args()
 os.umask(0o077);out=args.root/args.variant;out.mkdir(mode=0o700,exist_ok=True)
 key=(args.server/'api-key.txt').read_text().strip();env=dict(os.environ,BW_COW_API_KEY=key,BW_COW_CONNECTION=str(out/'connection.json'),PYTHONDONTWRITEBYTECODE='1');env.pop('PYTHONPATH',None)
 exe=args.root/'client314/bin/branchwrite'
 def status():
  req=urllib.request.Request('http://10.0.7.95:8099/cow/status',headers={'Authorization':'Bearer '+key})
  with urllib.request.urlopen(req,timeout=15) as response:return json.load(response)
 deadline=time.monotonic()+300
 while True:
  try:status();break
  except OSError:
   if time.monotonic()>deadline:raise TimeoutError('server readiness')
   time.sleep(2)
 with (out/'connect.log').open('w') as f:subprocess.run([str(exe),'connect','http://10.0.7.95:8099'],env=env,check=True,stdout=f,stderr=subprocess.STDOUT)
 profile=json.loads((args.server/'profile.json').read_text());write(out/'profile-summary.json',{k:profile[k] for k in ['model_contract_id','execution_profile_id','model_path','hardware','native_build','model_files','execution']})
 for domain in args.domains:
  trial=out/domain
  if trial.exists():raise RuntimeError('Trial already exists; reconcile original, never silently resend: '+str(trial))
  trial.mkdir(mode=0o700);project=trial/'project';project.mkdir(mode=0o700);state=trial/'state'
  prompt=args.source/'examples/prompts'/({'cad':'build123d','blender':'blender','pdf':'pdf','code':'code'}[domain]+'.txt')
  (trial/'prompt.txt').write_bytes(prompt.read_bytes())
  cmd=[str(exe),'code',str(project),'--project-files','--connection',str(out/'connection.json'),'--state',str(state),'--branch','bw-'+args.variant+'-'+domain+'-20261021','--sampler','greedy','--max-steps','2048','--task-file',str(prompt)]
  if domain in ('cad','blender'):cmd+=['--'+domain+'-config',str(args.root/(domain+'-config.json'))]
  record=dict(status='RUNNING',variant=args.variant,domain=domain,argv=cmd,prompt_sha256=hashlib.sha256(prompt.read_bytes()).hexdigest(),operator_candidate_edits=0,sampler='greedy',client_source=subprocess.check_output(['git','rev-parse','HEAD'],cwd=args.source,text=True).strip(),started_unix=time.time(),before=status(),notes='fresh project per domain; historical Q4 controls had different hardware/history; not a controlled speed comparison')
  started=time.monotonic();last=0;write(trial/'result.json',record)
  with (trial/'stdout.json').open('w') as stdout,(trial/'stderr.log').open('w') as stderr:
   process=subprocess.Popen(cmd,cwd=project,env=env,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,start_new_session=True);record['client_pid']=process.pid
   while process.poll() is None:
    now=time.monotonic();record['elapsed_seconds']=now-started
    if now-last>=30:
     write(trial/'result.json',record);write(args.root/'heartbeat.json',dict(variant=args.variant,domain=domain,client_pid=process.pid,seconds=now-started,last_output_bytes=(trial/'stderr.log').stat().st_size));print(json.dumps(dict(variant=args.variant,domain=domain,seconds=round(now-started,1),client_pid=process.pid)),flush=True);last=now
    if now-started>1800:
     record['status']='TIMEOUT_ORIGINAL_RECEIPTS_RETAINED';os.killpg(process.pid,signal.SIGTERM)
     try:process.wait(timeout=20)
     except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=10)
     break
    time.sleep(1)
  record.update(exit_code=process.returncode,elapsed_seconds=time.monotonic()-started)
  try:record['after']=status()
  except Exception as e:record['status_error']=repr(e)
  if record['status']=='RUNNING':
   try:
    result=json.loads((trial/'stdout.json').read_text());record['client_result']=result
    record['status']='CLI_REPORTED_COMPLETE_PENDING_AUDIT' if process.returncode==0 and result.get('verified') is True and result.get('status')=='complete' else 'CLI_FAILED'
   except Exception as e:record.update(status='CLI_ERROR',parse_error=repr(e))
  for f in ['stdout.json','stderr.log']:
   raw=(trial/f).read_text()
   if key in raw:(trial/f).write_text(raw.replace(key,'[REDACTED]'));record['credential_output_redacted']=True
  write(trial/'result.json',record);print(json.dumps({k:v for k,v in record.items() if k in ['status','variant','domain','elapsed_seconds','exit_code']}),flush=True)
  if record['status']=='TIMEOUT_ORIGINAL_RECEIPTS_RETAINED':raise RuntimeError('Stopped expansion after timeout; original operation must be inspected')
if __name__=='__main__':main()
