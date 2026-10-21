"""Test the real tool-feedback transform, not a separate diagnostic display."""
import json,tempfile,unittest
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch
from branchwrite.execution import Executor,Grant
from branchwrite.tool_registry import ToolRegistry,ToolOutcome,EffectIndeterminate
from branchwrite.records import RuntimeLog,encode
from branchwrite.kernel import FrameKernel
from branchwrite.interpreter import Interpreter,Value

class ModelProblemFeedbackTests(unittest.TestCase):
 def view(self,outcome):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);source=root/'source';source.mkdir();(source/'note.txt').write_text('fixture')
   registry=ToolRegistry(Executor.create(source,root/'world'),Grant((),False,read_paths=('note.txt',)))
   with RuntimeLog(root/'ledger') as log:
    # Script only the domain outcome here; real ledger/ACT/feedback transform.
    runtime=Interpreter(FrameKernel(log),registry)
    program='FLOW feedback\nPLAN p from=proposal against=world -> plan\nACT a plan=plan -> result\nTRANSFORM f contract=tool-feedback input=result -> view\nEND\n'
    runtime.start(program,{'proposal':Value('ToolProposal',json.dumps(dict(tool='read_file',arguments=dict(path='note.txt'))))})
    def execute(plan,operation_id):return replace(outcome,operation_id=operation_id,plan_sha256=plan.sha256)
    with patch.object(registry,'execute',side_effect=execute):result=runtime.run()
    self.assertEqual(result.status,'complete')
    return json.loads(result.value['bindings']['view'][1])
 def outcome(self,tool,status,code=1,stderr=b'actual diagnostic',**details):
  return ToolOutcome(status,code,0.01,b'',stderr,'original-operation','a'*64,tool,details=encode(details))
 def test_pdf_missing_export_reaches_model_with_repair_instruction(self):
  view=self.view(self.outcome('build_pdf','pdf_failed',build_disposition='missing_artifact'))
  self.assertEqual(view['problem']['stage'],'missing_artifact')
  self.assertIn('document.pdf',view['problem']['next_action'])
  self.assertEqual(view['stderr'],'actual diagnostic')
  self.assertTrue(view['operation_id'])
 def test_cad_missing_export_names_actual_step_contract(self):
  view=self.view(self.outcome('inspect_cad','cad_failed',disposition='missing_artifact'))
  self.assertIn('part.step',view['problem']['next_action'])
 def test_domain_timeout_and_scene_failure_have_distinct_observed_stage(self):
  pdf=self.view(self.outcome('build_pdf','pdf_failed',build_disposition='timeout'))
  self.assertEqual(pdf['problem']['stage'],'timeout')
  scene=self.view(self.outcome('inspect_scene','scene_failed'))
  self.assertEqual(scene['problem']['stage'],'scene_failed')
  self.assertIn('views',scene['problem']['next_action'])
 def test_rejection_guidance_does_not_grant_permission_or_claim_success(self):
  view=self.view(self.outcome('unadmitted','rejected_before_admission',None,stderr=b'path outside grant'))
  self.assertIn('grant',view['problem']['next_action'])
  self.assertEqual(view['exit_code'],None)
  self.assertEqual(view['disposition'],'rejected_before_admission')
 def test_nonzero_command_may_have_effects_and_unknown_details_are_not_forwarded(self):
  view=self.view(self.outcome('run_shell','exited',7,argv=['sh','-c','false'],secret='do-not-forward'))
  self.assertIn('effects',view['problem']['next_action'])
  self.assertNotIn('do-not-forward',json.dumps(view))
 def test_success_has_no_invented_problem(self):
  self.assertNotIn('problem',self.view(self.outcome('build_pdf','pdf_built',0,stderr=b'')))
 def test_uncertain_effect_exception_names_original_operation_and_forbids_resend(self):
  message=str(EffectIndeterminate('retained-operation','b'*64))
  self.assertIn('retained-operation',message)
  self.assertIn('reconcile',message)
  self.assertIn('instead of resending',message)

class ProblemTeachingTests(unittest.TestCase):
 def test_new_prefix_teaches_observation_based_repair_without_changing_grants(self):
  from branchwrite.coding_defaults import system_prefix
  schema={'oneOf':[{'properties':{'tool':{'enum':['read_file']}}}]}
  prefix=system_prefix(schema)
  self.assertIn('problem.stage',prefix)
  self.assertIn('unchanged',prefix)
  self.assertIn('does not undo',prefix)
