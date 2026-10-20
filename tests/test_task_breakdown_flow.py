"""Existing interpreter + real HTTP/CPU fixture; not autonomous/GPU evidence."""
from collections import defaultdict
from pathlib import Path
import json,unittest
from unittest.mock import patch
import test_cow_client_flow as fixture
from branchwrite.records import RuntimeLog
from branchwrite.kernel import FrameKernel
from branchwrite.execution import Executor,Grant
from branchwrite.tool_registry import ToolRegistry
from branchwrite.model_dispatch import ModelAdapter
from branchwrite.interpreter import Interpreter,Value

PROGRAM="""FLOW decompose
EXPAND propose from=current task=goal profile=planner -> proposal
TRANSFORM validate input=proposal contract=task-breakdown -> breakdown
END
"""
class TaskBreakdownFlowTests(unittest.TestCase):
 def setUp(self):
  self.case=fixture.CowClientFlowTests();self.addCleanup(self.case.doCleanups);self.case.setUp();self.base=Path(self.case.temp.name)
  self.client=self.case._client('http','decompose');ns=self.client.create_namespace('decompose','ns-decompose')['namespace_id'];self.head=self.client.load_context('planner',ns,[dict(role='system',content='Propose bounded repair steps.')],'root-decompose').receipt.branch
  source=self.base/'project';source.mkdir();self.executor=Executor.create(source,self.base/'world');self.registry=ToolRegistry(self.executor,Grant((),False))
  self.adapter=ModelAdapter(self.client,run_id='decompose',model_contract_id='flow-model',execution_profile_id='flow-profile',eos_tokens=(299,));self.profiles=dict(planner=dict(output_format='text',request_tokens=1024,max_requests=2,max_output_tokens=2048))
  self.log=RuntimeLog(self.base/'ledger');self.addCleanup(self.close);self.k=FrameKernel(self.log)
 def close(self):
  if not self.log._closed:self.log.close()
 def execute_plan(self,text):
  self.case.models[0].plans=defaultdict(lambda:tuple(text.encode('utf8'))+(299,))
  runtime=Interpreter(self.k,self.registry,adapter=self.adapter,profiles=self.profiles)
  import dataclasses
  runtime.start(PROGRAM,dict(current=Value('COWSource',dict(head=dataclasses.asdict(self.head),mode='ask')),goal=Value('Text','Repair the project using smaller evidence-based steps.')))
  with patch.object(self.registry,'execute',side_effect=AssertionError('planning must not execute tools')):result=runtime.run(max_steps=128)
  self.assertEqual(result.status,'complete');self.assertFalse(result.value['verified']);self.assertEqual(list(self.executor.workspace.iterdir()),[])
  return result.value
 def test_model_breakdown_has_source_provenance_and_reopens_offline(self):
  text=json.dumps(dict(schema=1,steps=[dict(id='inspect',role='diagnose',goal='Find the actual failure.',depends_on=[]),dict(id='change',role='edit',goal='Repair the cause.',depends_on=['inspect'])]))
  result=self.execute_plan(text);value=result['bindings']['breakdown'][1]
  self.assertTrue(value['valid']);self.assertEqual(value['plan']['order'],('inspect','change'));self.assertEqual(value['source']['snapshot'],self.head.tip)
  models=[f for f in self.k.frames() if f['contract']==('ModelOutput','record')];self.assertEqual(len(models),1);self.assertEqual(value['source']['model_frame'],models[0]['id'])
  self.close();self.log=RuntimeLog(self.base/'ledger');self.k=FrameKernel(self.log);runtime=Interpreter(self.k,self.registry,adapter=self.adapter,profiles=self.profiles)
  with patch.object(self.client.transport,'request',side_effect=AssertionError('offline reopen must not contact model')):
   self.assertEqual(runtime.run().value,result)
 def test_model_cannot_turn_a_breakdown_into_grants_or_verified_success(self):
  text=json.dumps(dict(schema=1,steps=[dict(id='admin',role='edit',goal='Change permissions.',depends_on=[])],grant=dict(allow_shell=True)))
  result=self.execute_plan(text);value=result['bindings']['breakdown'][1];self.assertFalse(value['valid']);self.assertIsNone(value['plan']);self.assertTrue(value['reason']);self.assertFalse(self.registry._grant.allow_shell)
