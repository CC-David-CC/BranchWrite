"""Real CPU weight updates through both CLIs; generated model, controlled tasks."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,sys,threading,time

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--pcc-root',type=Path,required=True)
parser.add_argument('--native-executable',type=Path,required=True)
parser.add_argument('--workdir',type=Path,required=True,help='New private output directory; existing directories are refused.')
args=parser.parse_args()
pcc=args.pcc_root.resolve(strict=True);bw=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(bw),str(pcc)]
from serve.cow_http import make_server
from tools.pcc_lessons import LessonService,NativeRunner
from tests.lesson_flow_harness import task
from branchwrite.lesson_cli import digest

root=args.workdir.absolute();root.mkdir(mode=0o700,parents=True,exist_ok=False)
from experimental.native_training.make_cpu_fixture import make_fixture
model=make_fixture(root/'tiny-byte-fixture.gguf');binary=args.native_executable.resolve(strict=True)
base_hash=hashlib.sha256(model.read_bytes()).hexdigest();contract=hashlib.sha256(b'pcc-byte-fixture-v1'+model.read_bytes()).hexdigest()
service=None;server=None;thread=None
def phase(name,**extra):
 value=dict(phase=name,time=time.time(),**extra);temp=root/'phase.tmp';temp.write_text(json.dumps(value)+'\n');temp.replace(root/'phase.json');print(json.dumps(value),flush=True)
def command(argv,name,env):
 with (root/(name+'.stdout')).open('w') as out,(root/(name+'.stderr')).open('w') as err:
  p=subprocess.run(list(map(str,argv)),stdout=out,stderr=err,env=env,timeout=240)
 (root/(name+'.exit')).write_text(str(p.returncode)+'\n');assert p.returncode==0,'Inspect '+name+'.stderr'
 return json.loads((root/(name+'.stdout')).read_text())
try:
 phase('native-cpu-service')
 runner=NativeRunner(dict(model=str(model),base_sha256=base_hash,executable=str(binary),devices=['CPU'],gpu_uuids=[],
   device_budget_bytes={'CPU':1024**3},reserve_bytes=16*1024**2))
 service=LessonService(root/'service',contract,lambda text:list(text.encode()),runner,max_tokens=32,max_steps=16)
 key='cpu-proof-'+os.urandom(16).hex()
 server=make_server(object(),api_key=key,training_service=service,connection_info=dict(model_contract_id=contract,execution_profile_id=digest({'cpu':'fixture'}),eos_tokens=[0]))
 thread=threading.Thread(target=server.serve_forever);thread.start();url='http://127.0.0.1:'+str(server.server_port)
 connection=dict(endpoint_url=url,endpoint_pin=digest({'url':url}),model_contract_id=contract,execution_profile_id=digest({'cpu':'fixture'}),eos_tokens=[0])
 connection_file=root/'connection.json';connection_file.write_text(json.dumps(connection));connection_file.chmod(0o600)
 env=dict(os.environ,PYTHONPATH=str(bw)+os.pathsep+str(pcc),BW_COW_API_KEY=key,COW_API_KEY=key)
 def bwcli(args,name):return command([sys.executable,'-m','branchwrite','lesson','--connection',connection_file,'--state-dir',root/'bw-requests',*args],name,env)
 def cowcli(args,name):return command([sys.executable,pcc/'tools/cow_cli.py','--url',url,'--state-dir',root/'cow-requests','lesson',*args],name,env)
 def wait(identity):
  deadline=time.monotonic()+180
  while True:
   value=service.job(identity)
   if value['state'] not in ('queued','running'):
    assert value['state']=='complete',value
    assert value['promoted'] is False
    return value
   if time.monotonic()>deadline:raise TimeoutError('Native CPU job '+identity)
   time.sleep(.05)
 phase('real-bw-failed-check-help-and-passing-check')
 states={}
 for name,factor in [('double',2),('triple',3),('quadruple',4),('quintuple',5)]:
  states[name]=task(root/name,connection,corrected=True,factor=factor,name=name,include_failed_check=True)
 def author(name,factor,*extra):
  return ['create','--corrected-state',states[name],'--prompt','Python '+name+'(n):','--completion',' '+str(factor)+'*n',
      '--title','Controlled '+name+' correction','--operation-id',name+'-lesson',*extra]
 phase('bw-one-command-single-example-update')
 first=bwcli(author('double',2,'--train-now','--learning-rate','.01'),'single-submit');single=wait(first['training']['job_id'])
 assert len(single['steps'])==1 and single['steps'][0]['examples']==1
 phase('queue-lessons-through-both-clis')
 second=bwcli(author('triple',3,'--queue'),'queue-triple')
 draft=bwcli(author('quadruple',4),'draft-quadruple')
 third=cowcli(['submit',draft['lesson_file'],'--operation-id','quadruple-lesson'],'queue-quadruple')
 fourth=bwcli(author('quintuple',5,'--queue'),'queue-quintuple')
 listing=bwcli(['list'],'pending-list');assert sum(row['pending'] for row in listing['lessons'])==3
 batch_args=['train','--pending','--operation-id','cpu-batch','--batch-size','2','--learning-rate','.01','--parent-job-id',single['job_id']]
 phase('bw-batch-default-covers-all-three-with-final-partial-batch')
 accepted=bwcli(batch_args,'batch-submit');batch=wait(accepted['job_id'])
 assert [step['examples'] for step in batch['steps']]==[2,1]
 assert all(step['after']<step['before'] for step in batch['steps'])
 phase('retry-frozen-selection-after-pending-queue-is-empty')
 assert bwcli(batch_args,'batch-retry')==accepted
 assert not any(row['pending'] for row in cowcli(['list'],'empty-pending')['lessons'])
 assert len(list((root/'service/runs').iterdir()))==2
 phase('cow-cli-direct-full-weight-update-and-continuation')
 identity=first['acceptance']['lesson_id']
 full_accept=cowcli(['train',identity,'--operation-id','cpu-full','--mode','full','--batch-size','1'],'full-submit')
 full=wait(full_accept['job_id'])
 continued_accept=cowcli(['train',identity,'--operation-id','cpu-full-next','--mode','full','--batch-size','1','--parent-job-id','cpu-full'],'full-next-submit')
 continued=wait(continued_accept['job_id'])
 phase('verify-native-candidate-reload')
 def evaluate(name,job,lesson_id,mode):
  record=json.loads((root/'service/operations'/(job+'.json')).read_text());candidate=record['candidate']
  example=service.lesson(lesson_id)['example']
  request=dict(model=str(model),base_sha256=base_hash,devices=['CPU'],mode='lora',rank=4,backprop_mode='standard',evaluate_only=True,
      examples=[example],learning_rate=.0001,device_budget_bytes={'CPU':1024**3},reserve_bytes=16*1024**2)
  if mode=='lora':request['initial_adapter']=candidate['candidate_path']
  else:request.update(model=candidate['candidate_path'],base_sha256=candidate['candidate_sha256'])
  path=root/(name+'-private.json');path.write_text(json.dumps(request)+'\n')
  result=command([binary,'--train',path],name,env)
  assert abs(result['losses'][0]-candidate['receipt']['steps'][-1]['after'])<=1e-6
  return dict(candidate_sha256=candidate['candidate_sha256'],loss=result['losses'][0])
 batch_record=json.loads((root/'service/operations/cpu-batch.json').read_text())
 reload_lora=evaluate('reload-lora','cpu-batch',batch_record['request']['lesson_ids'][-1],'lora')
 reload_full=evaluate('reload-full','cpu-full',identity,'full')
 continuation_record=json.loads((root/'service/operations/cpu-full-next.json').read_text())
 assert continuation_record['candidate']['base_sha256']==reload_full['candidate_sha256']
 assert hashlib.sha256(model.read_bytes()).hexdigest()==base_hash
 assert len(list((root/'service/runs').iterdir()))==4
 result=dict(status='PASS',scope='real native CPU single/batch/update/reload wiring through both CLIs and real BW tool boundaries',
    fixture='generated tiny hybrid GGUF with byte vocabulary; not a language-quality test',spontaneous_model_failure=False,
    gpu_used=False,promoted=False,base_unchanged=True,model_sha256=base_hash,executable_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
    single=single,batch=batch,full=full,full_continued=continued,lora_reload=reload_lora,full_reload=reload_full,
    duplicate_update_prevented=True,selected_batch_frozen=True,partial_final_batch=True,same_task_failure_and_repair=True)
 (root/'result.json').write_text(json.dumps(result,indent=2)+'\n');phase('complete',status='PASS');(root/'command.exit').write_text('0\n')
except BaseException as error:
 phase('failed',error=type(error).__name__+': '+str(error));(root/'command.exit').write_text('1\n');raise
finally:
 if server is not None:server.shutdown();server.server_close()
 if thread is not None:thread.join()
 if service is not None:service.close()
