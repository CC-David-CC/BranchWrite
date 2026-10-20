"""Read-only completed-fork recovery against actual COW HTTP/Store CPU fixture."""
from pathlib import Path
import json,unittest
from unittest.mock import patch
import test_cow_client_flow as fixture
from branchwrite.cow_client import CowClient,OperationJournal,OperationIndeterminate,ReceiptError
class ForkReceiptTests(unittest.TestCase):
 def setUp(self):
  self.case=fixture.CowClientFlowTests();self.addCleanup(self.case.doCleanups);self.case.setUp()
  self.client=self.case._client('http','fork-receipts')
  ns=self.client.create_namespace('Fork receipts','fork-ns')['namespace_id']
  self.root=self.client.prepare('main',ns,'Task facts.','fork-root').receipt.branch
 def test_completed_fork_is_read_locally_without_transport_or_forward_work(self):
  before=list(self.case.trace);fork=self.client.fork('main',self.root.tip,'alternative','fork-op')
  self.assertEqual(self.case.trace,before)
  with patch.object(self.client.transport,'request',side_effect=AssertionError('local receipt read must not send')):
   self.assertEqual(self.client.read_completed_fork('fork-op'),fork)
  self.assertEqual(self.client.head('main'),self.root)
 def test_missing_pending_and_generation_records_cannot_be_fork_receipts(self):
  with self.assertRaises(OperationIndeterminate):self.client.read_completed_fork('missing')
  with self.assertRaises(ReceiptError):self.client.read_completed_fork('fork-root')
  actual=self.client.transport.request
  def drop(method,path,body=None,**kwargs):
   response=actual(method,path,body,**kwargs)
   if method=='POST' and path=='/cow/fork':raise OperationIndeterminate('lost acknowledgment')
   return response
  with patch.object(self.client.transport,'request',side_effect=drop):
   with self.assertRaises(OperationIndeterminate):self.client.fork('main',self.root.tip,'pending','pending-op')
  with patch.object(self.client.transport,'request',side_effect=AssertionError('pending read must not send')):
   with self.assertRaises(OperationIndeterminate):self.client.read_completed_fork('pending-op')
 def test_lost_fork_ack_recovers_by_read_only_status_then_local_receipt(self):
  actual=self.client.transport.request;posts=[]
  def drop(method,path,body=None,**kwargs):
   response=actual(method,path,body,**kwargs)
   if method=='POST' and path=='/cow/fork':
    posts.append(body);raise OperationIndeterminate('lost committed acknowledgment')
   return response
  with patch.object(self.client.transport,'request',side_effect=drop):
   with self.assertRaises(OperationIndeterminate):self.client.fork('main',self.root.tip,'after-restart','lost-fork')
  before=list(self.case.trace)
  client=CowClient.http(self.case.base_url,journal=OperationJournal(self.client.journal.directory),api_key='cpu-flow-secret',endpoint_pin='flow-model-free')
  self.assertTrue(client.recover('lost-fork').durable)
  with patch.object(client.transport,'request',side_effect=AssertionError('must consume saved receipt')):
   result=client.read_completed_fork('lost-fork')
  self.assertEqual(result.name,'after-restart');self.assertEqual(result.tip,self.root.tip)
  self.assertEqual(result.revision,0);self.assertEqual(self.case.trace,before);self.assertEqual(len(posts),1)
 def test_recovery_refuses_self_consistent_receipt_for_wrong_snapshot(self):
  from types import SimpleNamespace
  import copy
  actual=self.client.transport.request
  def drop(method,path,body=None,**kwargs):
   response=actual(method,path,body,**kwargs)
   if method=='POST' and path=='/cow/fork':raise OperationIndeterminate('lost reply')
   return response
  with patch.object(self.client.transport,'request',side_effect=drop):
   with self.assertRaises(OperationIndeterminate):self.client.fork('main',self.root.tip,'original-target','wrong-status')
  def corrupt(method,path,body=None,**kwargs):
   self.assertEqual(method,'GET')
   response=actual(method,path,body,**kwargs);value=copy.deepcopy(response.json_value)
   if path.startswith('/cow/operation?'):
    value['receipt']['snapshot']='0'*64;value['receipt']['branch']['tip']='0'*64
    return SimpleNamespace(json_value=value)
   return response
  with patch.object(self.client.transport,'request',side_effect=corrupt):
   with self.assertRaises(ReceiptError):self.client.recover('wrong-status')
  self.assertEqual(self.client.journal.read('wrong-status')['state'],'pending')
if __name__=='__main__':unittest.main()
