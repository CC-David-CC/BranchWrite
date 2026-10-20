"""Full-project baselines precede tools and survive mutable checkout changes."""
import tempfile,unittest
from pathlib import Path
from branchwrite.records import RuntimeLog,MissingArtifact
from branchwrite.execution import Executor,Grant,ToolRejected
from branchwrite.tool_registry import ToolRegistry
class ProjectBaselineTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name);self.source=self.root/'source';self.source.mkdir()
  (self.source/'app.py').write_bytes(bytes([0,255,10]))
  (self.source/'empty').mkdir()
  self.ex=Executor.create(self.source,self.root/'world')
  self.registry=ToolRegistry(self.ex,Grant((),False))
 def test_saved_bytes_do_not_follow_later_workspace_or_original_changes(self):
  from branchwrite.project_baseline import capture,load
  with RuntimeLog(self.root/'ledger') as log:
   ref=capture(log,self.registry);original=load(log,ref)
   (self.ex.workspace/'app.py').write_bytes(b'new workspace')
   (self.source/'app.py').write_bytes(b'new checkout')
   self.assertEqual(load(log,ref),original)
   self.assertEqual(original['files']['app.py']['bytes'],bytes([0,255,10]))
   self.assertIn('empty',original['directories'])
 def test_missing_payload_is_rejected(self):
  from branchwrite.project_baseline import capture,load
  with RuntimeLog(self.root/'ledger') as log:
   ref=capture(log,self.registry);old=load(log,ref)
   (log.artifacts/old['files']['app.py']['sha256']).unlink()
   with self.assertRaises(MissingArtifact):load(log,ref)
 def test_links_are_rejected_without_reading_target(self):
  from branchwrite.project_baseline import capture
  (self.ex.workspace/'link').symlink_to('/etc/passwd')
  with RuntimeLog(self.root/'ledger') as log:
   with self.assertRaises(ToolRejected):capture(log,self.registry)
 def test_manifest_is_chunked_beyond_codec_container_limit(self):
  from branchwrite.project_baseline import capture,load
  for i in range(4100):(self.ex.workspace/('file'+str(i))).touch()
  with RuntimeLog(self.root/'ledger') as log:
   ref=capture(log,self.registry);data=load(log,ref)
   self.assertEqual(len(data['files']),4101)

 def test_real_cli_binds_manifest_and_reuses_it_after_a_restart(self):
  import subprocess,sys,json,os
  from branchwrite.kernel import FrameKernel
  from branchwrite.records import Artifact,decode
  from branchwrite.project_baseline import BINDING,load,parse_reference
  state=self.root/'cli-state';program=self.root/'job.bw';config=self.root/'config.json'
  program.write_text(chr(10).join(['FLOW job','TEXT task','|Hello','END','END','']))
  config.write_text(json.dumps(dict(schema=1,source=str(self.source),source_policy='metadata-free-project-v1',
   run_id='baseline-test',grant=dict(edit_paths=[],create_paths=[],read_paths=[],allow_tests=False),bindings={},profiles={})))
  args=[str(program),'--config',str(config),'--state',str(state)]
  first=subprocess.run([sys.executable,'-B','-m','branchwrite','step',*args],capture_output=True,text=True)
  self.assertEqual(first.returncode,3,first.stderr)
  def baseline():
   with RuntimeLog(state/'ledger',read_only=True) as log:
    k=FrameKernel(log);root=k.frame('program')
    inputs=decode(log.read_artifact(Artifact(*root['inputs'])))
    typed=inputs['bindings'][BINDING];self.assertEqual(typed[0],'Text')
    return typed,load(log,parse_reference(typed[1]))
  ref,initial=baseline()
  (self.source/'app.py').write_bytes(b'changed checkout')
  (state/'world/workspace/app.py').write_bytes(b'changed workspace')
  second=subprocess.run([sys.executable,'-B','-m','branchwrite','run',*args],capture_output=True,text=True)
  self.assertEqual(second.returncode,1,second.stderr)
  self.assertEqual(baseline(),(ref,initial))
