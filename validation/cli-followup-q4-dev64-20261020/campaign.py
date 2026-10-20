from pathlib import Path
import hashlib,json,os,subprocess,time,traceback
from branchwrite.run_report import continuation_context,read_report
root=Path(__file__).parent;exe=root.parent/'venv/bin/branchwrite';repo=Path('/home/dflanag3/src/branchwrite-documents-20261020');prompt=repo/'examples/prompts/followup.txt';project=root/'project';state=root/'run';assert not state.exists();original=(project/'index.html').read_bytes()
env=dict(os.environ,BW_COW_API_KEY=(root/'operator-test-key.txt').read_text().strip(),PYTHONDONTWRITEBYTECODE='1');env.pop('PYTHONPATH',None)
argv=[str(exe),'code',str(project),'--project-files','--task-file',str(prompt),'--connection',str(root/'connection.json'),'--state',str(state),'--branch','bw-followup-dev64-20261020-v1','--from-branch','bw-code-dev62-20261020','--sampler','greedy','--max-steps','2048']
report=dict(status='RUNNING',controller_pid=os.getpid(),argv=argv,prompt_sha256=hashlib.sha256(prompt.read_bytes()).hexdigest(),source_sha256=hashlib.sha256(original).hexdigest(),operator_candidate_edits=0,scope='new installed dev64 task from actual earlier Q4 code context on restored original8099; original source preserved')
start=time.monotonic()
def save():
 report['elapsed_seconds']=time.monotonic()-start;p=root/'result.tmp';p.write_text(json.dumps(report,indent=2)+'\n');os.replace(p,root/'result.json')
save()
try:
 with (root/'stdout.json').open('xb') as out,(root/'stderr.txt').open('xb') as err:
  child=subprocess.Popen(argv,cwd=root,env=env,stdout=out,stderr=err,start_new_session=True);report['client_pid']=child.pid;save()
  while child.poll() is None:
   time.sleep(1)
   if time.monotonic()-start-report.get('last_heartbeat',0)>=30:
    report['last_heartbeat']=time.monotonic()-start;save();print(json.dumps(dict(phase='actual-cli-followup',elapsed=report['elapsed_seconds'],pid=child.pid)),flush=True)
   if time.monotonic()-start>1200:report['status']='OBSERVATION_LIMIT_ORIGINAL_CLIENT_LIVE';save()
 report['client_exit']=child.returncode;assert child.returncode==0,(root/'stderr.txt').read_text()
 result=json.loads((root/'stdout.json').read_text());assert result['status']=='complete' and result['verified'] is True
 report['canonical_report']=read_report(state);report['context']=continuation_context(state,json.loads((root/'connection.json').read_text()))
 assert (project/'index.html').read_bytes()==original
 workspace=state/'world/workspace';raw=(workspace/'index.html').read_bytes();assert raw!=original
 report.update(status='CLIENT_PASS_PENDING_INDEPENDENT_BROWSER',workspace=str(workspace),html_sha256=hashlib.sha256(raw).hexdigest(),original_source_unchanged=True)
except BaseException as error:
 report.update(status='NEEDS_INSPECTION',error=repr(error),traceback=traceback.format_exc());raise
finally:save();print(json.dumps({k:v for k,v in report.items() if k not in ['canonical_report','traceback']}),flush=True)
