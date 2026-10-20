"""Actual CPU HTTP/COW fork plus model flow; not autonomous/GPU evidence."""
from pathlib import Path
from collections import defaultdict
from unittest.mock import patch
import json,unittest
import test_cow_client_flow as fixture
from branchwrite.records import RuntimeLog,Artifact
from branchwrite.kernel import FrameKernel,ResultContract,TransitionError
from branchwrite.model_dispatch import ModelAdapter,FrozenModelCall,ModelReconciliationRequired
from branchwrite.cow_client import OperationIndeterminate
from branchwrite.cow_fork import ForkReconciliationRequired

class PlanningRetryFlowTests(unittest.TestCase):
 def setUp(self):
  self.case=fixture.CowClientFlowTests();self.addCleanup(self.case.doCleanups);self.case.setUp()
  self.client=self.case._client('http','retry-flow')
  ns=self.client.create_namespace('retry flow','retry-flow-ns')['namespace_id']
  self.prefix=self.client.load_context('main',ns,[dict(role='system',content='Retained task facts.')],'retry-flow-root').receipt.branch
  self.text=json.dumps(dict(tool='finish',arguments=dict(answer='reconsidered')))
  self.case.models[0].plans=defaultdict(lambda:tuple(self.text.encode())+(299,))
  self.failed=self.client.ask('main',self.prefix.revision,'failed-first','Original goal.',1024).receipt.branch
  self.directory=Path(self.case.temp.name)/'workflow';self.log=RuntimeLog(self.directory);self.addCleanup(self.close)
  self.kernel=FrameKernel(self.log)
  self.kernel.create_root('root','root-attempt',self.log.put_artifact(b'host retry fixture'),self.log.put_artifact(b'host task'),ResultContract('TaskResult','record'))
  self.adapter=ModelAdapter(self.client,run_id='retry-flow-run',model_contract_id='flow-model',execution_profile_id='flow-profile',eos_tokens=(299,))
 def close(self):
  if not self.log._closed:self.log.close()
 def reopen(self):
  self.close();self.log=RuntimeLog(self.directory);self.kernel=FrameKernel(self.log)
 def admit(self,**options):
  from branchwrite.planning_retry import retry_model_call
  args=dict(child_id='retry',attempt_id='retry-attempt',slot='answer',source=self.failed,snapshot=self.prefix.tip,
   mode='ask',content='Original goal. Review the failed assumption.',profile=dict(request_tokens=1024),provenance=())
  args.update(options);call=retry_model_call(self.kernel,self.adapter,**args)
  self.kernel.spawn('root',expected_epoch=0,calls=(call,),next_pc=1)
 def step(self):
  from branchwrite.planning_retry import step_retry_model
  return step_retry_model(self.kernel,self.adapter,'retry')
 def complete(self):
  for _ in range(20):
   report=self.step()
   if report.status=='complete':return report
  self.fail('retry FLOW did not complete')
 def forks(self):return [f for f in self.kernel.frames() if f['contract']==('COWForkReceipt','record')]
 def test_actual_fork_selects_prior_point_and_preserves_failed_tip(self):
  self.admit();before=len(self.case.trace);result=self.complete()
  self.assertEqual(result.value['text'],self.text);self.assertEqual(self.client.head('main'),self.failed)
  fork=result.value['planning_fork'];head=self.client.head(fork['branch']['name'])
  self.assertEqual(fork['branch']['tip'],self.prefix.tip);self.assertEqual(fork['branch']['revision'],0)
  self.assertEqual(head.root,self.prefix.root);self.assertNotEqual(head.tip,self.failed.tip)
  self.assertEqual(len(self.case.trace)-before,1);self.assertEqual(len(self.forks()),1)
  self.assertEqual(self.kernel.slot_value('root',1,'answer'),result.value)
  native_plan=self.adapter.plan(FrozenModelCall(self.log.read_artifact(Artifact(*self.kernel.frame(result.value['model_frame'])['inputs']))))
  self.assertEqual(native_plan['config']['mode'],'ask');self.assertIn('Original goal.',native_plan['config']['content'])
 def test_restart_after_fork_return_before_resume_does_not_refork(self):
  self.admit();self.step()
  with patch.object(self.kernel,'resume',side_effect=OSError('before resume')):
   with self.assertRaises(OSError):self.step()
  self.assertEqual(self.forks()[0]['state'],'Closed');self.reopen();before=len(self.case.trace)
  result=self.complete();self.assertEqual(result.status,'complete');self.assertEqual(len(self.forks()),1)
  self.assertEqual(len(self.case.trace)-before,1)
 def test_lost_fork_ack_requires_original_reconciliation(self):
  self.admit();self.step();actual=self.client.transport.request;posts=[]
  def drop(method,path,body=None,**kw):
   result=actual(method,path,body,**kw)
   if method=='POST' and path=='/cow/fork':posts.append(body);raise OperationIndeterminate('drop fork ack')
   return result
  with patch.object(self.client.transport,'request',side_effect=drop):
   with self.assertRaises(OperationIndeterminate):self.step()
  op=self.forks()[0]['dispatch'][0];self.reopen()
  with patch.object(self.client.transport,'request',side_effect=AssertionError('no resend')):
   with self.assertRaises(ForkReconciliationRequired):self.step()
  self.assertTrue(self.client.recover(op).durable)
  self.assertEqual(self.complete().status,'complete');self.assertEqual(len(posts),1)
 def test_complete_native_output_recovers_without_another_model_request(self):
  self.admit()
  actual=self.kernel.finish
  def fail_once(identifier,*a,**kw):
   if identifier=='retry':raise OSError('before wrapper publication')
   return actual(identifier,*a,**kw)
  with patch.object(self.kernel,'finish',side_effect=fail_once):
   with self.assertRaises(OSError):
    for _ in range(20):self.step()
  before=len(self.case.trace);self.reopen()
  with patch.object(self.client.transport,'request',side_effect=AssertionError('complete output is local')):
   result=self.complete()
  self.assertEqual(result.value['text'],self.text);self.assertEqual(len(self.case.trace),before)
 def test_incomplete_output_cannot_close_caller_slot(self):
  self.case.models[0].plans=defaultdict(lambda:(ord('x'),))
  self.admit(profile=dict(request_tokens=1,max_requests=1,max_output_tokens=1))
  for _ in range(10):
   report=self.step()
   if report.status=='budget_exhausted':break
  else:self.fail('missing budget report')
  self.assertNotEqual(self.kernel.frame('retry')['state'],'Closed')
  self.assertEqual(self.kernel.frame('root')['state'],'Waiting')
  self.assertIsNone(self.kernel.frame('retry')['result'])
  with self.assertRaises(KeyError):self.kernel.slot_value('root',1,'answer')
 def test_append_user_boundary_is_preserved(self):
  # An actual stopped prior turn, not the context-only prefix.
  self.admit(snapshot=self.failed.tip,mode='append_user',content='A new explicit observation.')
  result=self.complete()
  from branchwrite.model_dispatch import FrozenModelCall
  from branchwrite.records import Artifact
  model=self.kernel.frame(result.value['model_frame'])
  plan=self.adapter.plan(FrozenModelCall(self.log.read_artifact(Artifact(*model['inputs']))))
  self.assertEqual(plan['config']['mode'],'append_user')
  self.assertEqual(plan['config']['content'],'A new explicit observation.')
 def test_closed_retry_reopens_without_server_or_new_work(self):
  self.admit();first=self.complete();before=len(self.case.trace);self.reopen()
  with patch.object(self.client.transport,'request',side_effect=AssertionError('closed result is local')):
   second=self.complete()
  self.assertEqual(first.value,second.value);self.assertEqual(len(self.case.trace),before)
 def test_lost_model_ack_retains_original_native_operation(self):
  self.admit()
  while self.kernel.frame('retry')['pc']<1:self.step()
  self.step()
  actual=self.client.transport.request;posts=[]
  def drop(method,path,body=None,**kw):
   value=actual(method,path,body,**kw)
   if method=='POST' and '/text/' in path:posts.append(body);raise OperationIndeterminate('drop model ack')
   return value
  with patch.object(self.client.transport,'request',side_effect=drop):
   with self.assertRaises(OperationIndeterminate):self.step()
  native=[f for f in self.kernel.frames() if f['contract']==('COWNativeReceipt','record')][0]
  op=native['dispatch'][0];before=len(self.case.trace);self.reopen()
  with patch.object(self.client.transport,'request',side_effect=AssertionError('no uncertain resend')):
   with self.assertRaises(ModelReconciliationRequired):self.step()
  self.client.replay_original(op)
  self.assertEqual(len(self.case.trace),before)
  with patch.object(self.client.transport,'request',side_effect=AssertionError('reconciled completion is local')):
   self.assertEqual(self.complete().status,'complete')
  self.assertEqual(len(posts),1)
 def test_invalid_profile_is_rejected_before_fork_admission(self):
  from branchwrite.model_dispatch import ModelContractError
  with self.assertRaises(ModelContractError):self.admit(profile=dict(request_tokens=0))
  self.assertEqual(self.forks(),[]);self.assertEqual(len(self.kernel.frames()),1)
if __name__=='__main__':unittest.main()
