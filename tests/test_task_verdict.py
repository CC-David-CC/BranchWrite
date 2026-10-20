"""Only the host's completed-task verification may drive escalation."""
from pathlib import Path
import hashlib,json,tempfile,unittest
from branchwrite.execution import Executor,Grant
from branchwrite.tool_registry import ToolRegistry
from branchwrite.records import RuntimeLog
from branchwrite.kernel import FrameKernel
from branchwrite.interpreter import Interpreter,Value
class TaskVerdictTests(unittest.TestCase):
 def outcome(self,tool='read_file',disposition='read',code=0,finish=False):
  return dict(tool=tool,disposition=disposition,exit_code=code,requested_finish=finish,operation_id='actual-tool-op')
 def verdict(self,outcome,status='fail'):
  from branchwrite.thinking_ladder import task_verdict
  return task_verdict(outcome,dict(status=status,policy='host-contract'))
 def test_not_finished_verification_is_progress_not_failed_task(self):
  self.assertEqual(self.verdict(self.outcome()),'tool_progress')
 def test_intentional_nonzero_probe_does_not_escalate_thinking(self):
  self.assertEqual(self.verdict(self.outcome('terminal','exited',7)),'tool_progress')
 def test_only_a_completed_rejected_finish_is_a_verified_failure(self):
  self.assertEqual(self.verdict(self.outcome('finish','completion_requested',None,True)),'verified_failure')
  self.assertEqual(self.verdict(self.outcome('unadmitted','rejected_before_admission',None)),'tool_progress')
 def test_host_pass_stops_after_actual_finish(self):
  self.assertEqual(self.verdict(self.outcome('finish','completion_requested',None,True),'pass'),'verified_pass')
  self.assertEqual(self.verdict(self.outcome(),'pass'),'tool_progress')
 def test_unknown_effects_and_infrastructure_faults_are_not_task_retries(self):
  self.assertEqual(self.verdict(self.outcome('terminal','effect_indeterminate',None)),'unresolved_effect')
  self.assertEqual(self.verdict(self.outcome('terminal','spawn_error',None)),'infrastructure_failure')
 def test_unrecognized_host_status_is_rejected(self):
  with self.assertRaises(ValueError):self.verdict(self.outcome('finish','completion_requested',None,True),'model_says_done')
 def run_workflow(self,expected):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);source=root/'source';source.mkdir();(source/'note.txt').write_bytes(b'actual\n')
   executor=Executor.create(source,root/'world');registry=ToolRegistry(executor,Grant((),False,read_paths=('note.txt',)))
   program="""FLOW task
PLAN read from=read_tool against=world -> p
ACT read_action plan=p -> observed
VERIFY progress contract=file-readback-and-finish input=observed -> progress_verdict
PLAN finish from=finish_tool against=world -> p
ACT finish_action plan=p -> final
VERIFY complete contract=file-readback-and-finish input=final -> verified
END
"""
   with RuntimeLog(root/'ledger') as log:
    runtime=Interpreter(FrameKernel(log),registry,verification=dict(schema=1,files=[dict(path='note.txt',sha256=hashlib.sha256(expected).hexdigest())]))
    runtime.start(program,dict(read_tool=Value('ToolProposal',json.dumps(dict(tool='read_file',arguments=dict(path='note.txt')))),finish_tool=Value('ToolProposal',json.dumps(dict(tool='finish',arguments=dict(answer='done'))))))
    result=runtime.run();return result.value
 def test_actual_failed_finish_is_bound_to_its_tool_operation_in_ledger(self):
  result=self.run_workflow(b'other\n');self.assertFalse(result['verified'])
  progress=result['bindings']['progress_verdict'][1];failed=result['bindings']['verified'][1]
  self.assertEqual(progress['task_verdict'],'tool_progress')
  self.assertEqual(failed['task_verdict'],'verified_failure')
  self.assertEqual(failed['outcome_operation_id'],result['bindings']['final'][1]['operation_id'])
 def test_actual_success_keeps_original_verification_acceptance(self):
  result=self.run_workflow(b'actual\n');self.assertTrue(result['verified'])
  self.assertEqual(result['bindings']['verified'][1]['task_verdict'],'verified_pass')
  self.assertEqual(result['bindings']['progress_verdict'][1]['task_verdict'],'tool_progress')
if __name__=='__main__':unittest.main()
