"""Real commands produce declared artifacts;inputs and host neighbors stay protected."""
from pathlib import Path
import os,tempfile,unittest
from branchwrite.execution import Executor,Grant
from branchwrite.terminal import ShellConfig
class CommandOutputTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name);source=self.root/'source';source.mkdir();(source/'output').mkdir()
  (source/'input.txt').write_text('observed input')
  code=chr(10).join([
   'from pathlib import Path',
   'import tempfile,os',
   'target=Path("output/report.txt")',
   'target.parent.mkdir(exist_ok=True)',
   'with tempfile.NamedTemporaryFile(dir=target.parent,delete=False) as stream:',
   ' stream.write(("produced:"+Path("input.txt").read_text()).encode())',
   ' stream.flush();os.fsync(stream.fileno());temporary=Path(stream.name)',
   'os.replace(temporary,target)',
   'print("program-finished")',''])
  (source/'job.py').write_text(code)
  self.e=Executor.create(source,self.root/'world',shell=ShellConfig(timeout=5,expected_hostname=os.uname().nodename))
 def test_atomic_program_output_is_published_only_to_declared_leaf(self):
  g=Grant((),False,read_paths=('job.py','input.txt','output/report.txt'),
    allow_shell=True,output_paths=('output/report.txt',))
  r=self.e.run_shell('actual-producer',g,'python3 job.py')
  self.assertEqual(r.exit_code,0);self.assertEqual(r.disposition,'exited')
  self.assertEqual((self.e.workspace/'output/report.txt').read_bytes(),b'produced:observed input')
  self.assertEqual((self.e.workspace/'input.txt').read_text(),'observed input')
  self.assertFalse((self.e.source/'output/report.txt').exists())
  self.assertEqual(len(r.details['outputs']),1)
 def test_existing_readonly_shell_cannot_persist_program_outputs(self):
  g=Grant((),False,read_paths=('job.py','input.txt'),allow_shell=True)
  r=self.e.run_shell('readonly-producer',g,'python3 job.py')
  self.assertNotEqual(r.exit_code,0)
  self.assertIn(b'Read-only file system',r.stderr.read_bytes())
  self.assertFalse((self.e.workspace/'output/report.txt').exists())

class CommandOutputIntegrationTests(unittest.TestCase):
 setUp=CommandOutputTests.setUp
 def test_cli_accepts_explicit_output_grants(self):
  import json
  from branchwrite.run_cli import _config
  c=dict(schema=1,source=str(self.e.source),run_id='command-outputs',
   grant=dict(edit_paths=[],read_paths=['job.py','input.txt','output/report.txt'],create_paths=[],
              allow_tests=False,allow_shell=True,output_paths=['output/report.txt']),
   shell=dict(timeout=5,expected_hostname=os.uname().nodename),bindings={})
  self.assertEqual(_config(json.dumps(c))['grant']['output_paths'],['output/report.txt'])
 def test_registry_roots_actual_output_bytes_in_existing_runtime_log(self):
  import json
  from branchwrite.records import RuntimeLog,Artifact
  from branchwrite.tool_registry import ToolRegistry
  g=Grant((),False,read_paths=('job.py','input.txt','output/report.txt'),
    allow_shell=True,output_paths=('output/report.txt',))
  reg=ToolRegistry(self.e,g)
  r=reg.execute(reg.freeze(json.dumps(dict(tool='run_shell',arguments=dict(command='python3 job.py')))),'produce')
  with RuntimeLog(self.root/'ledger') as log:
   value,roots=r.publish(log)
   artifact=Artifact(*value['details']['outputs'][0]['artifact'])
   self.assertIn(artifact,roots)
   self.assertEqual(log.read_artifact(artifact),b'produced:observed input')

class CommandOutputSafetyTests(unittest.TestCase):
 setUp=CommandOutputTests.setUp
 def grant(self,paths=('output/report.txt',)):
  return Grant((),False,read_paths=('job.py','input.txt',*paths),allow_shell=True,output_paths=paths)
 def program(self,code):
  (self.e.workspace/'job.py').write_text(code)
 def test_undeclared_persistent_file_rejects_all_publication(self):
  self.program("from pathlib import Path;Path('output/report.txt').write_text('valid');Path('output/extra.txt').write_text('ungranted')")
  r=self.e.run_shell('extra',self.grant(),'python3 job.py')
  self.assertEqual(r.disposition,'output_rejected')
  self.assertFalse((self.e.workspace/'output/report.txt').exists())
  self.assertFalse((self.e.workspace/'output/extra.txt').exists())
 def test_output_symlink_rejected_without_host_effects(self):
  self.program("import os;os.symlink('/etc/passwd','output/report.txt')")
  r=self.e.run_shell('link',self.grant(),'python3 job.py')
  self.assertEqual(r.disposition,'output_rejected')
  self.assertFalse((self.e.workspace/'output/report.txt').is_symlink())
 def test_hardlinked_outputs_rejected(self):
  self.program("from pathlib import Path;import os;Path('output/report.txt').write_text('data');os.link('output/report.txt','output/copy.txt')")
  r=self.e.run_shell('hardlink',self.grant(('output/report.txt','output/copy.txt')),'python3 job.py')
  self.assertEqual(r.disposition,'output_rejected')
  self.assertFalse((self.e.workspace/'output/report.txt').exists())
 def test_per_file_overflow_rejected_with_bounded_private_storage(self):
  self.program("from pathlib import Path;Path('output/report.txt').write_bytes(b'x'*(4*1024*1024+1))")
  r=self.e.run_shell('overflow',self.grant(),'python3 job.py')
  self.assertEqual(r.disposition,'output_rejected')
  self.assertFalse((self.e.workspace/'output/report.txt').exists())
 def test_input_stays_readonly_with_output_capability(self):
  self.program("from pathlib import Path;Path('input.txt').write_text('attack')")
  r=self.e.run_shell('input-write',self.grant(),'python3 job.py')
  self.assertNotEqual(r.exit_code,0)
  self.assertEqual((self.e.workspace/'input.txt').read_text(),'observed input')
 def test_nonzero_status_preserves_actual_valid_output_effects(self):
  self.program("from pathlib import Path;Path('output/report.txt').write_text('partial');raise SystemExit(7)")
  r=self.e.run_shell('failed-producer',self.grant(),'python3 job.py')
  self.assertEqual(r.exit_code,7);self.assertEqual(r.disposition,'exited')
  self.assertEqual((self.e.workspace/'output/report.txt').read_text(),'partial')
 def test_inaccessible_output_parent_cannot_be_misreported_as_deletion(self):
  target=self.e.workspace/'output/report.txt';target.write_text('retained')
  self.program("import os;os.chmod('output',0)")
  r=self.e.run_shell('hidden-parent',self.grant(),'python3 job.py')
  self.assertEqual(r.disposition,'output_rejected')
  self.assertEqual(target.read_text(),'retained')
 def test_unchanged_stale_output_is_not_rewritten_as_fresh(self):
  target=self.e.workspace/'output/report.txt';target.write_text('stale');before=target.stat().st_mtime_ns
  r=self.e.run_shell('noop',self.grant(),'true')
  self.assertEqual(r.exit_code,0)
  self.assertEqual(target.stat().st_mtime_ns,before)
  self.assertFalse(r.details['outputs'][0]['changed'])
 def test_receipt_failure_after_publication_is_indeterminate(self):
  import json
  from unittest.mock import patch
  from branchwrite.tool_registry import ToolRegistry,EffectIndeterminate
  reg=ToolRegistry(self.e,self.grant())
  plan=reg.freeze(json.dumps(dict(tool='run_shell',arguments=dict(command='python3 job.py'))))
  with patch.object(self.e,'_result',side_effect=OSError('receipt publication failed')):
   with self.assertRaises(EffectIndeterminate):reg.execute(plan,'uncertain-producer')
  self.assertEqual((self.e.workspace/'output/report.txt').read_bytes(),b'produced:observed input')

class CommandOutputLifecycleTests(unittest.TestCase):
 setUp=CommandOutputTests.setUp
 grant=CommandOutputSafetyTests.grant
 program=CommandOutputSafetyTests.program
 def test_timeout_preserves_bounded_actual_effect_and_retires_namespace(self):
  self.e._shell=ShellConfig(timeout=0.2,expected_hostname=os.uname().nodename)
  self.program("from pathlib import Path;import time;Path('output/report.txt').write_text('before-timeout');time.sleep(30)")
  r=self.e.run_shell('timeout',self.grant(),'python3 job.py')
  self.assertEqual(r.disposition,'timeout');self.assertNotEqual(r.exit_code,0)
  self.assertEqual((self.e.workspace/'output/report.txt').read_text(),'before-timeout')
  self.assertTrue(r.details['isolation']['worker_exited'])
  self.assertEqual(r.details['isolation']['namespace_members_after'],[])
 def test_escaping_command_child_is_rejected_then_namespace_retires(self):
  self.program("import subprocess;from pathlib import Path;subprocess.Popen(['python3','-c','import time;time.sleep(30)'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True);Path('output/report.txt').write_text('unsettled')")
  r=self.e.run_shell('escaping-child',self.grant(),'python3 job.py')
  self.assertEqual(r.disposition,'output_rejected')
  self.assertFalse((self.e.workspace/'output/report.txt').exists())
  self.assertEqual(r.details['isolation']['namespace_members_after'],[])
 def test_protected_neighbor_in_writable_output_parent_stays_readonly(self):
  neighbor=self.e.workspace/'output/neighbor.txt';neighbor.write_text('protected')
  self.program("from pathlib import Path;Path('output/neighbor.txt').write_text('attack')")
  g=Grant((),False,read_paths=('job.py','input.txt','output/neighbor.txt','output/report.txt'),allow_shell=True,output_paths=('output/report.txt',))
  r=self.e.run_shell('neighbor',g,'python3 job.py')
  self.assertNotEqual(r.exit_code,0);self.assertIn(b'Read-only file system',r.stderr.read_bytes())
  self.assertEqual(neighbor.read_text(),'protected')
 def test_declared_output_deletion_has_receipt_and_preserves_old_artifact(self):
  target=self.e.workspace/'output/report.txt';target.write_text('old')
  self.program("from pathlib import Path;Path('output/report.txt').unlink()")
  r=self.e.run_shell('delete',self.grant(),'python3 job.py')
  self.assertEqual(r.exit_code,0);self.assertFalse(target.exists())
  self.assertTrue(r.details['outputs'][0]['deleted'])
  self.assertEqual(r.assets[0].read_bytes(),b'old')
 def test_top_level_output_does_not_make_input_writable(self):
  self.program("from pathlib import Path;Path('report.txt').write_text('root-output')")
  g=self.grant(('report.txt',))
  r=self.e.run_shell('top-level',g,'python3 job.py')
  self.assertEqual(r.exit_code,0);self.assertEqual((self.e.workspace/'report.txt').read_text(),'root-output')
  self.assertEqual((self.e.workspace/'input.txt').read_text(),'observed input')
 def test_stale_preimage_rejected_before_any_visible_output_publication(self):
  import base64,hashlib
  from branchwrite.command_outputs import initial_state,publish
  from branchwrite.execution import ToolRejected
  target=self.e.workspace/'output/report.txt';target.write_text('initial')
  paths=('output/report.txt',);before=initial_state(self.e,paths);target.write_text('newer')
  body=b'captured'
  row=dict(path=paths[0],deleted=False,bytes=len(body),data=base64.b64encode(body).decode(),sha256=hashlib.sha256(body).hexdigest(),mode='0600')
  with self.assertRaises(ToolRejected):publish(self.e,paths,before,[row],'stale')
  self.assertEqual(target.read_text(),'newer')
if __name__=='__main__':unittest.main()
