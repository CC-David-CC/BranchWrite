"""Project scope and named checks must reach review/export without weaker scope."""
import tempfile,unittest,json,hashlib
from pathlib import Path
from branchwrite.coding_cli import build_launch,save_launch
from branchwrite.records import RuntimeLog,encode
from branchwrite.kernel import FrameKernel,CallSpec,ResultContract
from branchwrite.execution import Executor,Grant
from branchwrite.tool_registry import ToolRegistry
from branchwrite.project_baseline import capture,BINDING,reference_text
from branchwrite.coding_review import inspect_changes
from branchwrite.project_export import export_changes
class ProjectScopeReviewTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name);self.source=self.root/'source';self.source.mkdir()
  (self.source/'existing.txt').write_text('old')
  self.state=self.root/'state'
  c=dict(endpoint_url='http://127.0.0.1:1',endpoint_pin='x',model_contract_id='m',execution_profile_id='p',eos_tokens=[256])
  self.launch=build_launch(self.source,'Do the task',c,branch='project',project_files=True)
  save_launch(self.state,self.launch)
 def complete(self,action):
  ex=Executor.create(self.source,self.state/'world');reg=ToolRegistry(ex,Grant((),False))
  with RuntimeLog(self.state/'ledger') as log:
   ref=capture(log,reg);k=FrameKernel(log);definition=log.put_artifact(b'program')
   digest=hashlib.sha256(json.dumps(self.launch['config'],sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()
   inputs=log.put_artifact(encode({'bindings':{'host-config-sha256':('Text',digest),BINDING:('Text',reference_text(ref))}}))
   k.create_root('program','attempt',definition,inputs,ResultContract('ProgramResult','record'))
   action(ex.workspace)
   plan=log.put_artifact(encode(('bw.tool-plan.v2','reg','world','run_check',{'name':'content','command':'test -f existing.txt'},(),reg._inventory(),None)))
   k.spawn('program',expected_epoch=0,calls=(CallSpec('verify','attempt2','slot','ACT',definition,plan,ResultContract('ToolOutcome','record')),),next_pc=1)
   k.dispatch('verify','op',plan);out=log.put_artifact(b'')
   k.record_result('verify','op',dict(tool='run_check',disposition='exited',exit_code=0,stdout=(out.sha256,out.size_bytes)))
   k.resume('program',1);k.finish('program',{'verified':True})
  return ex.workspace
 def test_model_chosen_names_and_nested_directories_reach_review_export(self):
  def edit(p):
   (p/'existing.txt').write_text('changed');(p/'new-dir').mkdir();(p/'new-dir/other.txt').write_text('new')
  self.complete(edit);review=inspect_changes(self.state)
  self.assertEqual([r['path'] for r in review['changes']],['existing.txt','new-dir/other.txt'])
  self.assertTrue(review['complete_project_patch'])
  self.assertEqual(export_changes(self.state,self.root/'review.zip')['changed_files'],2)
 def test_after_check_change_cannot_be_reviewed(self):
  world=self.complete(lambda p:(p/'existing.txt').write_text('changed'))
  (world/'existing.txt').write_text('late')
  with self.assertRaisesRegex(ValueError,'inventory'):inspect_changes(self.state)
 def test_project_file_scope_does_not_silently_grant_deletion(self):
  self.complete(lambda p:(p/'existing.txt').unlink())
  with self.assertRaisesRegex(ValueError,'deletion'):inspect_changes(self.state)
if __name__=='__main__':unittest.main()
