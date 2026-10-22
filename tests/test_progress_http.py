"""Actual HTTP CPU fixture; checks progress routing, not model quality."""
from collections import defaultdict
from pathlib import Path
import json,tempfile,unittest
from branchwrite.execution import Executor,Grant
from branchwrite.tool_registry import ToolRegistry
from branchwrite.records import RuntimeLog
from branchwrite.kernel import FrameKernel
from branchwrite.interpreter import Interpreter,Value
from branchwrite.model_dispatch import ModelAdapter
class ModelProgressTests(unittest.TestCase):
 def test_async_wait_polls_do_not_repeat_model_progress_notices(self):
  import sys
  from unittest.mock import patch
  from branchwrite.parallel_dispatch import DispatchPool
  class GatedPool(DispatchPool):
   polls=0
   def ready(self,identifier):
    self.polls+=1
    return False if self.polls<=5 else super().ready(identifier)
  events=[];original=Interpreter
  with GatedPool(1) as pool:
   def build(*args,**kwargs):
    observe=kwargs['progress']
    def progress(event):events.append(event);observe(event)
    return original(*args,**dict(kwargs,dispatcher=pool,progress=progress))
   with patch.object(sys.modules[__name__],'Interpreter',build):
    self.test_model_progress_comes_from_existing_http_work_and_excludes_text()
   self.assertGreaterEqual(pool.polls,6)
   self.assertEqual(events.count('model_started'),1)
   self.assertEqual(events.count('model_step_returned'),1)

 def test_model_progress_comes_from_existing_http_work_and_excludes_text(self):
  import test_cow_client_flow as fixture
  case=fixture.CowClientFlowTests();self.addCleanup(case.doCleanups);case.setUp()
  client=case._client('http','progress')
  ns=client.create_namespace('progress','progress-ns')['namespace_id']
  client.load_context('work',ns,[dict(role='system',content='choose a tool')],'progress-root')
  head=client.head('work')
  output=json.dumps(dict(tool='finish',arguments=dict(answer='PRIVATE-MODEL-TEXT')))
  case.models[0].plans=defaultdict(lambda:tuple(output.encode())+(299,))
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);source=root/'source';source.mkdir()
   executor=Executor.create(source,root/'world')
   registry=ToolRegistry(executor,Grant((),False))
   with RuntimeLog(root/'ledger') as log:
    events=[]
    def observe(event):events.append((event,len(case.trace)))
    adapter=ModelAdapter(client,run_id='progress',model_contract_id='flow-model',execution_profile_id='flow-profile',eos_tokens=(299,))
    runtime=Interpreter(FrameKernel(log),registry,adapter=adapter,profiles={'control':dict(request_tokens=1024)},progress=observe)
    runtime.start('FLOW work\nTEXT task\n|Report readiness.\nEND\nEXPAND e from=current task=task profile=control -> proposed\nPLAN p from=proposed against=world -> plan\nACT a plan=plan -> outcome\nEND\n',
     {'current':Value('COWSource',dict(head=dict(name=head.name,revision=head.revision,tip=head.tip,root=head.root),mode='ask'))})
    report=runtime.run(max_steps=64)
    self.assertEqual(report.status,'complete')
    self.assertEqual(events[0],('model_started',0))
    self.assertIn(('model_step_returned',1),events)
    self.assertIn(('tool_started',1),events)
    self.assertIn(('tool_returned',1),events)
    self.assertEqual(len(case.trace),1)
    self.assertTrue(all('PRIVATE' not in e for e,_ in events))
