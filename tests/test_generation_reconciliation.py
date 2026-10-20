"""Explicit durable-output recovery on real CPU HTTP; not GPU evidence."""
import json,unittest
from pathlib import Path
from collections import defaultdict
from unittest.mock import patch
import test_cow_client_flow as fixture
from branchwrite.cow_client import (CowClient,OperationJournal,OperationIndeterminate,
    OperationReuseError,ReceiptError,RequestRejected,_Response,_record_digest)

class GenerationReconciliationTests(unittest.TestCase):
 def setUp(self):
  self.case=fixture.CowClientFlowTests();self.addCleanup(self.case.doCleanups);self.case.setUp()
  self.client=self.case._client('http','generation-reconciliation')
  ns=self.client.create_namespace('Recovery','recovery-ns')['namespace_id']
  self.root=self.client.prepare('recovery-main',ns,'A short answer.','recovery-root')
  self.case.models[0].plans=defaultdict(lambda:(257,))
 def answer(self):
  return self.client.answer('recovery-main',self.root.receipt.branch.revision,'recovery-answer',1)
 def lost(self):
  actual=self.client.transport.request;sent=[];responses=[]
  def drop(method,path,body=None,**kw):
   response=actual(method,path,body,**kw)
   if method=='POST' and path=='/cow/text/answer':
    sent.append((method,path,body));responses.append(response);raise OperationIndeterminate('lost durable reply')
   return response
  with patch.object(self.client.transport,'request',side_effect=drop):
   with self.assertRaises(OperationIndeterminate):self.answer()
  return sent[0],responses[0]
 def test_durable_lost_reply_recovers_original_bytes_without_forward_work(self):
  intent,response=self.lost();before=list(self.case.trace);actual=self.client.transport.request;posts=[]
  def observe(method,path,body=None,**kw):
   if method=='POST':posts.append((method,path,body))
   return actual(method,path,body,**kw)
  with patch.object(self.client.transport,'request',side_effect=observe):
   recovered=self.client.reconcile_generation('recovery-answer')
  self.assertEqual(posts,[intent]);self.assertEqual(self.case.trace,before)
  expected=[e for e in response.events if e['event']=='complete'][0]
  self.assertEqual(recovered.answer,expected['answer']);self.assertEqual(recovered.receipt.raw,expected['receipt'])
  self.assertEqual(self.client.read_completed_generation('recovery-answer').answer,recovered.answer)
 def test_unknown_request_cannot_trigger_a_post(self):
  actual=self.client.transport.request
  def drop(method,path,body=None,**kw):
   if method=='POST' and path=='/cow/text/answer':raise OperationIndeterminate('never admitted')
   return actual(method,path,body,**kw)
  with patch.object(self.client.transport,'request',side_effect=drop):
   with self.assertRaises(OperationIndeterminate):self.answer()
  before=list(self.case.trace)
  def no_post(method,path,body=None,**kw):
   self.assertEqual(method,'GET');return actual(method,path,body,**kw)
  with patch.object(self.client.transport,'request',side_effect=no_post):
   with self.assertRaises((RequestRejected,OperationIndeterminate)):self.client.reconcile_generation('recovery-answer')
  self.assertEqual(self.case.trace,before)
 def test_receipt_only_record_can_restore_exact_answer_without_regeneration(self):
  original=self.answer();record=self.client.journal.read('recovery-answer');record.pop('answer');record['record_sha256']=_record_digest(record)
  self.client.journal._atomic(self.client.journal._path('recovery-answer'),record)
  before=list(self.case.trace);recovered=self.client.reconcile_generation('recovery-answer')
  self.assertEqual(recovered.answer,original.answer);self.assertEqual(self.case.trace,before)
 def test_complete_output_recovers_offline(self):
  original=self.answer()
  with patch.object(self.client.transport,'request',side_effect=AssertionError('completed answer must remain local')):
   result=self.client.reconcile_generation('recovery-answer')
  self.assertEqual(result.answer,original.answer)
 def test_wrong_endpoint_rejected_before_network(self):
  self.lost();other=CowClient.http(self.client.endpoint_url,journal=self.client.journal,endpoint_pin='wrong-owner')
  with patch.object(other.transport,'request',side_effect=AssertionError('wrong endpoint must not send')):
   with self.assertRaises(OperationReuseError):other.reconcile_generation('recovery-answer')
 def test_wrong_observed_receipt_cannot_trigger_replay(self):
  self.lost();actual=self.client.transport.request;before=self.client.journal.read('recovery-answer')
  def corrupt(method,path,body=None,**kw):
   self.assertEqual(method,'GET');response=actual(method,path,body,**kw)
   value=json.loads(json.dumps(response.json_value));value['receipt']['operation_id']='wrong-operation'
   return _Response(json_value=value,transport='corrupt-status')
  with patch.object(self.client.transport,'request',side_effect=corrupt):
   with self.assertRaises(ReceiptError):self.client.reconcile_generation('recovery-answer')
  self.assertEqual(self.client.journal.read('recovery-answer'),before)

 def test_known_failed_request_cannot_trigger_another_post(self):
  self.case.models[0].plans={}
  with self.assertRaises(RequestRejected):self.answer()
  actual=self.client.transport.request;before=list(self.case.trace)
  def no_post(method,path,body=None,**kw):
   self.assertEqual(method,'GET');return actual(method,path,body,**kw)
  with patch.object(self.client.transport,'request',side_effect=no_post):
   with self.assertRaises(OperationIndeterminate):self.client.reconcile_generation('recovery-answer')
  self.assertEqual(self.case.trace,before)
 def test_replay_receipt_must_equal_the_prior_durable_proof(self):
  self.lost();actual=self.client.transport.request;before=self.client.journal.read('recovery-answer')
  def alter(method,path,body=None,**kw):
   response=actual(method,path,body,**kw)
   if method=='POST':
    events=json.loads(json.dumps(response.events))
    for event in events:
     if event['event']=='complete':event['receipt']['model_contract_id']='different-model'
    return _Response(events=tuple(events),transport='corrupt-replay')
   return response
  with patch.object(self.client.transport,'request',side_effect=alter):
   with self.assertRaises(ReceiptError):self.client.reconcile_generation('recovery-answer')
  self.assertEqual(self.client.journal.read('recovery-answer'),before)

 def test_fault_proxy_selects_first_native_request_then_recovery_does_no_work(self):
  from validation.cow_fault_proxy import LostAckProxy
  proxy=LostAckProxy(self.client.endpoint_url,None);self.addCleanup(proxy.close)
  client=CowClient.http(proxy.url,journal=OperationJournal(Path(self.case.temp.name)/'proxy-journal'),api_key='cpu-flow-secret',endpoint_pin='proxy-owned')
  with self.assertRaises(OperationIndeterminate):
   client.answer('recovery-main',self.root.receipt.branch.revision,'bwnative-selected',1)
  self.assertTrue(proxy.dropped.is_set());self.assertEqual(proxy.operation_id,'bwnative-selected')
  before=list(self.case.trace);result=client.reconcile_generation('bwnative-selected')
  self.assertEqual(result.answer,proxy.dropped_completion['answer']);self.assertEqual(self.case.trace,before)
  posts=[r for r in proxy.requests if r['method']=='POST']
  self.assertEqual(len(posts),2);self.assertEqual(posts[0]['body_sha256'],posts[1]['body_sha256'])
