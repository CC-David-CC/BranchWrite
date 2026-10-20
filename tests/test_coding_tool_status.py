"""Read-only tool recovery guidance never turns an uncertain effect into success."""
import contextlib,hashlib,io,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from branchwrite.execution import Executor,Grant
from branchwrite.tool_registry import ToolRegistry,EffectIndeterminate,FrozenToolPlan
from branchwrite.tool_dispatch import admit_tool,dispatch_tool
from branchwrite.records import RuntimeLog,Artifact
from branchwrite.kernel import FrameKernel,ResultContract
from branchwrite.coding_status import inspect_run,command

class CodingToolStatusTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.source=self.root/'source';self.source.mkdir();self.state=self.root/'state'
  self.e=Executor.create(self.source,self.root/'world');self.registry=ToolRegistry(self.e,Grant((),False,create_paths=('new.txt',)))
 def make(self,settling=False):
  with RuntimeLog(self.state/'ledger') as log:
   k=FrameKernel(log);k.create_root('program','attempt',log.put_artifact(b'canonical fixture'),log.put_artifact(b'original input'),ResultContract('ProgramResult','record'))
   admit_tool(k,self.registry,'program',expected_epoch=0,child_id='tool',attempt_id='tool-attempt',slot='outcome',next_pc=1,proposal=json.dumps(dict(tool='create_file',arguments=dict(path='new.txt',content='once'))))
   if settling:
    # Construct an actually unproven returned result in the canonical Kernel.
    # Overriding a returned flag no longer interrupts production dispatch,
    # which now performs an explicit later settlement. Assertions stay exact.
    frame=k.frame('tool');operation='fixture-unretired'
    k.dispatch('tool',operation,Artifact(*frame['inputs']))
    plan=FrozenToolPlan(log.read_artifact(Artifact(*frame['inputs'])))
    value,refs=self.registry.execute(plan,operation).publish(log)
    k.record_result('tool',operation,value,provenance=refs,settled=False)
   else:
    with patch.object(self.e,'_result',side_effect=OSError('receipt write failed')):
     with self.assertRaises(EffectIndeterminate):dispatch_tool(k,self.registry,'tool')
   return k.frame('tool')['dispatch'][0]
 def hashes(self):return {str(p.relative_to(self.root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in self.root.rglob('*') if p.is_file()}
 def test_unknown_effect_is_not_a_model_recovery_or_retry(self):
  op=self.make();before=self.hashes();r=inspect_run(self.state)
  self.assertEqual(r['pending_model_recovery'],[])
  self.assertEqual(r['pending_tool_recovery'],[dict(frame='tool',operation_id=op,state='Waiting',effect_status='outcome_unknown',automatic_replay=False)])
  self.assertEqual(self.hashes(),before);self.assertEqual((self.e.workspace/'new.txt').read_text(),'once')
 def test_recorded_result_awaiting_retirement_is_distinct(self):
  op=self.make(settling=True);r=inspect_run(self.state)
  self.assertEqual(r['pending_tool_recovery'],[dict(frame='tool',operation_id=op,state='Settling',effect_status='awaiting_settlement',automatic_replay=False)])
 def test_human_output_explains_unknown_effect_without_a_resend_command(self):
  self.make();before=self.hashes();out=io.StringIO()
  with contextlib.redirect_stdout(out):self.assertEqual(command(self.state),0)
  text=out.getvalue();self.assertIn('Tool effects',text);self.assertIn('do not repeat',text.lower());self.assertIn('matching file contents',text.lower());self.assertNotIn('branchwrite reconcile RUN_DIRECTORY',text)
  self.assertEqual(self.hashes(),before)
