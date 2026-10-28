"""CLI recovery binds the existing ledger and exact original HTTP intent."""
import hashlib,json,os,subprocess,sys,unittest
from pathlib import Path
from collections import defaultdict
from unittest.mock import patch
import test_cow_client_flow as fixture
from branchwrite.coding_cli import build_launch,save_launch,PROGRAM,_bytes
from branchwrite.records import RuntimeLog,Artifact,encode,decode
from branchwrite.kernel import FrameKernel,ResultContract,CallSpec
from branchwrite.language import parse,render
from branchwrite.model_dispatch import ModelAdapter,admit_model,step_model
from branchwrite.cow_client import OperationIndeterminate,GenerationIndeterminate,CowClientError,_Response

class CodingReconciliationTests(unittest.TestCase):
 def setUp(self):
  self.case=fixture.CowClientFlowTests();self.addCleanup(self.case.doCleanups);self.case.setUp()
  self.client=self.case._client('http','cli-recovery')
  ns=self.client.create_namespace('CLI recovery','cli-recovery-ns')['namespace_id']
  self.prepared=self.client.prepare('cli-main',ns,'A useful task.','cli-recovery-root')
  self.case.models[0].plans=defaultdict(lambda:(257,))
  base=Path(self.case.temp.name);self.source=base/'project';self.source.mkdir();(self.source/'app.py').write_text('pass\n')
  self.state=base/'run';self.state.mkdir(mode=0o700)
  connection=dict(endpoint_url=self.client.endpoint_url,endpoint_pin=self.client.endpoint_pin,model_contract_id='flow-model',execution_profile_id='flow-profile',eos_tokens=[299])
  self.launch=build_launch(self.source,'Inspect the file.',connection,branch='cli-main',read_paths=['app.py'],test_commands=['python3 -m unittest'])
  save_launch(self.state,self.launch)
  # The real canonical ledger carries the same bound program/config digest.
  from branchwrite.cow_client import OperationJournal
  self.client.journal=OperationJournal(self.state/'cow-operations')
  self.adapter=ModelAdapter(self.client,run_id='cli-main',model_contract_id='flow-model',execution_profile_id='flow-profile',eos_tokens=(299,))
  with RuntimeLog(self.state/'ledger') as log:
   k=FrameKernel(log);code=log.put_artifact(render(parse(PROGRAM)).encode());bindings={'host-config-sha256':('Text',hashlib.sha256(_bytes(self.launch['config'])).hexdigest())}
   inputs=log.put_artifact(encode(dict(schema=1,identity='fixture-interpreter',bindings=bindings)))
   k.create_root('program','program-attempt',code,inputs,ResultContract('ProgramResult','record'))
 def pending(self,failed=False):
  if failed:self.case.models[0].plans={}
  with RuntimeLog(self.state/'ledger') as log:
   k=FrameKernel(log);plan=self.adapter.freeze(self.client.head('cli-main'),mode='answer',request_tokens=1,max_requests=4,max_output_tokens=4)
   admit_model(k,self.adapter,'program',expected_epoch=0,child_id='model-flow',attempt_id='model-attempt',slot='proposal',next_pc=1,plan=plan)
   if failed:
    with self.assertRaises(GenerationIndeterminate) as caught:step_model(k,self.adapter,'model-flow')
    self.assertEqual(caught.exception.operation_id,next(f['dispatch'][0] for f in k.frames() if f['contract']==('COWNativeReceipt','record')))
   else:
    actual=self.client.transport.request
    def drop(method,path,body=None,**kwargs):
     result=actual(method,path,body,**kwargs)
     if method=='POST' and path=='/cow/text/answer':raise OperationIndeterminate('lost committed reply')
     return result
    with patch.object(self.client.transport,'request',side_effect=drop):
     with self.assertRaises(OperationIndeterminate):step_model(k,self.adapter,'model-flow')
   return next(f['dispatch'][0] for f in k.frames() if f['contract']==('COWNativeReceipt','record'))
 def hashes(self):
  return {str(p.relative_to(self.state/'ledger')):hashlib.sha256(p.read_bytes()).hexdigest() for p in (self.state/'ledger').rglob('*') if p.is_file()}
 def invoke(self,op):
  return subprocess.run([sys.executable,'-B','-m','branchwrite','reconcile',str(self.state),'--operation-id',op],capture_output=True,text=True,env=dict(os.environ,BW_COW_API_KEY='cpu-flow-secret'),timeout=20)
 def diagnose(self,op):
  return subprocess.run([sys.executable,'-B','-m','branchwrite','diagnose',str(self.state),'--operation-id',op],capture_output=True,text=True,env=dict(os.environ,BW_COW_API_KEY='cpu-flow-secret'),timeout=20)
 def test_cli_restores_output_then_existing_step_resumes_without_new_work(self):
  op=self.pending();before=self.hashes();trace=list(self.case.trace);r=self.invoke(op)
  self.assertEqual(r.returncode,0,r.stderr);value=json.loads(r.stdout)
  self.assertEqual(value['operation_id'],op);self.assertFalse(value['workflow_advanced']);self.assertEqual(value['status'],'reconciled')
  self.assertEqual(self.hashes(),before);self.assertEqual(self.case.trace,trace)
  with RuntimeLog(self.state/'ledger') as log:
   k=FrameKernel(log)
   with patch.object(self.client.transport,'request',side_effect=AssertionError('recovered output is local')):
    self.assertEqual(step_model(k,self.adapter,'model-flow').status,'partial')
 def test_cli_refuses_operation_not_owned_by_pending_model_frame(self):
  before=self.hashes();trace=list(self.case.trace);r=self.invoke('unowned-operation')
  self.assertEqual(r.returncode,2);self.assertEqual(self.hashes(),before);self.assertEqual(self.case.trace,trace)
 def test_cli_refuses_live_workflow_writer(self):
  op=self.pending();before=self.hashes()
  with RuntimeLog(self.state/'ledger'):r=self.invoke(op)
  self.assertEqual(r.returncode,2);self.assertIn('busy',r.stderr.lower());self.assertEqual(self.hashes(),before)
 def test_cli_cannot_reconcile_a_tool_effect(self):
  with RuntimeLog(self.state/'ledger') as log:
   k=FrameKernel(log);code=log.put_artifact(b'tool');inputs=log.put_artifact(encode({}))
   k.spawn('program',expected_epoch=0,calls=(CallSpec('tool-child','tool-attempt','out','ACT',code,inputs,ResultContract('ToolOutcome','record')),),next_pc=1)
   k.dispatch('tool-child','owned-tool-operation',inputs)
  before=self.hashes();r=self.invoke('owned-tool-operation');self.assertEqual(r.returncode,2);self.assertEqual(self.hashes(),before)
 def test_self_consistent_changed_launch_rejected_before_network(self):
  op=self.pending();path=self.state/'coding-launch.json';v=json.loads(path.read_text());v['launch']['config']['grant']['edit_paths']=['app.py'];v['sha256']=hashlib.sha256(_bytes(v['launch'])).hexdigest();path.write_bytes(_bytes(v))
  before=self.hashes();trace=list(self.case.trace);r=self.invoke(op)
  self.assertEqual(r.returncode,2);self.assertEqual(self.hashes(),before);self.assertEqual(self.case.trace,trace)
 def test_failed_uncommitted_model_operation_stays_unresolved(self):
  op=self.pending(failed=True);before=self.hashes();trace=list(self.case.trace);r=self.invoke(op)
  self.assertEqual(r.returncode,4,r.stderr);self.assertEqual(self.hashes(),before);self.assertEqual(self.case.trace,trace)
 def test_diagnostic_reads_original_failure_without_advancing_or_replay(self):
  op=self.pending(failed=True);before=self.hashes();trace=list(self.case.trace)
  journal=self.client.journal.read(op);r=self.diagnose(op)
  self.assertEqual(r.returncode,0,r.stderr);value=json.loads(r.stdout)
  self.assertEqual(value['status'],'diagnostic');self.assertFalse(value['workflow_advanced'])
  self.assertFalse(value['durable_claim_verified'])
  self.assertEqual(value['operation_id'],op)
  self.assertEqual(value['diagnostic']['state'],'failed')
  self.assertEqual(value['diagnostic']['diagnostic_scope'],'coordinator-process-only')
  self.assertIsNotNone(value['diagnostic']['failure'])
  self.assertEqual(self.hashes(),before);self.assertEqual(self.case.trace,trace)
  self.assertEqual(self.client.journal.read(op),journal)
  self.assertEqual(self.invoke(op).returncode,4)
  self.assertEqual(self.client.journal.read(op),journal)
 def test_diagnostic_rejects_unowned_operation_before_network(self):
  before=self.hashes();trace=list(self.case.trace);r=self.diagnose('unowned-operation')
  self.assertEqual(r.returncode,2);self.assertEqual(self.hashes(),before);self.assertEqual(self.case.trace,trace)
 def test_diagnostic_refuses_live_workflow_writer(self):
  op=self.pending(failed=True);before=self.hashes()
  with RuntimeLog(self.state/'ledger'):r=self.diagnose(op)
  self.assertEqual(r.returncode,2);self.assertIn('busy',r.stderr.lower())
  self.assertEqual(self.hashes(),before)
 def test_diagnostic_client_rejects_a_different_operation(self):
  response=_Response(json_value=dict(operation_id='other',scope='coordinator-process',
   diagnostic_scope='coordinator-process-only',durable=False,branch='cli-main',
   state='failed',publication_retryable=False,failure=dict(type='Error',message='bad')))
  with patch.object(self.client.transport,'request',return_value=response):
   with self.assertRaises(CowClientError):self.client.operation_diagnostic('original')

 def restart_fixture_server(self, *, evict_checkpoints=False):
  # Actual HTTP server/coordinator replacement on the same endpoint. This is a
  # CPU integration fixture, not process-kill or GPU qualification.
  from context_time_travel.coordinator import ContextCoordinator
  from serve.cow_adapter import CowAdapter
  from serve.cow_http import make_server
  from serve.cow_text_adapter import CowTextAdapter
  import threading
  c=self.case;old=c.coordinator;config=old.config;factory=old._factory
  host,port=c.server.server_address[:2]
  c._stop_server();c.server.server_close();old.close()
  if evict_checkpoints:
   checkpoint_dir=Path(c.temp.name)/'checkpoints'
   for path in checkpoint_dir.iterdir():
    self.assertTrue(path.resolve().is_relative_to(Path(c.temp.name).resolve()))
    if path.is_file():path.unlink()
  c.coordinator=ContextCoordinator(c.temp.name,config,factory)
  c.addCleanup(c.coordinator.close);c.coordinator.ready(5)
  c.text=CowTextAdapter(CowAdapter(c.coordinator),c.text.tokenizer,
   c.text.render,c.text.encode_rendered,append_user_suffix=c.text.append_user_suffix,
   append_initial_user_suffix=c.text.append_initial_user_suffix,
   initial_root_mode=c.text.initial_root_mode,renderer_id='b'*64)
  c.server=make_server(CowAdapter(c.coordinator),host=host,port=port,
   api_key='cpu-flow-secret',text_adapter=c.text)
  c.addCleanup(c.server.server_close)
  c.server_thread=threading.Thread(target=c.server.serve_forever,daemon=True)
  c.server_thread.start()
 def annotate_fixture_publications(self):
  # Modern native publications bind this metadata in Store.move. FlowModel is
  # an older synthetic fixture; annotate only these new integration cases.
  model=self.case.models[0];move=model.store.move
  def annotated(name,revision,target,operation,**options):
   cp=model.cache[target]
   options['checkpoint_receipt']=dict(schema=1,snapshot=target,
    payload_sha256=cp.checksum,model_contract_id='flow-model',
    execution_profile_id='flow-profile')
   return move(name,revision,target,operation,**options)
  model.store.move=annotated
 def assert_restart_reconciliation(self, *, evict_checkpoints=False):
  self.annotate_fixture_publications()
  op=self.pending();before=self.hashes();trace=list(self.case.trace)
  head=self.client.head('cli-main')
  self.restart_fixture_server(evict_checkpoints=evict_checkpoints)
  stats=dict(self.case.models[0].stats)
  r=self.invoke(op)
  self.assertEqual(r.returncode,0,r.stderr)
  value=json.loads(r.stdout)
  self.assertEqual(value['operation_id'],op)
  self.assertEqual(value['status'],'reconciled')
  self.assertFalse(value['workflow_advanced'])
  self.assertEqual(self.hashes(),before)
  self.assertEqual(self.case.trace,trace)
  self.assertEqual(self.case.models[0].stats,stats)
  self.assertEqual(self.client.head('cli-main'),head)
  with RuntimeLog(self.state/'ledger') as log:
   k=FrameKernel(log)
   with patch.object(self.client.transport,'request',side_effect=AssertionError('recovered output is local')):
    self.assertEqual(step_model(k,self.adapter,'model-flow').status,'partial')
 def test_cli_reconciles_after_server_reconstruction_without_new_work(self):
  self.assert_restart_reconciliation()
 def test_cli_reconciles_after_checkpoint_eviction_and_server_reconstruction(self):
  self.assert_restart_reconciliation(evict_checkpoints=True)
 def test_failed_operation_remains_unresolved_after_server_reconstruction(self):
  op=self.pending(failed=True);before=self.hashes();trace=list(self.case.trace)
  self.restart_fixture_server()
  r=self.invoke(op)
  self.assertEqual(r.returncode,4,r.stderr)
  self.assertEqual(self.hashes(),before);self.assertEqual(self.case.trace,trace)

 def test_live_diagnostic_is_unavailable_after_coordinator_reconstruction(self):
  op=self.pending(failed=True);before=self.hashes();trace=list(self.case.trace)
  self.restart_fixture_server();journal=self.client.journal.read(op)
  r=self.diagnose(op)
  self.assertEqual(r.returncode,2,r.stderr);self.assertEqual(self.hashes(),before)
  self.assertEqual(self.case.trace,trace);self.assertEqual(self.client.journal.read(op),journal)

 def test_uncommitted_bootstrap_stays_pending_without_new_root_work(self):
  from branchwrite.cow_client import CowClient,OperationJournal,OperationIntent
  state=Path(self.case.temp.name)/'uncommitted-bootstrap';save_launch(state,self.launch)
  with RuntimeLog(state/'ledger'):pass
  seed=hashlib.sha256(_bytes(self.launch['config'])+self.launch['program'].encode('utf8')).hexdigest()[:40]
  op='bw-root-'+seed
  journal=OperationJournal(state/'cow-operations')
  body=_bytes(dict(branch=self.launch['config']['cow']['branch'],namespace_id='0'*32,messages=[dict(role='system',content='never sent')],operation_id=op,stream=True))
  journal.begin(OperationIntent(op,'POST','/cow/text/context',body,self.launch['config']['cow']['branch'],None,None,self.client.endpoint_pin),self.client.endpoint_url)
  before=journal.read(op);trace=list(self.case.trace)
  files={str(p.relative_to(state/'ledger')):p.read_bytes() for p in (state/'ledger').rglob('*') if p.is_file()}
  result=subprocess.run([sys.executable,'-B','-m','branchwrite','reconcile',str(state),'--operation-id',op],capture_output=True,text=True,env=dict(os.environ,BW_COW_API_KEY='cpu-flow-secret'),timeout=20)
  self.assertEqual(result.returncode,4,result.stderr)
  self.assertEqual(journal.read(op),before);self.assertEqual(self.case.trace,trace)
  self.assertEqual({str(p.relative_to(state/'ledger')):p.read_bytes() for p in (state/'ledger').rglob('*') if p.is_file()},files)
