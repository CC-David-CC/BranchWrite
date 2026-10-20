"""Client journal and actual COW HTTP fixture; run in server CPU test env."""
import tempfile,unittest
from pathlib import Path
import serve.test_cow_grammar_registration_http as fixture
from branchwrite.cow_client import CowClient,OperationJournal,OperationReuseError
class GrammarClientTests(unittest.TestCase):
 def setUp(self):
  f=fixture.GrammarRegistrationHttpTests('runTest');f.setUp();self.addCleanup(f.doCleanups)
  self.fixture=f;self.url=f.start()
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.journal=OperationJournal(Path(self.temp.name)/'journal')
  self.client=CowClient.http(self.url,journal=self.journal,api_key='owned-key',endpoint_pin='cpu-grammar-fixture')
 def config(self,text='"A"'):
  return dict(schema=1,states=dict(ANSWER=dict(format='gbnf',source='root ::= '+text)))
 def test_registration_journals_original_request_and_reopens_locally(self):
  receipt=self.client.register_grammars(self.config(),'register-one')
  record=self.journal.read('register-one')
  self.assertEqual(record['state'],'complete')
  self.assertEqual(record['path'],'/cow/grammars')
  self.assertEqual(receipt['operation_id'],'register-one')
  self.assertEqual(self.client.replay_original('register-one'),receipt)
 def test_registration_id_cannot_be_reused_for_different_definitions(self):
  self.client.register_grammars(self.config(),'register-one')
  with self.assertRaises(OperationReuseError):
   self.client.register_grammars(self.config('"B"'),'register-one')
 def test_fresh_client_can_reconcile_registration_after_lost_acknowledgment(self):
  from branchwrite.cow_client import OperationIndeterminate
  original=self.client.transport.request
  def lose(method,path,body=None,**options):
   response=original(method,path,body,**options)
   if path=='/cow/grammars':raise OperationIndeterminate('injected lost acknowledgment after actual server publication')
   return response
  self.client.transport.request=lose
  with self.assertRaises(OperationIndeterminate):
   self.client.register_grammars(self.config(),'register-lost')
  record=self.journal.read('register-lost');self.assertEqual(record['state'],'pending')
  fresh=CowClient.http(self.url,journal=OperationJournal(self.journal.directory),api_key='owned-key',endpoint_pin='cpu-grammar-fixture')
  receipt=fresh.replay_original('register-lost')
  self.assertEqual(receipt['operation_id'],'register-lost')
  self.assertEqual(fresh.journal.read('register-lost')['state'],'complete')

 def test_wrong_definition_receipt_remains_pending_until_original_replay(self):
  from dataclasses import replace
  from branchwrite.cow_client import ReceiptError
  original=self.client.transport.request
  def tamper(method,path,body=None,**options):
   response=original(method,path,body,**options)
   if path=='/cow/grammars':
    return replace(response,json_value={**response.json_value,'definition_sha256':'0'*64})
   return response
  self.client.transport.request=tamper
  with self.assertRaises(ReceiptError):self.client.register_grammars(self.config(),'register-wrong-receipt')
  self.assertEqual(self.journal.read('register-wrong-receipt')['state'],'pending')
  self.client.transport.request=original
  result=self.client.replay_original('register-wrong-receipt')
  self.assertEqual(result['operation_id'],'register-wrong-receipt')
  self.assertEqual(self.journal.read('register-wrong-receipt')['state'],'complete')
