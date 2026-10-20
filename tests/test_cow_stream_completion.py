"""NDJSON framing checks supplement real COW original-request replay tests."""
import tempfile,unittest
from pathlib import Path
from branchwrite.cow_client import CowClient,OperationJournal,COWSourceBinding,_Response,ReceiptError,OperationIndeterminate
class StreamCompletionTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.client=CowClient.http('http://127.0.0.1:1',journal=OperationJournal(self.tmp.name),endpoint_pin='framing-unit')
 def response(self,op,pieces=(),complete=True):
  body=self.client._generation_body('main',0,op,3,None,None)
  source=COWSourceBinding(op,'main','main',0,'b'*64,'framing-unit')
  intent=self.client._intent(op,'POST','/cow/text/answer',body,'main',0,None,source)
  record,_=self.client.journal.begin(intent,self.client.endpoint_url)
  receipt=dict(operation_id=op,snapshot='c'*64,branch=dict(name='main',revision=1,root='a'*64,tip='c'*64))
  answer=dict(snapshot='c'*64,text='done',tokens=[7,299])
  events=({'event':'complete','receipt':receipt,'answer':answer},) if complete else ()
  return _Response(events=events,provisional_text=pieces,transport='http'),record,intent
 def test_checked_complete_only_reply_has_exact_retained_answer(self):
  response,record,intent=self.response('complete-only')
  result=self.client._accept_stream(response,record,intent)
  self.assertEqual(result.answer['text'],'done');self.assertEqual(result.provisional_text,())
  self.assertEqual(self.client.read_completed_generation('complete-only').answer,result.answer)
 def test_observed_fragments_must_equal_complete_answer(self):
  for i,pieces in enumerate([('don',),('different',),('',),('done','extra')]):
   op='mismatch-'+str(i);response,record,intent=self.response(op,pieces)
   with self.subTest(pieces=pieces),self.assertRaises(ReceiptError):self.client._accept_stream(response,record,intent)
   self.assertEqual(self.client.journal.read(op)['state'],'pending')
  response,record,intent=self.response('matching',('do','ne'))
  self.assertEqual(self.client._accept_stream(response,record,intent).answer['text'],'done')
 def test_fragments_without_durable_completion_never_become_output(self):
  response,record,intent=self.response('no-complete',('done',),False)
  with self.assertRaises(OperationIndeterminate):self.client._accept_stream(response,record,intent)
  self.assertEqual(self.client.journal.read('no-complete')['state'],'pending')
if __name__=='__main__':unittest.main()
