"""Recover durable, resource-retired tool returns through the canonical ledger."""
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from branchwrite.execution import Executor,Grant
from branchwrite.records import RuntimeLog,Artifact,decode,encode,CorruptLog
from branchwrite.kernel import FrameKernel,ResultContract,TransitionError
from branchwrite.tool_registry import ToolRegistry,EffectIndeterminate,FrozenToolPlan
from branchwrite.tool_dispatch import admit_tool,tool_call,dispatch_tool,ReconciliationRequired

class ToolSettlementRecoveryTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  source=self.root/'source';source.mkdir();(source/'data.txt').write_text('observed bytes')
  self.executor=Executor.create(source,self.root/'world')
  self.registry=ToolRegistry(self.executor,Grant((),False,read_paths=('data.txt',),create_paths=('new.txt',)))
  self.log=RuntimeLog(self.root/'run');self.addCleanup(self.close);self.kernel=FrameKernel(self.log)
  self.kernel.create_root('root','attempt',self.log.put_artifact(b'FLOW tools\nEND\n'),self.log.put_artifact(b'task'),ResultContract('AgentResult','record'))
 def close(self):
  if not self.log._closed:self.log.close()
 def admit(self,tool='create_file',**args):
  if not args:args=dict(path='new.txt',content='written exactly once')
  admit_tool(self.kernel,self.registry,'root',expected_epoch=0,child_id='tool',attempt_id='tool-attempt',slot='outcome',next_pc=1,proposal=json.dumps(dict(tool=tool,arguments=args)))
 def interrupted(self):
  self.admit()
  with patch.object(self.kernel,'settle',side_effect=OSError('interrupted after durable return')):
   with self.assertRaises(EffectIndeterminate):dispatch_tool(self.kernel,self.registry,'tool')
  self.assertEqual(self.kernel.frame('tool')['state'],'Settling')
  self.assertEqual((self.executor.workspace/'new.txt').read_text(),'written exactly once')
 def reopen(self):
  self.log.close();self.log=RuntimeLog(self.root/'run');self.kernel=FrameKernel(self.log)
 def test_recorded_retired_result_resumes_without_reexecution(self):
  self.interrupted();self.reopen()
  before=self.log.event_count
  with patch.object(self.registry,'execute',side_effect=AssertionError('must not repeat effect')):
   value=dispatch_tool(self.kernel,self.registry,'tool')
  self.assertEqual(value['disposition'],'created');self.assertEqual(self.log.event_count,before+1)
  self.assertEqual(self.kernel.frame('tool')['state'],'Closed');self.assertEqual(self.kernel.slot_value('root',1,'outcome'),value)
  self.assertTrue(self.kernel.resume('root',1))
 def test_completed_replay_has_no_new_event(self):
  self.interrupted();self.reopen();value=dispatch_tool(self.kernel,self.registry,'tool');before=self.log.event_count
  self.assertEqual(dispatch_tool(self.kernel,self.registry,'tool'),value);self.assertEqual(self.log.event_count,before)
 def test_unproven_settling_result_stays_unresolved(self):
  self.admit();frame=self.kernel.frame('tool')
  self.kernel.dispatch('tool','unknown-op',Artifact(*frame['inputs']))
  self.kernel.record_result('tool','unknown-op',dict(schema=1,operation_id='unknown-op',plan_sha256=frame['inputs'][0],tool='create_file'),settled=False)
  before=self.log.event_count
  with self.assertRaises(ReconciliationRequired):dispatch_tool(self.kernel,self.registry,'tool')
  self.assertEqual(self.log.event_count,before);self.assertEqual(self.kernel.frame('tool')['state'],'Settling')
 def test_effect_without_durable_return_is_not_recovered_by_file_contents(self):
  self.admit()
  with patch.object(self.executor,'_result',side_effect=OSError('output capture failed')):
   with self.assertRaises(EffectIndeterminate):dispatch_tool(self.kernel,self.registry,'tool')
  self.reopen();before=self.log.event_count
  with self.assertRaises(ReconciliationRequired):dispatch_tool(self.kernel,self.registry,'tool')
  self.assertEqual(self.log.event_count,before)
 def test_known_preflight_rejection_also_has_explicit_settlement(self):
  self.admit('read_file',path='data.txt');(self.executor.workspace/'data.txt').write_text('changed before execution')
  value=dispatch_tool(self.kernel,self.registry,'tool');frame=self.kernel.frame('tool')
  self.assertEqual(value['disposition'],'rejected_before_execution')
  self.assertIsNotNone(frame['settlement_receipt']);self.assertTrue(frame['result_settled'])
 def test_changed_registry_cannot_settle_prior_effect(self):
  self.interrupted();self.reopen()
  other=ToolRegistry(self.executor,Grant((),False,read_paths=('data.txt',),create_paths=('new.txt','other.txt')))
  before=self.log.event_count
  with self.assertRaises(TransitionError):dispatch_tool(self.kernel,other,'tool')
  self.assertEqual(self.log.event_count,before)
 def test_unproven_return_with_ordinary_artifacts_stays_unknown(self):
  self.admit();frame=self.kernel.frame('tool');operation='unproven-operation'
  self.kernel.dispatch('tool',operation,Artifact(*frame['inputs']))
  outcome=self.registry.execute(FrozenToolPlan(self.log.read_artifact(Artifact(*frame['inputs']))),operation)
  value,refs=outcome.publish(self.log);self.kernel.record_result('tool',operation,value,provenance=refs,settled=False)
  before=self.log.event_count
  with self.assertRaises(ReconciliationRequired):dispatch_tool(self.kernel,self.registry,'tool')
  self.assertEqual(self.log.event_count,before)
 def test_repeated_settlement_write_failure_does_not_repeat_effect(self):
  self.interrupted();self.reopen();before=self.log.event_count
  with patch.object(self.kernel,'settle',side_effect=OSError('still cannot publish')),patch.object(self.registry,'execute',side_effect=AssertionError('no resend')):
   with self.assertRaises(EffectIndeterminate):dispatch_tool(self.kernel,self.registry,'tool')
  self.assertEqual(self.log.event_count,before);self.assertEqual(self.kernel.frame('tool')['state'],'Settling')
 def test_receipt_from_another_workflow_ledger_is_not_transferable(self):
  self.interrupted();original=self.kernel.frame('tool')
  payload=decode(self.log.read_artifact(Artifact(*original['result'])))
  with RuntimeLog(self.root/'another-run') as log:
   k=FrameKernel(log)
   k.create_root('root','attempt',log.put_artifact(b'FLOW tools\nEND\n'),log.put_artifact(b'different task'),ResultContract('AgentResult','record'))
   call=tool_call(k,self.registry,child_id='tool',attempt_id='tool-attempt',slot='outcome',plan=FrozenToolPlan(self.log.read_artifact(Artifact(*original['inputs']))))
   k.spawn('root',expected_epoch=0,calls=(call,),next_pc=1)
   k.dispatch('tool',original['dispatch'][0],Artifact(*k.frame('tool')['inputs']))
   refs=tuple(log.put_artifact(self.log.read_artifact(Artifact(*wire))) for wire in payload[3])
   k.record_result('tool',original['dispatch'][0],payload[2],provenance=refs,settled=False)
   before=log.event_count
   with self.assertRaises(TransitionError):dispatch_tool(k,self.registry,'tool')
   self.assertEqual(log.event_count,before);self.assertEqual(k.frame('tool')['state'],'Settling')
 def test_altered_retirement_proof_is_rejected(self):
  self.interrupted();frame=self.kernel.frame('tool');payload=decode(self.log.read_artifact(Artifact(*frame['result'])))
  proof=Artifact(*payload[3][-1]);p=self.log.artifacts/proof.sha256;p.chmod(0o600);p.write_bytes(b'x'*proof.size_bytes)
  before=self.log.event_count
  with self.assertRaises(CorruptLog):dispatch_tool(self.kernel,self.registry,'tool')
  self.assertEqual(self.log.event_count,before);self.assertEqual(self.kernel.frame('tool')['state'],'Settling')

if __name__=='__main__':unittest.main()
