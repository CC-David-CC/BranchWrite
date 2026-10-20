"""Completed transport outputs survive restart; CPU COW, never GPU claims."""
import json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import test_cow_client_flow as fixture
from branchwrite.cow_client import (CowClient, OperationJournal, ReceiptError,
    OperationIndeterminate, OperationReuseError, CowClientError, _Response)

class DurableAnswerTests(unittest.TestCase):
 def setUp(self):
  self.case=fixture.CowClientFlowTests();self.addCleanup(self.case.doCleanups);self.case.setUp()
  self.client=self.case._client('http','durable-answer')
  ns=self.client.create_namespace('Durable answer','durable-ns')['namespace_id']
  self.prepared=self.client.prepare('durable',ns,'Produce a short answer.','durable-root')
 def answer(self,op='answer-op',limit=1):
  return self.client.answer('durable',self.prepared.receipt.branch.revision,op,limit)
 def fresh(self):
  return CowClient.http(self.client.endpoint_url,journal=OperationJournal(self.client.journal.directory),api_key='cpu-flow-secret',endpoint_pin=self.client.endpoint_pin)
 def test_reopened_journal_preserves_exact_answer_without_head_read_or_network(self):
  original=self.answer();saved=json.loads(json.dumps(dict(original.answer)))
  original.answer['tokens'].append(999);original.answer['text']='not persisted'
  reopened=self.fresh()
  with patch.object(reopened.transport,'request',side_effect=AssertionError('no network on completed read')):
   restored=reopened.read_completed_generation('answer-op')
   replay=reopened.replay_original('answer-op')
   repeated=reopened.answer('durable',self.prepared.receipt.branch.revision,'answer-op',1)
  for result in [restored,replay,repeated]:
   self.assertEqual(result.answer,saved);self.assertEqual(result.receipt.raw,original.receipt.raw)
   self.assertEqual(result.source_binding.snapshot,self.prepared.receipt.snapshot)
   self.assertEqual(result.provisional_text,())
  restored.answer['tokens'].append(777)
  self.assertEqual(self.fresh().read_completed_generation('answer-op').answer,saved)
 def test_client_process_exit_after_saved_reply_recovers_in_another_process(self):
  import subprocess,sys,os
  import branchwrite.cow_client as client_module
  repository=Path(client_module.__file__).resolve().parents[1]
  journal=Path(self.case.temp.name)/'process-answer-journal'
  args=[str(journal),self.client.endpoint_url,str(self.prepared.receipt.branch.revision)]
  producer="""import os,sys
from branchwrite.cow_client import CowClient,OperationJournal
c=CowClient.http(sys.argv[2],journal=OperationJournal(sys.argv[1]),api_key='cpu-flow-secret',endpoint_pin='flow-model-free')
c.answer('durable',int(sys.argv[3]),'answer-op',1)
os._exit(73)
"""
  env={**os.environ,'PYTHONPATH':str(repository),'PYTHONDONTWRITEBYTECODE':'1'}
  made=subprocess.run([sys.executable,'-B','-c',producer,*args],env=env,capture_output=True,timeout=20)
  self.assertEqual(made.returncode,73,made.stderr.decode())
  record=OperationJournal(journal).read('answer-op');self.assertIn('answer',record)
  self.assertEqual(record['state'],'complete');before=list(self.case.trace)
  reader="""import json,sys
from branchwrite.cow_client import CowClient,OperationJournal
c=CowClient.http(sys.argv[2],journal=OperationJournal(sys.argv[1]),endpoint_pin='flow-model-free')
def no_network(*args,**kwargs):raise AssertionError('recovery must be local')
c.transport.request=no_network
r=c.read_completed_generation('answer-op')
print(json.dumps(dict(answer=r.answer,receipt=r.receipt.raw,source=r.source_binding.to_json())))
"""
  read=subprocess.run([sys.executable,'-B','-c',reader,*args],env=env,capture_output=True,timeout=20)
  self.assertEqual(read.returncode,0,read.stderr.decode());value=json.loads(read.stdout)
  self.assertEqual(value['answer'],record['answer']);self.assertEqual(value['receipt'],record['receipt'])
  self.assertEqual(value['source'],record['source_binding']);self.assertEqual(self.case.trace,before)

 def test_live_partial_stays_partial_after_recovery(self):
  original=self.answer();restored=self.fresh().read_completed_generation('answer-op')
  self.assertEqual(restored.answer['tokens'],[257]);self.assertNotEqual(restored.answer['tokens'][-1],299)
  from branchwrite.cow_actions import completed_thinking_text
  with self.assertRaises(ValueError):completed_thinking_text(restored,(299,))
  self.assertEqual(self.case.coordinator.store.get_snapshot(original.receipt.snapshot)['controller']['status'],'active')
 def test_actual_cli_completed_answer_is_retained_too(self):
  client=self.case._client('cli','durable-cli')
  original=client.answer('durable',self.prepared.receipt.branch.revision,'answer-op',1)
  with patch.object(client.transport,'request',side_effect=AssertionError('no CLI replay')):
   restored=client.read_completed_generation('answer-op')
  self.assertEqual(restored.answer,original.answer)
 def test_receipt_only_legacy_record_is_not_an_exact_answer(self):
  original=self.answer();journal=self.client.journal;record=journal.read('answer-op')
  record.pop('answer',None)
  from branchwrite.cow_client import _record_digest
  record['record_sha256']=_record_digest(record);journal._atomic(journal._path('answer-op'),record)
  with patch.object(self.client.transport,'request',side_effect=AssertionError('must not regenerate')):
   self.assertTrue(self.client.recover('answer-op').durable)
   with self.assertRaisesRegex(ReceiptError,'answer'):self.client.read_completed_generation('answer-op')
 def test_output_write_failure_leaves_pending_not_empty_completed_success(self):
  journal=self.client.journal;atomic=journal._atomic
  def fail_completed(path,record,**kwargs):
   if record['state']=='complete':raise CowClientError('injected output publication failure')
   return atomic(path,record,**kwargs)
  with patch.object(journal,'_atomic',side_effect=fail_completed):
   with self.assertRaises(CowClientError):self.answer()
  self.assertEqual(journal.read('answer-op')['state'],'pending')
  self.assertEqual(self.client.head('durable').revision,self.prepared.receipt.branch.revision+1)
  with patch.object(self.client.transport,'request',side_effect=AssertionError('must not resend')):
   with self.assertRaises(OperationIndeterminate):self.client.read_completed_generation('answer-op')
   with self.assertRaises(OperationIndeterminate):self.answer()
 def test_saved_answer_wrong_snapshot_is_rejected_even_with_valid_record_digest(self):
  self.answer();journal=self.client.journal;record=journal.read('answer-op');self.assertIn('answer',record)
  record['answer']['snapshot']='0'*64
  from branchwrite.cow_client import _record_digest
  record['record_sha256']=_record_digest(record);journal._atomic(journal._path('answer-op'),record)
  with self.assertRaises(ReceiptError):self.fresh().read_completed_generation('answer-op')
 def test_completed_output_cannot_be_overwritten_by_a_conflicting_completion(self):
  self.answer();journal=self.client.journal;record=journal.read('answer-op');self.assertIn('answer',record)
  changed=dict(record['answer'],text='other answer')
  with self.assertRaises((ReceiptError,OperationReuseError)):journal.complete(record,record['receipt'],answer=changed)
  self.assertNotEqual(self.fresh().read_completed_generation('answer-op').answer['text'],'other answer')
 def test_saved_source_owner_cannot_change_with_a_recomputed_record_digest(self):
  self.answer();journal=self.client.journal;record=journal.read('answer-op')
  record['source_binding']['operation_id']='different-owner'
  from branchwrite.cow_client import _record_digest
  record['record_sha256']=_record_digest(record);journal._atomic(journal._path('answer-op'),record)
  with self.assertRaises(ReceiptError):self.fresh().read_completed_generation('answer-op')
 def test_completed_read_rejects_other_endpoint_binding(self):
  self.answer();other=CowClient.http('http://127.0.0.1:1',journal=OperationJournal(self.client.journal.directory),endpoint_pin='different')
  with patch.object(other.transport,'request',side_effect=AssertionError('no network')):
   with self.assertRaises(OperationReuseError):other.read_completed_generation('answer-op')
if __name__=='__main__':unittest.main()
