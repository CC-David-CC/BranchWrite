"""Setup recovery never invents authority from a pending or unrelated intent."""
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from branchwrite.cow_client import CowClient,OperationJournal,OperationIntent,OperationIndeterminate
from branchwrite.run_cli import _coding_bootstrap
from branchwrite.interpreter import AdmissionError

class BootstrapRecoveryTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.client=CowClient.http('http://127.0.0.1:1',journal=OperationJournal(Path(self.temp.name)/'journal'),endpoint_pin='host')
  self.cow=dict(branch='worker',model_contract_id='model',execution_profile_id='profile')
 def intent(self,path='/cow/text/context'):
  body=json.dumps(dict(branch='worker',namespace_id='a'*32,messages=[dict(role='system',content='original')],operation_id='bw-root-seed',stream=True)).encode()
  return OperationIntent('bw-root-seed','POST',path,body,'worker',None,None,'host')
 def recover(self):
  return _coding_bootstrap(self.client,self.cow,{},'seed',None,task_bound=True,output_paths=(),command_requirements=())
 def test_pending_context_is_not_sent_or_rebuilt(self):
  self.client.journal.begin(self.intent(),self.client.endpoint_url)
  before={p.name:p.read_bytes() for p in self.client.journal.directory.glob('*') if p.is_file()}
  with patch.object(self.client.transport,'request',side_effect=AssertionError('no resend')):
   with self.assertRaisesRegex(OperationIndeterminate,'bw-root-seed'):self.recover()
  self.assertEqual({p.name:p.read_bytes() for p in self.client.journal.directory.glob('*') if p.is_file()},before)
 def test_unrelated_intent_cannot_become_a_bootstrap(self):
  self.client.journal.begin(self.intent('/cow/text/answer'),self.client.endpoint_url)
  with patch.object(self.client.transport,'request',side_effect=AssertionError('no transport')):
   with self.assertRaises(AdmissionError):self.recover()
