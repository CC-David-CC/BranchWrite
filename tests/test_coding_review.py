"""Recorded edit review is read-only and refuses stale workspace evidence."""
import hashlib,json,tempfile,unittest
from pathlib import Path
from branchwrite.records import RuntimeLog,encode
from branchwrite.kernel import FrameKernel,ResultContract,CallSpec
from branchwrite.coding_cli import build_launch,save_launch
from branchwrite.execution import Executor,Grant
from branchwrite.tool_registry import ToolRegistry
class CodingReviewTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name);self.project=self.root/'project';self.project.mkdir()
  (self.project/'app.py').write_bytes(b'old\n')
  self.state=self.root/'state'
  connection=dict(endpoint_url='http://127.0.0.1:1',endpoint_pin='test',model_contract_id='m',execution_profile_id='p',eos_tokens=[256])
  self.launch=build_launch(self.project,'Fix app',connection,branch='run',edit_paths=['app.py'],test_commands=['true'])
  save_launch(self.state,self.launch)
 def make(self):
  ex=Executor.create(self.project,self.state/'world')
  registry=ToolRegistry(ex,Grant((),False))
  with RuntimeLog(self.state/'ledger') as log:
   k=FrameKernel(log);definition=log.put_artifact(b'program')
   digest=hashlib.sha256(json.dumps(self.launch['config'],sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()
   inputs=log.put_artifact(encode({'bindings':{'host-config-sha256':('Text',digest)}}))
   k.create_root('program','attempt',definition,inputs,ResultContract('ProgramResult','record'))
   def result(idx,tool,args,preimages,disposition,stdout=b'',inventory=None):
    plan=log.put_artifact(encode(('bw.tool-plan.v2','registry','world',tool,args,preimages,inventory,None)))
    child='child'+str(idx)
    k.spawn('program',expected_epoch=idx-1,calls=(CallSpec(child,'attempt'+str(idx),'slot','ACT',definition,plan,ResultContract('ToolOutcome','record')),),next_pc=idx)
    k.dispatch(child,'op'+str(idx),plan)
    ref=log.put_artifact(stdout)
    k.record_result(child,'op'+str(idx),dict(tool=tool,disposition=disposition,exit_code=0,stdout=(ref.sha256,ref.size_bytes)))
    k.resume('program',idx)
   old=hashlib.sha256(b'old\n').hexdigest()
   result(1,'read_file',{'path':'app.py'},(('app.py',old,0o644),),'read',b'old\n')
   result(2,'replace',{'path':'app.py','before':'old','after':'new'},(('app.py',old,0o644),),'applied')
   (ex.workspace/'app.py').write_bytes(b'new\n')
   result(3,'run_shell',{'command':'true'},(),'exited',inventory=registry._inventory())
   k.finish('program',{'verified':True})
 def test_exact_saved_preimage_and_current_bytes_form_diff(self):
  self.make()
  from branchwrite.coding_review import inspect_changes
  x=inspect_changes(self.state)
  self.assertEqual(x['coverage'],'recorded-file-tools')
  self.assertEqual(len(x['changes']),1);c=x['changes'][0]
  self.assertEqual(c['path'],'app.py');self.assertIn('-old',c['diff']);self.assertIn('+new',c['diff'])
  self.assertEqual(c['before_sha256'],hashlib.sha256(b'old\n').hexdigest())
 def test_post_completion_workspace_change_is_rejected(self):
  self.make();(self.state/'world/workspace/app.py').write_text('changed later')
  from branchwrite.coding_review import inspect_changes
  with self.assertRaisesRegex(ValueError,'workspace'):inspect_changes(self.state)
 def test_changed_launch_grants_are_rejected(self):
  self.make()
  f=self.state/'coding-launch.json';x=json.loads(f.read_text())
  x['launch']['config']['grant']['edit_paths'].append('other.py')
  from branchwrite.coding_cli import _bytes
  x['sha256']=hashlib.sha256(_bytes(x['launch'])).hexdigest();f.write_bytes(_bytes(x))
  from branchwrite.coding_review import inspect_changes
  with self.assertRaisesRegex(ValueError,'configuration'):inspect_changes(self.state)
 def test_active_writer_excludes_review(self):
  self.make()
  from branchwrite.coding_review import inspect_changes
  from branchwrite.records import WriterBusy
  with RuntimeLog(self.state/'ledger'):
   with self.assertRaises(WriterBusy):inspect_changes(self.state)
