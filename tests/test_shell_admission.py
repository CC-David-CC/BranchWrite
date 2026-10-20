"""Host shell readiness and not-yet-created readable paths; real OS probes."""
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from branchwrite.execution import Executor,Grant,ToolRejected
from branchwrite.terminal import ShellConfig
class ShellAdmissionTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.base=Path(self.tmp.name);self.source=self.base/'source';self.source.mkdir()
  (self.source/'app.py').write_text('print("original")\n')
 def executor(self):
  return Executor.create(self.source,self.base/'world',shell=ShellConfig(timeout=5))
 def test_shell_rejection_precedes_any_cow_admission(self):
  from branchwrite.coding_cli import build_launch,PROGRAM
  from branchwrite.run_cli import execute
  connection=dict(endpoint_url='http://127.0.0.1:1',endpoint_pin='owned',model_contract_id='model',execution_profile_id='profile',eos_tokens=[256])
  launch=build_launch(self.source,'Repair app',connection,branch='new',read_paths=['app.py'],test_commands=['python3 -m unittest'])
  with patch.object(Executor,'check_shell_boundary',side_effect=ToolRejected('host namespace denied'),create=True),patch('branchwrite.run_cli.CowClient.http',side_effect=AssertionError('transport admitted before shell readiness')) as http:
   with self.assertRaisesRegex(ToolRejected,'namespace denied'):
    execute('run',PROGRAM,json.dumps(launch['config']),self.base/'run',max_steps=1)
   http.assert_not_called()
  self.assertFalse((self.base/'run/cow-operations').exists())
 def test_real_probe_settles_without_changing_workspace(self):
  executor=self.executor()
  before={str(p.relative_to(executor.workspace)):p.read_bytes() for p in executor.workspace.rglob('*') if p.is_file()}
  witness=executor.check_shell_boundary()
  self.assertTrue(witness['worker_exited'])
  self.assertEqual(witness['namespace_members_after'],[])
  self.assertEqual(before,{str(p.relative_to(executor.workspace)):p.read_bytes() for p in executor.workspace.rglob('*') if p.is_file()})
 def test_shell_can_test_before_and_after_granted_file_creation(self):
  executor=self.executor()
  grant=Grant((),False,read_paths=('app.py','future.py'),create_paths=('future.py',),allow_shell=True)
  first=executor.run_shell('before-create',grant,'python3 -c "import future"')
  self.assertEqual(first.disposition,'exited')
  self.assertNotEqual(first.exit_code,0)
  self.assertIn(b'ModuleNotFoundError',first.stderr.read_bytes())
  executor.create_file('create-future',grant,'future.py',b'VALUE=42\n')
  second=executor.run_shell('after-create',grant,'python3 -c "import future; print(future.VALUE)"')
  self.assertEqual(second.exit_code,0,second.stderr.read_bytes())
  self.assertEqual(second.stdout.read_bytes(),b'42\n')
 def test_missing_read_path_without_create_grant_still_fails(self):
  executor=self.executor()
  grant=Grant((),False,read_paths=('app.py','missing.py'),allow_shell=True)
  with self.assertRaises(ToolRejected):executor.run_shell('missing-read',grant,'true')
