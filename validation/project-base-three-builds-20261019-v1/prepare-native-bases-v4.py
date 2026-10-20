from pathlib import Path
import json,subprocess,time,sys,threading,dataclasses
root=Path(__file__).parent;d=root/'comparison-service-v4'
sys.path.insert(0,'/home/dflanag3/src/branchwrite-model-reconciliation-20261019')
from branchwrite.cow_client import CowClient,OperationJournal
result=dict(status='RUNNING',scope='Administrative HTTP preparation of three native Project Bases; not a BranchWrite coding comparison',bases=[])
def write():
 q=root/'native-base-preparation-v4.partial';q.write_text(json.dumps(result,indent=2)+'\n');q.replace(root/'native-base-preparation-v4.json')
write();service=None;done=threading.Event()
def heartbeat():
 while not done.wait(30):print(json.dumps(dict(phase=result.get('phase'),elapsed_seconds=time.monotonic()-started)),flush=True)
started=time.monotonic();threading.Thread(target=heartbeat,daemon=True).start()
try:
 service=subprocess.Popen([sys.executable,'-B',str(d/'launch.py')],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 result['service_supervisor_pid']=service.pid;result['phase']='startup';write();deadline=time.monotonic()+240
 while not (d/'credentials.json').exists():
  if service.poll() is not None:raise RuntimeError('service exited during startup')
  if time.monotonic()>deadline:raise TimeoutError('service credential observation timeout')
  time.sleep(.25)
 c=json.loads((d/'credentials.json').read_text())
 client=CowClient.http('http://127.0.0.1:'+str(c['port']),journal=OperationJournal(root/'preparation-journal-v4'),api_key=c['api_key'],endpoint_pin='owned-llm60-project-base-comparison',timeout=3000)
 namespace=client.create_namespace('Project Base comparison','project-base-namespace-v4')['namespace_id']
 result['namespace_id']=namespace;write()
 for label in ['B-compact-selected','C-compact-examples','A-all-product-source']:
  result['phase']='prefill-'+label;write();text=(root/(label+'.system.txt')).read_text();t=time.monotonic()
  r=client.load_context('project-base-'+label.lower(),namespace,[dict(role='system',content=text)],'prepare-'+label.lower()+'-v4')
  result['bases'].append(dict(label=label,seconds=time.monotonic()-t,receipt=dataclasses.asdict(r.receipt),operation_id=r.operation_id));write()
 result['status']='PASS'
except BaseException as exc:
 result.update(status='FAIL',error=dict(type=type(exc).__name__,message=str(exc)))
finally:
 (d/'STOP').write_text('administrative preparation settled\n')
 if service is not None:
  try:result['service_exit']=service.wait(timeout=180)
  except subprocess.TimeoutExpired:result['shutdown']='still live; inspect original supervisor, do not restart'
 result['elapsed_seconds']=time.monotonic()-started;write();done.set()
raise SystemExit(result['status']!='PASS')
