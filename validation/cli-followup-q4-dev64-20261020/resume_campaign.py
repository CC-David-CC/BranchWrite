from pathlib import Path
import hashlib,json,os,subprocess,time,traceback
from branchwrite.run_report import continuation_context,read_report
root=Path(__file__).parent;state=root/'run';exe=root.parent/'venv/bin/branchwrite'
before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (state/'cow-operations').glob('*.json')}
env=dict(os.environ,BW_COW_API_KEY=(root/'operator-test-key.txt').read_text().strip(),PYTHONDONTWRITEBYTECODE='1');env.pop('PYTHONPATH',None)
start=time.monotonic();report=dict(status='RUNNING',controller_pid=os.getpid(),original_run=str(state),action='resume original retained run, never a new user task')
def save():
 report['elapsed_seconds']=time.monotonic()-start;p=root/'resume-result.tmp';p.write_text(json.dumps(report,indent=2)+'\n');os.replace(p,root/'resume-result.json')
save()
try:
 with (root/'resume-stdout.json').open('xb') as out,(root/'resume-stderr.txt').open('xb') as err:
  p=subprocess.Popen([str(exe),'resume',str(state),'--max-steps','2048'],cwd=root,env=env,stdout=out,stderr=err,start_new_session=True);report['client_pid']=p.pid;save()
  while p.poll() is None:
   time.sleep(1)
   if int(time.monotonic()-start)%30==0:save();print(json.dumps(dict(phase='retained-followup-resume',pid=p.pid,elapsed=report['elapsed_seconds'])),flush=True)
 result=json.loads((root/'resume-stdout.json').read_text());report['client_exit']=p.returncode;assert p.returncode==0 and result['verified'] is True,result
 after={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (state/'cow-operations').glob('*.json')}
 assert all(after.get(k)==v for k,v in before.items()),'original completed requests changed'
 report.update(status='CLIENT_PASS_PENDING_INDEPENDENT_BROWSER',original_completed_journals_unchanged=True,new_model_operations=len(set(after)-set(before)),canonical_report=read_report(state),context=continuation_context(state,json.loads((root/'connection.json').read_text())),workspace=str(state/'world/workspace'))
except BaseException as error:report.update(status='NEEDS_INSPECTION',error=repr(error),traceback=traceback.format_exc());raise
finally:save();print(json.dumps({k:v for k,v in report.items() if k not in ['canonical_report','traceback']}),flush=True)
