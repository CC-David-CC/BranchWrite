from pathlib import Path
import os,json,hashlib,subprocess,time,socket,sys
from unittest.mock import patch
from branchwrite.cow_client import CowClient,OperationJournal,OperationIndeterminate
from branchwrite.model_dispatch import ModelAdapter,admit_model,step_model
from branchwrite.coding_cli import build_launch,save_launch,PROGRAM,_bytes
from branchwrite.records import RuntimeLog,encode
from branchwrite.kernel import FrameKernel,ResultContract
from branchwrite.language import parse,render
d=Path(__file__).parent
creds=json.loads((d/'credentials.json').read_text())
root=d.parent
if sys.argv[1]=='prepare':
 port=50447
 access=root/'client-access'
 argv=['ssh','-N','-o','BatchMode=yes','-o','ExitOnForwardFailure=yes','-o','IdentitiesOnly=yes','-o','StrictHostKeyChecking=yes','-o','HostKeyAlias=bw-llm60','-o','UserKnownHostsFile='+str(access/'known_hosts'),'-i',str(access/'id_ed25519'),'-L','127.0.0.1:'+str(port)+':127.0.0.1:'+str(creds['port']),'dflanag3@llm-60']
 with (d/'ssh.stderr').open('xb') as e:tunnel=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=e,start_new_session=True)
 (d/'tunnel.pid').write_text(str(tunnel.pid))
 endpoint='http://127.0.0.1:'+str(port)
 deadline=time.monotonic()+20
 while True:
  if tunnel.poll() is not None:raise RuntimeError('tunnel exited')
  try:
   with socket.create_connection(('127.0.0.1',port),timeout=1):break
  except OSError:
   if time.monotonic()>deadline:raise TimeoutError('tunnel startup')
   time.sleep(.1)
 (d/'endpoint').write_text(endpoint)
 c=CowClient.http(endpoint,journal=OperationJournal(d/'setup-journal'),api_key=creds['api_key'],endpoint_pin='ssh-pinned-owned-llm60-api')
 ns=c.create_namespace('Restart reconciliation probe','restart-probe-ns')['namespace_id']
 c.prepare('restart-probe',ns,'This is a bounded recovery test. Read the question and answer carefully. '*32,'restart-probe-root')
 project=d/'project';project.mkdir(exist_ok=True);(project/'app.py').write_text('pass\n')
 state=d/'state';state.mkdir(mode=0o700,exist_ok=True)
 connection=dict(endpoint_url=endpoint,endpoint_pin=c.endpoint_pin,model_contract_id=creds['model_contract_id'],execution_profile_id=creds['execution_profile_id'],eos_tokens=creds['eos_tokens'])
 launch=build_launch(project,'Describe the file.',connection,branch='restart-probe',read_paths=['app.py'],test_commands=['python3 -m unittest'])
 save_launch(state,launch);c.journal=OperationJournal(state/'cow-operations')
 adapter=ModelAdapter(c,run_id=launch['config']['run_id'],model_contract_id=creds['model_contract_id'],execution_profile_id=creds['execution_profile_id'],eos_tokens=tuple(creds['eos_tokens']))
 with RuntimeLog(state/'ledger') as log:
  k=FrameKernel(log);code=log.put_artifact(render(parse(PROGRAM)).encode());bindings={'host-config-sha256':('Text',hashlib.sha256(_bytes(launch['config'])).hexdigest())}
  inputs=log.put_artifact(encode(dict(schema=1,identity='restart-probe',bindings=bindings)))
  k.create_root('program','program-attempt',code,inputs,ResultContract('ProgramResult','record'))
  plan=adapter.freeze(c.head('restart-probe'),mode='ask',content='Explain why recording an operation ID matters.',request_tokens=16,max_requests=4,max_output_tokens=64)
  admit_model(k,adapter,'program',expected_epoch=0,child_id='model-flow',attempt_id='model-attempt',slot='proposal',next_pc=1,plan=plan)
  actual=c.transport.request
  def drop(method,path,body=None,**kwargs):
   result=actual(method,path,body,**kwargs)
   if method=='POST' and path=='/cow/text/ask':
    # Consume the response fully, then deliberately lose it at the client
    # boundary before journal publication. Server commitment remains genuine.
    events=list(result.events)
    complete=[e for e in events if e.get('event')=='complete'];assert len(complete)==1
    (d/'server-complete-observed.json').write_text(json.dumps(complete[0],indent=2)+'\n')
    raise OperationIndeterminate('injected lost committed reply')
   return result
  with patch.object(c.transport,'request',side_effect=drop):
   try:step_model(k,adapter,'model-flow')
   except OperationIndeterminate:pass
   else:raise AssertionError('lost acknowledgment did not leave pending work')
  op=next(f['dispatch'][0] for f in k.frames() if f['contract']==('COWNativeReceipt','record'))
 (d/'operation').write_text(op)
 hashes={str(p.relative_to(state/'ledger')):hashlib.sha256(p.read_bytes()).hexdigest() for p in (state/'ledger').rglob('*') if p.is_file()}
 (d/'ledger-before.json').write_text(json.dumps(hashes,sort_keys=True))
 record=c.journal.read(op);assert record['state']=='pending'
 (d/'PREPARED').write_text('producer request committed; client journal pending; client process exits now\n')
 print(json.dumps(dict(status='COMMITTED_REPLY_LOST',operation=op,client_pid=os.getpid())),flush=True)
elif sys.argv[1]=='verify':
 state=d/'state-v2';op=(d/'operation-v2').read_text();endpoint=(d/'endpoint').read_text()
 env=dict(os.environ,BW_COW_API_KEY=creds['api_key']);env.pop('PYTHONPATH',None)
 r=subprocess.run([sys.executable,'-B','-m','branchwrite','reconcile',str(state),'--operation-id',op],env=env,capture_output=True,text=True,timeout=30)
 (d/'reconcile.stdout').write_text(r.stdout);(d/'reconcile.stderr').write_text(r.stderr)
 assert r.returncode==0,(r.returncode,r.stderr)
 value=json.loads(r.stdout);assert value['operation_id']==op and not value['workflow_advanced']
 hashes={str(p.relative_to(state/'ledger')):hashlib.sha256(p.read_bytes()).hexdigest() for p in (state/'ledger').rglob('*') if p.is_file()}
 assert hashes==json.loads((d/'ledger-before-v2.json').read_text())
 c=CowClient.http(endpoint,journal=OperationJournal(state/'cow-operations'),api_key=creds['api_key'],endpoint_pin='ssh-pinned-owned-llm60-api')
 recovered=c.read_completed_generation(op);original=json.loads((d/'server-complete-observed.json').read_text())
 assert dict(recovered.receipt.raw)==original['receipt']
 assert {k:recovered.answer.get(k) for k in ('snapshot','tokens','text','thinking')}=={k:original['answer'].get(k) for k in ('snapshot','tokens','text','thinking')}
 (d/'recovered-answer.json').write_text(json.dumps(dict(recovered.answer),indent=2)+'\n')
 result=dict(status='BOUNDED_NATIVE_RESTART_CLI_RECONCILIATION_PASS',operation=op,output_tokens=len(recovered.answer['tokens']),answer_exact=True,receipt_exact=True,workflow_ledger_unchanged=True,reconcile_exit=r.returncode,client_pid=os.getpid(),scope='Lost reply injected before client journal completion; actual server/native restart; real remote installed CLI; counters verified separately')
 (d/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result),flush=True)
