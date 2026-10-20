"""Planning forks on FrameKernel and actual HTTP/Store; no GPU inference claim."""
from pathlib import Path
import copy,json,unittest
from unittest.mock import patch
import test_cow_client_flow as fixture
from branchwrite.cow_client import OperationIndeterminate
from branchwrite.records import RuntimeLog,Artifact,decode
from branchwrite.kernel import FrameKernel,ResultContract
from branchwrite.model_dispatch import ModelAdapter
class PlanningForkTests(unittest.TestCase):
 def setUp(self):
  self.case=fixture.CowClientFlowTests();self.addCleanup(self.case.doCleanups);self.case.setUp()
  self.client=self.case._client('http','planning-fork')
  ns=self.client.create_namespace('Planning forks','planning-ns')['namespace_id']
  self.source=self.client.prepare('main',ns,'Task facts.','planning-root').receipt.branch
  self.directory=Path(self.case.temp.name)/'workflow';self.log=RuntimeLog(self.directory);self.addCleanup(self.close);self.kernel=FrameKernel(self.log)
  self.kernel.create_root('root','root-attempt',self.log.put_artifact(b'FLOW caller END'),self.log.put_artifact(b'host task'),ResultContract('TaskResult','record'))
  self.adapter=ModelAdapter(self.client,run_id='planning-fork-run',model_contract_id='flow-model',execution_profile_id='flow-profile',eos_tokens=(299,))
 def close(self):
  if not self.log._closed:self.log.close()
 def reopen(self):
  self.close();self.log=RuntimeLog(self.directory);self.kernel=FrameKernel(self.log)
 def call(self,identifier='planning',name='next-plan',source=None,snapshot=None,slot='plan'):
  from branchwrite.cow_fork import fork_call
  return fork_call(self.kernel,self.adapter,child_id=identifier,attempt_id='try-'+identifier,slot=slot,
    source=self.source if source is None else source,snapshot=self.source.tip if snapshot is None else snapshot,name=name)
 def admit(self,**kwargs):self.kernel.spawn('root',expected_epoch=0,calls=(self.call(**kwargs),),next_pc=1)
 def run_fork(self,identifier='planning'):
  from branchwrite.cow_fork import dispatch_fork
  return dispatch_fork(self.kernel,self.adapter,identifier)
 def test_fork_keeps_failed_tip_and_selects_prior_snapshot_without_forward(self):
  old=self.source;failed=self.client.answer('main',old.revision,'answer-op',1).receipt.branch
  self.admit(source=failed,snapshot=old.tip);before=list(self.case.trace);v=self.run_fork()
  self.assertEqual(v['branch'],dict(name='next-plan',revision=0,tip=old.tip,root=old.root))
  self.assertEqual(self.client.head('main'),failed);self.assertEqual(self.case.trace,before)
  self.assertEqual(self.kernel.slot_value('root',1,'plan'),v)
 def test_restart_before_send_dispatches_one_original_fork(self):
  self.admit();self.reopen();actual=self.client.transport.request;posts=[]
  def observe(method,path,body=None,**kwargs):
   if method=='POST':posts.append((path,body))
   return actual(method,path,body,**kwargs)
  with patch.object(self.client.transport,'request',side_effect=observe):v=self.run_fork()
  self.assertEqual([x[0] for x in posts],['/cow/fork']);self.assertEqual(v['branch']['tip'],self.source.tip)
 def test_client_complete_before_kernel_return_recovers_offline(self):
  self.admit()
  with patch.object(self.kernel,'record_result',side_effect=OSError('before workflow acknowledgment')):
   with self.assertRaises(OSError):self.run_fork()
  self.reopen()
  with patch.object(self.client.transport,'request',side_effect=AssertionError('must use local original receipt')):v=self.run_fork()
  self.assertEqual(v['branch']['tip'],self.source.tip)
 def test_lost_server_ack_requires_reconciliation_and_never_resends(self):
  from branchwrite.cow_fork import ForkReconciliationRequired
  self.admit();actual=self.client.transport.request;posts=[]
  def drop(method,path,body=None,**kwargs):
   response=actual(method,path,body,**kwargs)
   if method=='POST' and path=='/cow/fork':
    posts.append(body);raise OperationIndeterminate('lost committed fork reply')
   return response
  with patch.object(self.client.transport,'request',side_effect=drop):
   with self.assertRaises(OperationIndeterminate):self.run_fork()
  op=self.kernel.frame('planning')['dispatch'][0];self.reopen()
  with patch.object(self.client.transport,'request',side_effect=AssertionError('no automatic resend')):
   with self.assertRaises(ForkReconciliationRequired):self.run_fork()
  self.assertTrue(self.client.recover(op).durable)
  with patch.object(self.client.transport,'request',side_effect=AssertionError('recovered receipt is local')):v=self.run_fork()
  self.assertEqual(v['branch']['tip'],self.source.tip);self.assertEqual(len(posts),1)
 def test_missing_client_intent_after_dispatch_is_not_assumed_unsent(self):
  from branchwrite.cow_fork import ForkReconciliationRequired,fork_operation_id
  self.admit();f=self.kernel.frame('planning');op=fork_operation_id(f)
  self.kernel.dispatch('planning',op,Artifact(*f['inputs']));self.reopen()
  with patch.object(self.client.transport,'request',side_effect=AssertionError('unknown dispatch cannot send')):
   with self.assertRaises(ForkReconciliationRequired):self.run_fork()
 def test_wrong_root_receipt_cannot_close_workflow(self):
  from branchwrite.cow_fork import ForkContractError
  from types import SimpleNamespace
  self.admit();actual=self.client.transport.request
  def corrupt(method,path,body=None,**kwargs):
   response=actual(method,path,body,**kwargs)
   if method=='POST' and path=='/cow/fork':
    value=copy.deepcopy(response.json_value);head=value.get('branch',value);head['root']='0'*64
    return SimpleNamespace(json_value=value)
   return response
  with patch.object(self.client.transport,'request',side_effect=corrupt):
   with self.assertRaises(ForkContractError):self.run_fork()
  self.assertEqual(self.kernel.frame('planning')['state'],'Waiting')
 def test_closed_fork_reopens_without_server_or_client_journal_read(self):
  self.admit();v=self.run_fork();self.reopen()
  with patch.object(self.client,'read_completed_fork',side_effect=AssertionError('canonical workflow return is enough')),patch.object(self.client.transport,'request',side_effect=AssertionError('closed result must be offline')):
   self.assertEqual(self.run_fork(),v)
 def test_two_out_of_order_forks_fill_only_their_own_slots(self):
  a=self.call('forkA','plan-A',slot='A');b=self.call('forkB','plan-B',slot='B')
  self.kernel.spawn('root',expected_epoch=0,calls=(a,b),next_pc=1)
  bv=self.run_fork('forkB');av=self.run_fork('forkA')
  self.assertEqual(self.kernel.slot_value('root',1,'A'),av);self.assertEqual(self.kernel.slot_value('root',1,'B'),bv)
  self.assertEqual((av['branch']['name'],bv['branch']['name']),('plan-A','plan-B'))
if __name__=='__main__':unittest.main()
