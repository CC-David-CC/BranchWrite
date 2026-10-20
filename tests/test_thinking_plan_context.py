"""Planning provenance is canonical workflow metadata, never a native controller."""
from collections import defaultdict
from pathlib import Path
import hashlib,json,unittest
from tests import test_cow_client_flow as fixture
from branchwrite.records import RuntimeLog,decode
from branchwrite.kernel import FrameKernel
from branchwrite.execution import Executor,Grant
from branchwrite.tool_registry import ToolRegistry
from branchwrite.interpreter import Interpreter,Value
from branchwrite.model_dispatch import ModelAdapter,FrozenModelCall,ModelContractError

class ThinkingPlanContextTests(unittest.TestCase):
 def context(self,**changes):
  value=dict(schema=1,profile='control',mode='standard',rung=1,origin_model_frame='first-model',handled_failures=('bwtool-failed',))
  value.update(changes);return value
 def test_valid_context_is_detached_with_exact_rung_and_failure_count(self):
  from branchwrite.thinking_ladder import planning_context
  value=self.context();saved=planning_context(value);value['profile']='different'
  self.assertEqual(saved['profile'],'control');self.assertEqual(saved['rung'],1)
 def test_missing_or_extra_context_fields_are_rejected(self):
  from branchwrite.thinking_ladder import planning_context
  missing=self.context();del missing['origin_model_frame']
  for value in [missing,self.context(rng='not owned here'),self.context(schema=True),self.context(profile='../other')]:
   with self.subTest(value=value),self.assertRaises(ValueError):planning_context(value)
 def test_invalid_rung_duplicate_failures_or_foreign_mode_are_rejected(self):
  from branchwrite.thinking_ladder import planning_context
  for value in [self.context(rung=True),self.context(rung=0),self.context(rung=4),self.context(mode='invented'),
                self.context(handled_failures=('same','same')),self.context(handled_failures=['bwtool-failed'])]:
   with self.subTest(value=value),self.assertRaises(ValueError):planning_context(value)
 def test_lite_context_uses_its_own_rungs_without_changing_standard(self):
  from branchwrite.thinking_ladder import planning_context,ladder
  value=self.context(mode='lite',rung=0,handled_failures=())
  self.assertEqual(planning_context(value),value);self.assertEqual(ladder('lite')[0].tokens,256)
  self.assertEqual(ladder('standard')[0].tokens,4096)

class ModelThinkingPlanContextTests(unittest.TestCase):
 def setUp(self):
  self.case=fixture.CowClientFlowTests();self.addCleanup(self.case.doCleanups);self.case.setUp()
  self.client=self.case._client('http','thinking-context')
  ns=self.client.create_namespace('thinking context','thinking-context-ns')['namespace_id']
  self.head=self.client.load_context('work',ns,[dict(role='system',content='Task facts.')],'thinking-context-root').receipt.branch
  self.adapter=ModelAdapter(self.client,run_id='thinking-context',model_contract_id='flow-model',execution_profile_id='flow-profile',eos_tokens=(299,))
 def context(self):return ThinkingPlanContextTests().context()
 def test_context_changes_frozen_plan_and_rejects_wrong_named_grammar(self):
  value=self.context()
  plan=self.adapter.freeze(self.head,mode='ask',content='Actual task.',output_format='thinking',grammar_state='BW_TOOLS_THINK_8192',planning=value)
  self.assertEqual(self.adapter.plan(plan)['planning'],value);self.assertEqual(self.adapter.plan(plan)['config']['content'],'Actual task.')
  before=plan.data;value['profile']='changed';self.assertEqual(plan.data,before)
  with self.assertRaises(ModelContractError):
   self.adapter.freeze(self.head,mode='ask',content='Actual task.',output_format='thinking',grammar_state='BW_TOOLS',planning=self.context())
  with self.assertRaises(ModelContractError):
   self.adapter.freeze(self.head,mode='ask',content='Actual task.',planning=self.context())
 def test_existing_plan_without_context_roundtrips_without_added_field(self):
  plan=self.adapter.freeze(self.head,mode='ask',content='Actual task.')
  self.assertNotIn('planning',self.adapter.plan(plan))

class FinishPlanningProvenanceTests(unittest.TestCase):
 def run_case(self,manual=False):
  case=fixture.CowClientFlowTests();self.addCleanup(case.doCleanups);case.setUp();client=case._client('http','finish-provenance')
  ns=client.create_namespace('finish provenance','finish-provenance-ns')['namespace_id']
  head=client.load_context('work',ns,[dict(role='system',content='Task facts.')],'finish-provenance-root').receipt.branch
  text=json.dumps(dict(tool='finish',arguments=dict(answer='not actually verified')))
  case.models[0].plans=defaultdict(lambda:tuple(text.encode())+(299,))
  base=Path(case.temp.name);source=base/'source';source.mkdir();(source/'data.txt').write_text('present\n')
  executor=Executor.create(source,base/'world');registry=ToolRegistry(executor,Grant((),False,read_paths=('data.txt',)))
  adapter=ModelAdapter(client,run_id='finish-provenance',model_contract_id='flow-model',execution_profile_id='flow-profile',eos_tokens=(299,))
  program="""FLOW task
EXPAND first from=current task=task profile=control -> first
PLAN p from=FROM against=world -> plan
TRANSFORM source input=first contract=cow-source -> current
EXPAND later from=current task=task profile=control -> later
ACT a plan=plan -> outcome
VERIFY v input=outcome contract=file-readback-and-finish -> verified
END
""".replace('from=FROM','from=manual' if manual else 'from=first')
  bindings=dict(current=Value('COWSource',dict(head=dict(name=head.name,revision=head.revision,tip=head.tip,root=head.root),mode='ask')),task=Value('Text','Read the actual file before finish.'),manual=Value('ToolProposal',text))
  with RuntimeLog(base/'ledger') as log:
   runtime=Interpreter(FrameKernel(log),registry,adapter=adapter,profiles=dict(control=dict(request_tokens=1024)),
    verification=dict(schema=1,files=[dict(path='data.txt',sha256=hashlib.sha256(b'present\n').hexdigest())]))
   runtime.start(program,bindings);return runtime.run().value
 def test_failed_finish_binds_original_proposal_not_latest_unrelated_model(self):
  value=self.run_case();self.assertFalse(value['verified']);v=value['bindings']['verified'][1]
  self.assertEqual(v['task_verdict'],'verified_failure')
  self.assertEqual(v['planning_model_frame'],value['bindings']['first'][1]['model_frame'])
  self.assertNotEqual(v['planning_model_frame'],value['bindings']['later'][1]['model_frame'])
 def test_manual_finish_does_not_borrow_a_model_planning_origin(self):
  value=self.run_case(manual=True);self.assertFalse(value['verified'])
  self.assertIsNone(value['bindings']['verified'][1].get('planning_model_frame'))
if __name__=='__main__':unittest.main()
