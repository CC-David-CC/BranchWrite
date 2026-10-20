"""Typed, causal feedback from recorded verification; no model/GPU claims."""
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from branchwrite.execution import Executor,Grant
from branchwrite.tool_registry import ToolRegistry
from branchwrite.records import RuntimeLog
from branchwrite.kernel import FrameKernel
from branchwrite.interpreter import Interpreter,Value,AdmissionError

class VerificationFeedbackTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  source=self.root/'source';source.mkdir();(source/'data.txt').write_text('visible text')
  self.executor=Executor.create(source,self.root/'world');self.registry=ToolRegistry(self.executor,Grant((),True,read_paths=('data.txt',)))
  self.log=RuntimeLog(self.root/'ledger');self.addCleanup(lambda:self.log.close() if not self.log._closed else None)
  self.kernel=FrameKernel(self.log);self.runtime=Interpreter(self.kernel,self.registry)
 def proposal(self,tool,**args):return Value('ToolProposal',json.dumps(dict(tool=tool,arguments=args)))
 def program(self,extra=''):
  return ('FLOW task\nPLAN p from=request against=world -> plan\nACT a plan=plan -> outcome\n'
    'VERIFY v input=outcome contract=unit-tests-and-finish -> verified\n'+extra+
    'TRANSFORM f input=outcome contract=tool-feedback evidence=verified -> feedback\nEND\n')
 def test_failed_finish_receives_real_verifier_reason_and_identity(self):
  self.runtime.start(self.program(),{'request':self.proposal('finish',answer='done')})
  result=self.runtime.run(max_steps=80);values=result.value['bindings']
  message=json.loads(values['feedback'][1]);verdict=message['verification']
  self.assertEqual(verdict['status'],'fail');self.assertEqual(verdict['policy'],'unit-tests-and-finish')
  self.assertEqual(verdict['reason'],values['verified'][1]['reason'])
  self.assertEqual(verdict['outcome_operation_id'],values['outcome'][1]['operation_id'])
  self.assertFalse(result.value['verified']);self.assertEqual(verdict['scope'],'recorded checked boundary')
 def test_other_tool_outcome_cannot_borrow_an_earlier_verdict(self):
  program=self.program('PLAN second from=other against=world -> later\nACT b plan=later -> outcome\n')
  self.runtime.start(program,{'request':self.proposal('read_file',path='data.txt'),'other':self.proposal('finish',answer='done')})
  with self.assertRaisesRegex(AdmissionError,'different|matching'):self.runtime.run(max_steps=100)
 def test_preflight_requires_an_already_bound_verification(self):
  for program in [self.program().replace('evidence=verified','evidence=request'),self.program().replace('VERIFY v input=outcome contract=unit-tests-and-finish -> verified\n','')]:
   with self.subTest(program=program),self.assertRaises(AdmissionError):self.runtime.start(program,{'request':self.proposal('finish',answer='done')})
  self.assertEqual(self.log.event_count,0)
 def test_feedback_allowlist_does_not_export_protected_details(self):
  self.runtime.start(self.program(),{'request':self.proposal('finish',answer='done')})
  with patch.object(self.runtime,'_verification_result',return_value=dict(status='fail',policy='unit-tests-and-finish',reason='public failure reason',protected_expected='DO_NOT_EXPORT_THIS')):
   result=self.runtime.run(max_steps=80)
  message=result.value['bindings']['feedback'][1]
  self.assertIn('public failure reason',message);self.assertNotIn('DO_NOT_EXPORT_THIS',message);self.assertNotIn('protected_expected',message)
 def test_restart_reuses_recorded_verdict_without_running_verifier_again(self):
  source=self.program();bindings={'request':self.proposal('finish',answer='done')};self.runtime.start(source,bindings)
  while not (self.kernel.frame('program')['pc']==3 and self.kernel.frame('program')['state']=='Ready'):self.runtime.step()
  self.log.close();self.log=RuntimeLog(self.root/'ledger');self.kernel=FrameKernel(self.log);self.runtime=Interpreter(self.kernel,self.registry)
  with patch.object(self.runtime,'_verification',side_effect=AssertionError('must reuse recorded verification')):
   self.runtime.start(source,bindings);result=self.runtime.run(max_steps=80)
  self.assertEqual(json.loads(result.value['bindings']['feedback'][1])['verification']['status'],'fail')
 def test_evidence_is_not_valid_for_unrelated_transform_contracts(self):
  source='FLOW task\nTRANSFORM bad input=request contract=cow-source evidence=missing -> result\nEND\n'
  with self.assertRaises(AdmissionError):self.runtime.start(source,{'request':Value('ToolProposal','unused')})
