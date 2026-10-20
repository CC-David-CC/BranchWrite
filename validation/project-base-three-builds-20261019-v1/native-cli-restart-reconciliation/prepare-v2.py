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
endpoint=(d/'endpoint').read_text()
c=CowClient.http(endpoint,journal=OperationJournal(d/'setup-journal'),api_key=creds['api_key'],endpoint_pin='ssh-pinned-owned-llm60-api')
ns=c.create_namespace('Restart reconciliation probe','restart-probe-ns')['namespace_id']
c.prepare('restart-probe-v2',ns,'This is a bounded recovery test. Read the question and answer carefully. '*32,'restart-probe-v2-root')
project=d/'project';project.mkdir(exist_ok=True);(project/'app.py').write_text('pass\n')
state=d/'state-v2';state.mkdir(mode=0o700,exist_ok=True)
connection=dict(endpoint_url=endpoint,endpoint_pin=c.endpoint_pin,model_contract_id=creds['model_contract_id'],execution_profile_id=creds['execution_profile_id'],eos_tokens=creds['eos_tokens'])
launch=build_launch(project,'Describe the file.',connection,branch='restart-probe-v2',read_paths=['app.py'],test_commands=['python3 -m unittest'])
save_launch(state,launch);c.journal=OperationJournal(state/'cow-operations')
adapter=ModelAdapter(c,run_id=launch['config']['run_id'],model_contract_id=creds['model_contract_id'],execution_profile_id=creds['execution_profile_id'],eos_tokens=tuple(creds['eos_tokens']))
with RuntimeLog(state/'ledger') as log:
 k=FrameKernel(log);code=log.put_artifact(render(parse(PROGRAM)).encode());bindings={'host-config-sha256':('Text',hashlib.sha256(_bytes(launch['config'])).hexdigest())}
 inputs=log.put_artifact(encode(dict(schema=1,identity='restart-probe-v2',bindings=bindings)))
 k.create_root('program','program-attempt',code,inputs,ResultContract('ProgramResult','record'))
 plan=adapter.freeze(c.head('restart-probe-v2'),mode='answer',request_tokens=16,max_requests=4,max_output_tokens=64)
 admit_model(k,adapter,'program',expected_epoch=0,child_id='model-flow',attempt_id='model-attempt',slot='proposal',next_pc=1,plan=plan)
 actual=c.transport.request
 def drop(method,path,body=None,**kwargs):
  result=actual(method,path,body,**kwargs)
  if method=='POST' and path=='/cow/text/answer':
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
(d/'operation-v2').write_text(op)
hashes={str(p.relative_to(state/'ledger')):hashlib.sha256(p.read_bytes()).hexdigest() for p in (state/'ledger').rglob('*') if p.is_file()}
(d/'ledger-before-v2.json').write_text(json.dumps(hashes,sort_keys=True))
record=c.journal.read(op);assert record['state']=='pending'
(d/'PREPARED').write_text('producer request committed; client journal pending; client process exits now\n')
print(json.dumps(dict(status='COMMITTED_REPLY_LOST',operation=op,client_pid=os.getpid())),flush=True)
