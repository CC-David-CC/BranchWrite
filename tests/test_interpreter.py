"""Executable workflow REDs: real filesystem/executor and real COW HTTP, CPU model.

Scripted synthetic model decisions validate routing, not autonomous model quality.
"""
from collections import defaultdict
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from branchwrite.records import RuntimeLog,Artifact,decode
from branchwrite.kernel import FrameKernel
from branchwrite.execution import Executor,Grant
from branchwrite.tool_registry import ToolRegistry,EffectIndeterminate
from branchwrite.tool_dispatch import ReconciliationRequired
from branchwrite.interpreter import Interpreter,Value,AdmissionError

class InterpreterTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.directory=Path(self.temp.name)
  source=self.directory/'source';source.mkdir();(source/'data.txt').write_text('original\n')
  (source/'tests').mkdir();(source/'tests/__init__.py').write_text('')
  (source/'tests/test_task.py').write_text('import unittest\nfrom pathlib import Path\nclass Task(unittest.TestCase):\n def test_data(self):\n  self.assertEqual(Path("data.txt").read_text(),"correct\\n")\n')
  self.executor=Executor.create(source,self.directory/'world')
  self.registry=ToolRegistry(self.executor,Grant(('data.txt',),True,read_paths=('data.txt',),create_paths=('new.txt',)))
  self.log=RuntimeLog(self.directory/'log');self.addCleanup(self.close);self.kernel=FrameKernel(self.log)
  self.runtime=Interpreter(self.kernel,self.registry)
 def close(self):
  if not self.log._closed:self.log.close()
 def reopen(self,adapter=None):
  self.close();self.log=RuntimeLog(self.directory/'log');self.kernel=FrameKernel(self.log)
  self.runtime=Interpreter(self.kernel,self.registry,adapter=adapter,profiles={'control':dict(request_tokens=1024)} if adapter else None)
 def program(self,lines):return 'FLOW work\n'+lines+'END\n'
 def proposal(self,tool,**args):return Value('ToolProposal',json.dumps(dict(tool=tool,arguments=args)))
 def test_text_value_plan_act_uses_actual_files_and_preserves_original(self):
  source=self.program('VALUE proposed type=ToolProposal ref=request\nPLAN freeze from=proposed against=world -> frozen\nACT execute plan=frozen -> outcome\n')
  self.runtime.start(source,{'request':self.proposal('create_file',path='new.txt',content='made')})
  result=self.runtime.run(max_steps=64)
  self.assertEqual(result.status,'complete');self.assertFalse(result.value['verified'])
  self.assertEqual((self.executor.workspace/'new.txt').read_bytes(),b'made')
  self.assertFalse((self.executor.source/'new.txt').exists())
  tool=[f for f in self.kernel.frames() if f['contract']==('ToolOutcome','record')][0]
  self.assertIsNotNone(tool['dispatch'])
  self.assertEqual(self.log.read_artifact(Artifact(*tool['inputs'])),result.value['bindings']['frozen'][1]['data'])
 def test_whole_program_rejects_late_unsupported_operation_before_any_dispatch(self):
  source=self.program('PLAN p from=request against=world -> plan\nACT a plan=plan\nSAVE later input=plan name=not-yet-supported\n')
  with self.assertRaisesRegex(AdmissionError,'unsupported'):self.runtime.start(source,{'request':self.proposal('create_file',path='new.txt',content='bad')})
  self.assertEqual(self.log.event_count,0);self.assertFalse((self.executor.workspace/'new.txt').exists())
 def test_type_and_missing_binding_reject_before_root_admission(self):
  for value in [None,Value('Text','not a model proposal')]:
   with self.subTest(value=value),self.assertRaises(AdmissionError):
    self.runtime.start(self.program('PLAN p from=request against=world -> plan\n'),{} if value is None else {'request':value})
  self.assertEqual(self.log.event_count,0)
 def test_plan_act_does_not_re_freeze_and_stale_world_returns_rejection(self):
  self.runtime.start(self.program('PLAN p from=request against=world -> plan\nACT a plan=plan -> outcome\n'),{'request':self.proposal('create_file',path='new.txt',content='wanted')})
  while self.kernel.frame('program')['pc']<1:self.runtime.step()
  (self.executor.workspace/'new.txt').write_bytes(b'newer')
  with patch.object(self.registry,'freeze',side_effect=AssertionError('ACT must use existing plan')):
   result=self.runtime.run(max_steps=32)
  self.assertEqual(result.value['bindings']['outcome'][1]['disposition'],'rejected_before_execution')
  self.assertEqual((self.executor.workspace/'new.txt').read_bytes(),b'newer')
 def test_restart_after_tool_return_before_parent_resume_never_reexecutes(self):
  self.runtime.start(self.program('PLAN p from=request against=world -> plan\nACT a plan=plan -> outcome\n'),{'request':self.proposal('create_file',path='new.txt',content='once')})
  while not (self.kernel.frame('program')['pc']==1 and any(f['contract']==('ToolOutcome','record') and f['state']=='Closed' for f in self.kernel.frames())):self.runtime.step()
  self.reopen()
  with patch.object(self.registry,'execute',side_effect=AssertionError('closed call must not resend')):result=self.runtime.run(max_steps=32)
  self.assertEqual(result.status,'complete');self.assertEqual((self.executor.workspace/'new.txt').read_bytes(),b'once')
 def test_unknown_post_effect_does_not_retry_after_reopen(self):
  self.runtime.start(self.program('PLAN p from=request against=world -> plan\nACT a plan=plan\n'),{'request':self.proposal('create_file',path='new.txt',content='once')})
  while not any(f['contract']==('ToolOutcome','record') for f in self.kernel.frames()):self.runtime.step()
  with patch.object(self.executor,'_result',side_effect=OSError('lost tool receipt')):
   with self.assertRaises(EffectIndeterminate):self.runtime.step()
  self.reopen()
  with patch.object(self.registry,'execute',side_effect=AssertionError('must reconcile original operation')):
   with self.assertRaises(ReconciliationRequired):self.runtime.step()
 def test_registry_or_program_change_refused_on_reopen(self):
  self.runtime.start(self.program('TEXT task\n|Original task\nEND\n'))
  other=ToolRegistry(self.executor,Grant((),False,read_paths=('data.txt',)))
  with self.assertRaisesRegex(AdmissionError,'identity'):Interpreter(self.kernel,other).step()
  with self.assertRaises(AdmissionError):self.runtime.start(self.program('TEXT changed\n|changed\nEND\n'))
 def test_malformed_proposal_becomes_feedback_not_an_effect(self):
  source=self.program('PLAN p from=request against=world -> plan\nACT a plan=plan -> outcome\nTRANSFORM f input=outcome contract=tool-feedback -> feedback\n')
  self.runtime.start(source,{'request':Value('ToolProposal','not JSON')});result=self.runtime.run(max_steps=64)
  self.assertIn('rejected_before_admission',result.value['bindings']['feedback'][1]);self.assertFalse(result.value['verified'])
 def test_finish_request_without_host_tests_is_not_verified(self):
  source=self.program('PLAN p from=request against=world -> plan\nACT a plan=plan -> outcome\nVERIFY v input=outcome contract=unit-tests-and-finish -> verified\n')
  self.runtime.start(source,{'request':self.proposal('finish',answer='Trust me')});result=self.runtime.run(max_steps=64)
  self.assertFalse(result.value['verified']);self.assertEqual(result.value['bindings']['verified'][1]['status'],'fail')
 def test_repeat_exhaustion_and_step_budget_keep_distinct_statuses(self):
  source=self.program('REPEAT attempts max=2 until=verified exhausted=stop\nPLAN p from=request against=world -> plan\nACT a plan=plan -> outcome\nVERIFY v input=outcome contract=unit-tests-and-finish -> verified\nEND\n')
  self.runtime.start(source,{'request':self.proposal('finish',answer='not checked')})
  self.assertEqual(self.runtime.run(max_steps=1).status,'step_budget_exhausted')
  result=self.runtime.run(max_steps=128);self.assertEqual(result.status,'complete');self.assertFalse(result.value['verified'])
  self.assertEqual(result.value['bindings']['attempts'][1]['disposition'],'exhausted')
  self.assertEqual(sum(f['contract']==('ToolOutcome','record') for f in self.kernel.frames()),2)
 def test_changed_files_invalidate_prior_successful_tests(self):
  (self.executor.workspace/'data.txt').write_bytes(b'correct\n')
  source=self.program('PLAN p from=test-request against=world -> test-plan\nACT tests plan=test-plan -> tests-result\nPLAN f from=finish-request against=world -> finish-plan\nACT finish plan=finish-plan -> outcome\nVERIFY v input=outcome contract=unit-tests-and-finish -> verified\n')
  self.runtime.start(source,{'test-request':self.proposal('run_tests',suite='unit'),'finish-request':self.proposal('finish',answer='done')})
  while self.kernel.frame('program')['pc']<2:self.runtime.step()
  (self.executor.workspace/'data.txt').write_bytes(b'changed after tests\n')
  result=self.runtime.run(max_steps=64);self.assertFalse(result.value['verified'])
 def test_passed_actual_tests_and_finish_are_verified(self):
  (self.executor.workspace/'data.txt').write_bytes(b'correct\n')
  source=self.program('PLAN p from=test-request against=world -> test-plan\nACT tests plan=test-plan\nPLAN f from=finish-request against=world -> finish-plan\nACT finish plan=finish-plan -> outcome\nVERIFY v input=outcome contract=unit-tests-and-finish -> verified\n')
  self.runtime.start(source,{'test-request':self.proposal('run_tests',suite='unit'),'finish-request':self.proposal('finish',answer='done')})
  self.assertTrue(self.runtime.run(max_steps=64).value['verified'])

 def test_rejected_proposal_does_not_erase_a_previously_visible_read(self):
  from hashlib import sha256
  source=self.program('PLAN r from=read-request against=world -> plan\nACT read plan=plan -> outcome\nPLAN bad from=bad-request against=world -> plan\nACT reject plan=plan -> outcome\nPLAN good from=good-request against=world -> plan\nACT write plan=plan -> outcome\n')
  args=dict(path='data.txt',before='original',after='correct')
  self.runtime.start(source,{'read-request':self.proposal('read_file',path='data.txt'),'bad-request':self.proposal('replace',source_sha256=self.registry.world,**args),'good-request':self.proposal('replace',**args)})
  self.runtime.run(max_steps=128)
  self.assertEqual((self.executor.workspace/'data.txt').read_bytes(),b'correct\n')
 def test_feedback_names_world_and_file_hash_and_keeps_actual_source(self):
  source=self.program('PLAN r from=request against=world -> plan\nACT read plan=plan -> outcome\nTRANSFORM feedback input=outcome contract=tool-feedback -> text\n')
  self.runtime.start(source,{'request':self.proposal('read_file',path='data.txt')});result=self.runtime.run(max_steps=64)
  feedback=json.loads(result.value['bindings']['text'][1]);self.assertEqual(feedback['observation']['path'],'data.txt')
  self.assertEqual(feedback['observation']['world'],self.registry.world)
  from hashlib import sha256
  self.assertEqual(feedback['observation']['source_sha256'],sha256(b'original\n').hexdigest());self.assertEqual(feedback['stdout'],'original\n')
 def test_model_profiles_are_detached_after_freeze(self):
  runtime=Interpreter(self.kernel,self.registry,profiles={'control':{'settings':{'temperature':0.7}}})
  runtime.profiles['control']['settings']['temperature']=1.8
  self.assertEqual(runtime.profiles['control']['settings']['temperature'],0.7)
 def test_zero_tests_cannot_verify(self):
  (self.executor.workspace/'tests/test_task.py').unlink()
  source=self.program('PLAN t from=test-request against=world -> plan\nACT test plan=plan\nPLAN f from=finish-request against=world -> plan\nACT finish plan=plan -> outcome\nVERIFY v input=outcome contract=unit-tests-and-finish -> verified\n')
  self.runtime.start(source,{'test-request':self.proposal('run_tests',suite='unit'),'finish-request':self.proposal('finish',answer='done')})
  self.assertFalse(self.runtime.run(max_steps=64).value['verified'])

class ModelInterpreterTests(unittest.TestCase):
 setUp=InterpreterTests.setUp
 close=InterpreterTests.close
 reopen=InterpreterTests.reopen
 program=InterpreterTests.program
 proposal=InterpreterTests.proposal
 # Do not inherit base tests: separate integration fixtures below.
 __unittest_skip__=False
 def setUp(self):
  InterpreterTests.setUp(self)
 def test_model_chosen_read_edit_test_finish_with_feedback_and_restart(self):
  import test_cow_client_flow as fixture
  from branchwrite.model_dispatch import ModelAdapter
  case=fixture.CowClientFlowTests();self.addCleanup(case.doCleanups);case.setUp();client=case._client('http','interpreter')
  ns=client.create_namespace('interpreter','interpreter-ns')['namespace_id']
  root=client.load_context('work',ns,[{'role':'system','content':'Choose a tool to complete the task.'}],'interpreter-root')
  head=client.head('work');adapter=ModelAdapter(client,run_id='interpreter',model_contract_id='flow-model',execution_profile_id='flow-profile',eos_tokens=(299,))
  from hashlib import sha256
  decisions=[self.proposal('read_file',path='data.txt').data,self.proposal('replace',path='data.txt',before='original',after='correct').data,self.proposal('run_tests',suite='unit').data,self.proposal('finish',answer='done').data]
  it=iter(tuple(text.encode())+(299,) for text in decisions);case.models[0].plans=defaultdict(lambda:next(it))
  self.runtime=Interpreter(self.kernel,self.registry,adapter=adapter,profiles={'control':dict(request_tokens=1024)})
  source=self.program('TEXT task\n|Change data.txt to correct and run tests.\nEND\nREPEAT attempts max=6 until=verified exhausted=stop\nEXPAND choice from=current task=task profile=control -> proposed\nPLAN p from=proposed against=world -> plan\nACT a plan=plan -> outcome\nTRANSFORM source input=proposed contract=cow-source -> current\nTRANSFORM feedback input=outcome contract=tool-feedback -> task\nVERIFY check input=outcome contract=unit-tests-and-finish -> verified\nEND\n')
  self.runtime.start(source,{'current':Value('COWSource',dict(head=dict(name=head.name,revision=head.revision,tip=head.tip,root=head.root),mode='ask'))})
  for _ in range(400):
   report=self.runtime.step()
   if report.status=='complete' and report.frame=='program':break
   self.reopen(adapter)
  else:self.fail('workflow did not terminate')
  self.assertTrue(report.value['verified']);self.assertEqual((self.executor.workspace/'data.txt').read_bytes(),b'correct\n')
  self.assertEqual(len(case.trace),4)
  history=client.history('work');texts='\n'.join(m.get('text','') for m in history.messages)
  self.assertIn('Change data.txt',texts);self.assertIn('original',texts);self.assertIn('exited',texts)
  self.assertEqual(len([f for f in self.kernel.frames() if f['contract']==('ModelOutput','record')]),4)
