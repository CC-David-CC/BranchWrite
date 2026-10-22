"""Interpreter/COW boundary on real HTTP/Store CPU fixture; not GPU evidence."""
from collections import defaultdict
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import test_cow_client_flow as fixture
from branchwrite.records import RuntimeLog,Artifact,decode
from branchwrite.kernel import FrameKernel,ResultContract
from branchwrite.cow_client import OperationIndeterminate,CowClient,OperationJournal
from branchwrite.model_dispatch import (ModelAdapter,model_call,admit_model,step_model,
    ModelReconciliationRequired,ModelSourceChanged,ModelBranchBusy,ModelContractError)

class ModelFlowTests(unittest.TestCase):
 def setUp(self):
  self.case=fixture.CowClientFlowTests();self.addCleanup(self.case.doCleanups);self.case.setUp()
  self.client=self.case._client('http','model-flow')
  ns=self.client.create_namespace('Model flow','model-flow-ns')['namespace_id']
  self.root=self.client.prepare('model-main',ns,'A useful task.','model-flow-root')
  self.model=self.case.models[0];self.model.plans=defaultdict(lambda:(257,))
  self.directory=Path(self.case.temp.name)/'workflow';self.log=RuntimeLog(self.directory);self.addCleanup(self.close)
  self.kernel=FrameKernel(self.log);code=self.log.put_artifact(b'FLOW caller END');inputs=self.log.put_artifact(b'host task')
  self.kernel.create_root('root','root-attempt',code,inputs,ResultContract('TaskResult','record'))
  self.adapter=ModelAdapter(self.client,run_id='model-flow-run',model_contract_id='flow-model',execution_profile_id='flow-profile',eos_tokens=(299,))
 def close(self):
  if not self.log._closed:self.log.close()
 def reopen(self):
  self.close();self.log=RuntimeLog(self.directory);self.kernel=FrameKernel(self.log)
 def plan(self,branch='model-main',**kwargs):
  return self.adapter.freeze(self.client.head(branch),mode='answer',request_tokens=2,max_requests=4,max_output_tokens=8,**kwargs)
 def admit(self,plan=None):
  return admit_model(self.kernel,self.adapter,'root',expected_epoch=0,child_id='model-flow',attempt_id='model-attempt',slot='proposal',next_pc=1,plan=self.plan() if plan is None else plan)
 def native_frames(self):return [x for x in self.kernel.frames() if x['contract']==('COWNativeReceipt','record')]
 def test_partial_then_restart_continue_returns_once_at_consumed_eos(self):
  self.admit();first=step_model(self.kernel,self.adapter,'model-flow')
  self.assertEqual(first.status,'partial');self.assertIsNone(first.value)
  self.assertEqual(self.kernel.frame('root')['state'],'Waiting')
  with self.assertRaises(KeyError):self.kernel.slot_value('root',1,'proposal')
  self.reopen();self.model.plans=defaultdict(lambda:(258,299))
  final=step_model(self.kernel,self.adapter,'model-flow')
  self.assertEqual(final.status,'complete');self.assertEqual(final.value['text'],'hi!')
  self.assertEqual(final.value['consumed_output_tokens'],3);self.assertEqual(final.value['request_count'],2)
  self.assertEqual(self.kernel.slot_value('root',1,'proposal'),final.value)
  before=list(self.case.trace);self.reopen()
  with patch.object(self.client.transport,'request',side_effect=AssertionError('closed FLOW must not call COW')):
   again=step_model(self.kernel,self.adapter,'model-flow')
  self.assertEqual(again.value,final.value);self.assertEqual(self.case.trace,before)
  self.assertEqual([x['operation'] for x in self.native_frames()],['EXPAND','CONTINUE'])
  self.assertEqual(self.case.trace[-1][3],'active')
 def test_background_dispatch_returns_only_observations_until_owner_collects(self):
  from branchwrite.parallel_dispatch import DispatchPool
  self.admit()
  with DispatchPool(2) as pool:
   first=step_model(self.kernel,self.adapter,'model-flow',dispatcher=pool)
   self.assertEqual(first.status,'waiting')
   events=self.log.event_count
   while not pool.ready(first.native_operation):pool.wait(.05)
   self.assertEqual(self.log.event_count,events)
   self.assertEqual(self.native_frames()[0]['state'],'Waiting')
   collected=step_model(self.kernel,self.adapter,'model-flow',dispatcher=pool)
   self.assertEqual(collected.status,'partial')
   self.assertEqual(self.native_frames()[0]['state'],'Closed')
   self.assertFalse(pool.pending)
 def test_committed_client_reply_recovers_before_kernel_return_without_network(self):
  self.admit()
  with patch.object(self.kernel,'record_result',side_effect=OSError('injected before workflow return')):
   with self.assertRaises(OSError):step_model(self.kernel,self.adapter,'model-flow')
  self.assertEqual(self.native_frames()[0]['state'],'Waiting');before=list(self.case.trace)
  self.reopen()
  with patch.object(self.client.transport,'request',side_effect=AssertionError('use saved original reply')):
   recovered=step_model(self.kernel,self.adapter,'model-flow')
  self.assertEqual(recovered.status,'partial');self.assertEqual(self.case.trace,before)
  self.assertEqual(len(self.native_frames()),1)
 def test_saved_native_return_recovers_before_parent_resume_without_new_call(self):
  self.admit()
  with patch.object(self.kernel,'resume',side_effect=OSError('injected before parent resume')):
   with self.assertRaises(OSError):step_model(self.kernel,self.adapter,'model-flow')
  self.assertEqual(self.native_frames()[0]['state'],'Closed');before=list(self.case.trace);self.reopen()
  with patch.object(self.client.transport,'request',side_effect=AssertionError('no call at recovery boundary')):
   result=step_model(self.kernel,self.adapter,'model-flow')
  self.assertEqual(result.status,'partial');self.assertEqual(self.case.trace,before)
 def drop_once(self):
  actual=self.client.transport.request;posts=[]
  def request(method,path,body=None,**kwargs):
   result=actual(method,path,body,**kwargs)
   if method=='POST' and '/text/' in path:
    posts.append((path,body));raise OperationIndeterminate('injected dropped committed response')
   return result
  return actual,posts,request
 def test_missing_reply_never_resends_and_explicit_original_replay_recovers(self):
  self.admit();actual,posts,drop=self.drop_once()
  with patch.object(self.client.transport,'request',side_effect=drop):
   with self.assertRaises(OperationIndeterminate):step_model(self.kernel,self.adapter,'model-flow')
  self.assertEqual(len(posts),1);before=list(self.case.trace);op=self.native_frames()[0]['dispatch'][0];self.reopen()
  with patch.object(self.client.transport,'request',side_effect=AssertionError('must not resend automatically')):
   with self.assertRaises(ModelReconciliationRequired) as caught:step_model(self.kernel,self.adapter,'model-flow')
  self.assertEqual(caught.exception.operation_id,op);self.assertEqual(self.case.trace,before)
  self.client.replay_original(op)
  self.assertEqual(self.case.trace,before)
  with patch.object(self.client.transport,'request',side_effect=AssertionError('reconciled output is local')):
   self.assertEqual(step_model(self.kernel,self.adapter,'model-flow').status,'partial')
 def test_stale_source_never_dispatches_inference(self):
  plan=self.plan();self.admit(plan)
  self.client.answer('model-main',self.root.receipt.branch.revision,'answer-op',1);before=list(self.case.trace)
  with self.assertRaises(ModelSourceChanged):step_model(self.kernel,self.adapter,'model-flow')
  self.assertEqual(self.case.trace,before);self.assertEqual(len(self.native_frames()),0)
 def test_other_unresolved_operation_owns_the_branch(self):
  plan=self.plan();a=model_call(self.kernel,self.adapter,child_id='model-A',attempt_id='try-A',slot='A',plan=plan);c=model_call(self.kernel,self.adapter,child_id='model-B',attempt_id='try-B',slot='B',plan=plan)
  self.kernel.spawn('root',expected_epoch=0,calls=(a,c),next_pc=1)
  actual,posts,drop=self.drop_once()
  with patch.object(self.client.transport,'request',side_effect=drop):
   with self.assertRaises(OperationIndeterminate):step_model(self.kernel,self.adapter,'model-A')
  before=list(self.case.trace)
  with self.assertRaises(ModelBranchBusy):step_model(self.kernel,self.adapter,'model-B')
  self.assertEqual(self.case.trace,before);self.assertEqual(len(self.native_frames()),1)
 def test_partial_model_flow_keeps_branch_owner_between_native_requests(self):
  from branchwrite.kernel import CallSpec
  a=model_call(self.kernel,self.adapter,child_id='model-A',attempt_id='try-A',slot='A',plan=self.plan())
  code=self.log.put_artifact(b'FLOW independent host scope END');inputs=self.log.put_artifact(b'host scope inputs')
  host=CallSpec('host-B','host-B-attempt','B','FLOW',code,inputs,ResultContract('HostResult','record'))
  self.kernel.spawn('root',expected_epoch=0,calls=(a,host),next_pc=1)
  self.assertEqual(step_model(self.kernel,self.adapter,'model-A').status,'partial')
  current=self.plan()
  admit_model(self.kernel,self.adapter,'host-B',expected_epoch=0,child_id='model-B',attempt_id='try-B',slot='proposal',next_pc=1,plan=current)
  with patch.object(self.client.transport,'request',side_effect=AssertionError('active logical turn belongs to model-A')):
   with self.assertRaises(ModelBranchBusy):step_model(self.kernel,self.adapter,'model-B')
 def test_independent_branches_return_in_reverse_order_without_sibling_visibility(self):
  self.client.fork('model-main',self.root.receipt.snapshot,'model-other','model-other-fork')
  a=model_call(self.kernel,self.adapter,child_id='model-A',attempt_id='try-A',slot='A',plan=self.plan())
  c=model_call(self.kernel,self.adapter,child_id='model-B',attempt_id='try-B',slot='B',plan=self.plan('model-other'))
  self.kernel.spawn('root',expected_epoch=0,calls=(a,c),next_pc=1);self.model.plans=defaultdict(lambda:(257,299))
  b=step_model(self.kernel,self.adapter,'model-B');self.assertEqual(b.status,'complete')
  self.assertEqual(self.kernel.frame('root')['state'],'Waiting')
  with self.assertRaises(KeyError):self.kernel.slot_value('root',1,'A')
  a=step_model(self.kernel,self.adapter,'model-A');self.assertEqual(a.status,'complete')
  self.assertEqual(self.kernel.slot_value('root',1,'B')['native_receipt']['branch']['name'],'model-other')
  self.assertTrue(self.kernel.resume('root',1))
 def test_budget_exhaustion_retains_partial_without_typed_parent_return(self):
  plan=self.adapter.freeze(self.client.head('model-main'),mode='answer',request_tokens=1,max_requests=1,max_output_tokens=1)
  self.admit(plan);self.assertEqual(step_model(self.kernel,self.adapter,'model-flow').status,'partial');before=list(self.case.trace)
  with patch.object(self.client.transport,'request',side_effect=AssertionError('budget exhausted')):
   report=step_model(self.kernel,self.adapter,'model-flow')
  self.assertEqual(report.status,'budget_exhausted');self.assertIsNone(report.value)
  self.assertEqual(self.kernel.frame('root')['state'],'Waiting');self.assertEqual(self.case.trace,before)
 def test_adapter_profile_change_cannot_reinterpret_existing_flow(self):
  self.admit();wrong=ModelAdapter(self.client,run_id='model-flow-run',model_contract_id='other-model',execution_profile_id='flow-profile',eos_tokens=(299,))
  with patch.object(self.client.transport,'request',side_effect=AssertionError('contract changed')):
   with self.assertRaises(ModelContractError):step_model(self.kernel,wrong,'model-flow')
 def test_rejected_stopped_metadata_cannot_trigger_hidden_continuation(self):
  from dataclasses import replace
  self.admit();actual=self.client.transport.request
  def broken_view(method,path,body=None,**kwargs):
   response=actual(method,path,body,**kwargs)
   if method=='POST' and '/text/' in path:
    events=[]
    for e in response.events:
     item=dict(e)
     if item['event']=='complete':item['answer']=dict(item['answer'],thinking=dict(schema=1,complete=True,final_text='unsafe',snapshot=item['receipt']['snapshot']))
     events.append(item)
    return replace(response,events=tuple(events))
   return response
  with patch.object(self.client.transport,'request',side_effect=broken_view):
   with self.assertRaises(ModelContractError):step_model(self.kernel,self.adapter,'model-flow')
  before=list(self.case.trace);self.reopen()
  with patch.object(self.client.transport,'request',side_effect=AssertionError('invalid result must not start another request')):
   with self.assertRaises(ModelContractError):step_model(self.kernel,self.adapter,'model-flow')
  self.assertEqual(self.case.trace,before)
 def test_five_thousand_output_tokens_use_opaque_native_receipts_not_typed_lists(self):
  self.model.plans=defaultdict(lambda:(257,)*5000+(299,))
  plan=self.adapter.freeze(self.client.head('model-main'),mode='answer',request_tokens=5001,max_requests=1,max_output_tokens=5001)
  self.admit(plan);report=step_model(self.kernel,self.adapter,'model-flow')
  self.assertEqual(report.status,'complete');self.assertEqual(report.value['text'],'hi'*5000)
  self.assertEqual(report.value['consumed_output_tokens'],5001)
  raw=self.log.read_artifact(Artifact(*report.value['responses'][0]))
  self.assertEqual(len(json.loads(raw)['answer']['tokens']),5001)
 def test_partial_text_byte_budget_stops_before_another_request(self):
  self.admit(self.plan(max_result_bytes=1))
  with self.assertRaises(ModelContractError):step_model(self.kernel,self.adapter,'model-flow')
  before=list(self.case.trace);self.reopen()
  with patch.object(self.client.transport,'request',side_effect=AssertionError('output byte budget already exceeded')):
   with self.assertRaises(ModelContractError):step_model(self.kernel,self.adapter,'model-flow')
  self.assertEqual(self.case.trace,before)
 def test_controller_frame_inventory_is_detached(self):
  frames=self.kernel.frames();frames[0]['state']='Closed'
  self.assertEqual(self.kernel.frame('root')['state'],'Ready')
 def test_constrained_and_thinking_formats_require_explicit_named_grammar(self):
  for format in ['constrained','thinking']:
   with self.subTest(format=format),self.assertRaises(ModelContractError):self.plan(output_format=format)
if __name__=='__main__':unittest.main()
