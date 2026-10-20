"""Full review compares all project files against immutable admission bytes."""
import tempfile,unittest,json,hashlib
from pathlib import Path
from branchwrite.coding_cli import build_launch,save_launch
from branchwrite.records import RuntimeLog,encode
from branchwrite.kernel import FrameKernel,CallSpec,ResultContract
from branchwrite.execution import Executor,Grant
from branchwrite.tool_registry import ToolRegistry
from branchwrite.project_baseline import capture,BINDING,reference_text
from branchwrite.coding_review import inspect_changes
class FullProjectReviewTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name);self.source=self.root/'source';self.source.mkdir()
  (self.source/'app.py').write_bytes(b'old')
  (self.source/'protected.txt').write_bytes(b'protected')
  self.state=self.root/'state'
  c=dict(endpoint_url='http://127.0.0.1:1',endpoint_pin='x',model_contract_id='m',execution_profile_id='p',eos_tokens=[256])
  self.launch=build_launch(self.source,'Fix app',c,branch='r',edit_paths=['app.py'],create_paths=['new.txt'],test_commands=['true'])
  save_launch(self.state,self.launch)
 def make(self,action):
  ex=Executor.create(self.source,self.state/'world');reg=ToolRegistry(ex,Grant((),False))
  with RuntimeLog(self.state/'ledger') as log:
   ref=capture(log,reg);k=FrameKernel(log);definition=log.put_artifact(b'program')
   digest=hashlib.sha256(json.dumps(self.launch['config'],sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()
   inputs=log.put_artifact(encode({'bindings':{'host-config-sha256':('Text',digest),BINDING:('Text',reference_text(ref))}}))
   k.create_root('program','attempt',definition,inputs,ResultContract('ProgramResult','record'))
   action(ex.workspace)
   # Represents a subsequent verification command, after the shell edit.
   plan=log.put_artifact(encode(('bw.tool-plan.v2','reg','world','run_shell',{'command':'true'},(),reg._inventory(),None)))
   k.spawn('program',expected_epoch=0,calls=(CallSpec('verify','attempt2','slot','ACT',definition,plan,ResultContract('ToolOutcome','record')),),next_pc=1)
   k.dispatch('verify','op',plan);out=log.put_artifact(b'')
   k.record_result('verify','op',dict(tool='run_shell',disposition='exited',exit_code=0,stdout=(out.sha256,out.size_bytes)))
   k.resume('program',1);k.finish('program',{'verified':True})
 def test_shell_written_edit_is_in_complete_review(self):
  self.make(lambda p:(p/'app.py').write_bytes(b'new'))
  r=inspect_changes(self.state);self.assertTrue(r['complete_project_patch'])
  self.assertEqual(r['coverage'],'complete-project')
  self.assertEqual([c['path'] for c in r['changes']],['app.py'])
  self.assertEqual(r['changes'][0]['before_sha256'],hashlib.sha256(b'old').hexdigest())
 def test_ungranted_shell_write_is_rejected(self):
  self.make(lambda p:(p/'protected.txt').write_bytes(b'wrong'))
  with self.assertRaisesRegex(ValueError,'grant'):inspect_changes(self.state)
 def test_file_deletion_has_no_implicit_permission(self):
  self.make(lambda p:(p/'app.py').unlink())
  with self.assertRaisesRegex(ValueError,'delet'):inspect_changes(self.state)
 def test_binary_creation_and_exact_newline_flags(self):
  def action(p):
   (p/'app.py').write_bytes(bytes.fromhex('6e65770a'))
   (p/'new.txt').write_bytes(bytes([255,0]))
  self.make(action);r=inspect_changes(self.state)
  changes={c['path']:c for c in r['changes']}
  self.assertFalse(changes['app.py']['before_final_newline']);self.assertTrue(changes['app.py']['after_final_newline'])
  self.assertTrue(changes['new.txt']['binary']);self.assertIsNone(changes['new.txt']['before_sha256'])
 def test_mode_change_requires_mode_grant(self):
  self.make(lambda p:(p/'app.py').chmod(0o755))
  with self.assertRaisesRegex(ValueError,'mode'):inspect_changes(self.state)
