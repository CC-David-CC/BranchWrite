"""Real SIGKILL at owned tool-return boundaries; no GPU/model claims."""
import json,os,signal,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from branchwrite.execution import Executor,Grant
from branchwrite.records import RuntimeLog
from branchwrite.kernel import FrameKernel
from branchwrite.tool_registry import ToolRegistry
from branchwrite.tool_dispatch import dispatch_tool,ReconciliationRequired

CHILD = r"""
import os,signal,sys,json
from pathlib import Path
from unittest.mock import patch
from branchwrite.execution import Executor,Grant
from branchwrite.records import RuntimeLog
from branchwrite.kernel import FrameKernel,ResultContract
from branchwrite.tool_registry import ToolRegistry
from branchwrite.tool_dispatch import admit_tool,dispatch_tool
root=Path(sys.argv[1]);phase=sys.argv[2];source=root/'source';source.mkdir()
e=Executor.create(source,root/'world');registry=ToolRegistry(e,Grant((),False,create_paths=('new.txt',)))
with RuntimeLog(root/'ledger') as log:
 k=FrameKernel(log);k.create_root('root','root-attempt',log.put_artifact(b'owned crash fixture'),log.put_artifact(b'original task'),ResultContract('AgentResult','record'))
 admit_tool(k,registry,'root',expected_epoch=0,child_id='tool',attempt_id='tool-attempt',slot='outcome',next_pc=1,proposal=json.dumps(dict(tool='create_file',arguments=dict(path='new.txt',content='written once'))))
 def die(*a,**kw):os.kill(os.getpid(),signal.SIGKILL)
 if phase=='before-dispatch':
  with patch.object(k,'dispatch',side_effect=die):dispatch_tool(k,registry,'tool')
 elif phase=='before-return':
  with patch.object(k,'record_result',side_effect=die):dispatch_tool(k,registry,'tool')
 else:
  dispatch_tool(k,registry,'tool');die()
"""

class ToolProcessRecoveryTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
 def crash(self,phase):
  child=subprocess.run([sys.executable,'-B','-c',CHILD,str(self.root),phase],capture_output=True,timeout=30)
  self.assertEqual(child.returncode,-signal.SIGKILL,child.stderr.decode())
  if phase=='before-dispatch':self.assertFalse((self.root/'world/workspace/new.txt').exists())
  else:self.assertEqual((self.root/'world/workspace/new.txt').read_bytes(),b'written once')
  self.assertFalse((self.root/'source/new.txt').exists())
  e=Executor(self.root/'source',self.root/'world',self.root/'world/workspace')
  return ToolRegistry(e,Grant((),False,create_paths=('new.txt',)))
 def test_kill_after_effect_before_return_retains_unresolved_operation(self):
  registry=self.crash('before-return')
  with RuntimeLog(self.root/'ledger') as log:
   k=FrameKernel(log);before=k.frame('tool');self.assertEqual(before['state'],'Waiting');self.assertIsNone(before['result'])
   with patch.object(registry,'execute',side_effect=AssertionError('uncertain effect must not execute again')):
    with self.assertRaises(ReconciliationRequired) as error:dispatch_tool(k,registry,'tool')
   self.assertEqual(error.exception.operation_id,before['dispatch'][0]);self.assertEqual(k.frame('tool'),before)
   self.assertEqual(k.frame('root')['state'],'Waiting')
  self.assertEqual((self.root/'world/workspace/new.txt').read_bytes(),b'written once')
 def test_kill_after_durable_return_consumes_original_result_once(self):
  registry=self.crash('after-return')
  with RuntimeLog(self.root/'ledger') as log:
   k=FrameKernel(log);self.assertEqual(k.frame('tool')['state'],'Closed');self.assertEqual(k.frame('root')['state'],'Waiting')
   with patch.object(registry,'execute',side_effect=AssertionError('completed effect must not execute again')):
    value=dispatch_tool(k,registry,'tool');self.assertEqual(value['disposition'],'created')
    self.assertEqual(k.slot_value('root',1,'outcome'),value)
    self.assertTrue(k.resume('root',1));self.assertFalse(k.resume('root',1))
   self.assertEqual(k.frame('root')['pc'],1)
  with RuntimeLog(self.root/'ledger') as log:
   k=FrameKernel(log);self.assertEqual(k.frame('root')['state'],'Ready');self.assertEqual(k.frame('root')['pc'],1)
  self.assertEqual((self.root/'world/workspace/new.txt').read_bytes(),b'written once')

 def test_kill_before_dispatch_admits_one_fresh_execution(self):
  registry=self.crash('before-dispatch')
  with RuntimeLog(self.root/'ledger') as log:
   k=FrameKernel(log);self.assertEqual(k.frame('tool')['state'],'Ready');self.assertIsNone(k.frame('tool')['dispatch'])
   value=dispatch_tool(k,registry,'tool');self.assertEqual(value['disposition'],'created')
   self.assertTrue(k.resume('root',1));self.assertFalse(k.resume('root',1))
   with patch.object(registry,'execute',side_effect=AssertionError('no second effect')):
    self.assertEqual(dispatch_tool(k,registry,'tool'),value)
  self.assertEqual((self.root/'world/workspace/new.txt').read_bytes(),b'written once')
