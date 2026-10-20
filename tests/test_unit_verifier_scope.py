"""Unit completion must use only joined current-world test receipts."""
from pathlib import Path
import json,tempfile,unittest
from branchwrite.execution import Executor,Grant
from branchwrite.tool_registry import ToolRegistry
from branchwrite.tool_dispatch import tool_call,dispatch_tool
from branchwrite.records import RuntimeLog
from branchwrite.kernel import FrameKernel,ResultContract,CallSpec,TransitionError
from branchwrite.interpreter import Interpreter

class UnitVerifierScopeTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.base=Path(self.temp.name)
  source=self.base/'source';source.mkdir();(source/'tests').mkdir();(source/'tests/__init__.py').write_text('')
  (source/'tests/test_task.py').write_text('import unittest\nclass Check(unittest.TestCase):\n def test_actual(self):self.assertEqual(3+4,7)\n')
  self.executor=Executor.create(source,self.base/'world');self.grant=Grant((),True)
  self.registry=ToolRegistry(self.executor,self.grant);self.log=RuntimeLog(self.base/'ledger');self.addCleanup(self.close)
  self.kernel=FrameKernel(self.log);self.runtime=Interpreter(self.kernel,self.registry)
  self.runtime.start('FLOW scope\nEND\n')
 def close(self):
  if not self.log._closed:self.log.close()
 def run_tests(self,parent='program',registry=None):
  registry=self.registry if registry is None else registry
  plan=registry.freeze(json.dumps(dict(tool='run_tests',arguments=dict(suite='unit'))))
  call=tool_call(self.kernel,registry,child_id='actual-tests',attempt_id='tests-attempt',slot='result',plan=plan)
  frame=self.kernel.frame(parent)
  self.kernel.spawn(parent,expected_epoch=frame['epoch'],calls=(call,),next_pc=1)
  result=dispatch_tool(self.kernel,registry,'actual-tests')
  self.assertEqual(result['disposition'],'exited');self.assertEqual(result['exit_code'],0)
 def verdict(self):
  return self.runtime._verification(dict(tool='finish',disposition='completion_requested',requested_finish=True,exit_code=None,operation_id='finish-op'),frame=self.kernel.frame('program'))
 def join(self,parent='program'):
  frame=self.kernel.frame(parent);self.kernel.resume(parent,frame['epoch'])
 def test_unjoined_actual_test_receipt_cannot_verify_until_resume(self):
  self.run_tests()
  self.assertEqual(self.verdict()['status'],'fail')
  self.join();self.assertEqual(self.verdict()['status'],'pass')
 def test_kernel_prevents_another_root_in_same_log(self):
  with self.assertRaisesRegex(TransitionError,'one root per run'):
   self.kernel.create_root('other','other-attempt',self.log.put_artifact(b'fixture'),self.log.put_artifact(b'fixture'),ResultContract('Fixture','record'))
 def test_unjoined_sibling_cannot_supply_successful_tests(self):
  definition=self.log.put_artifact(b'fixture');inputs=self.log.put_artifact(b'fixture')
  calls=tuple(CallSpec(n,n+'-attempt',n,'FLOW',definition,inputs,ResultContract('Fixture','record')) for n in ('other','inspect'))
  self.kernel.spawn('program',expected_epoch=0,calls=calls,next_pc=1)
  self.run_tests('other');self.join('other');self.kernel.finish('other',{})
  result=self.runtime._verification(dict(tool='finish',disposition='completion_requested',requested_finish=True,exit_code=None,operation_id='finish-op'),frame=self.kernel.frame('inspect'))
  self.assertEqual(result['status'],'fail')
 def test_actual_test_receipt_from_another_registry_cannot_verify(self):
  other=ToolRegistry(self.executor,self.grant,test_timeout=31)
  self.assertNotEqual(other.identity,self.registry.identity)
  self.run_tests(registry=other);self.join()
  self.assertEqual(self.verdict()['status'],'fail')
 def test_joined_current_receipt_survives_real_log_reopen(self):
  self.run_tests();self.join();self.close();self.log=RuntimeLog(self.base/'ledger')
  self.kernel=FrameKernel(self.log);self.runtime=Interpreter(self.kernel,self.registry)
  self.assertEqual(self.verdict()['status'],'pass');self.assertEqual(self.verdict()['task_verdict'],'verified_pass')
 def test_changed_current_files_invalidate_joined_success(self):
  self.run_tests();self.join();(self.executor.workspace/'new.txt').write_text('after tests\n')
  self.assertEqual(self.verdict()['status'],'fail')
if __name__=='__main__':unittest.main()
