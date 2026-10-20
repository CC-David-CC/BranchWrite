"""Actual distro-Python venv admission without pinning unrelated /usr data."""
import subprocess,tempfile,unittest
from pathlib import Path
from branchwrite.cad_execution import CadRuntime,build_candidate

class SystemPythonRuntimeTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.prefix=self.root/'venv'
  subprocess.run(['/usr/bin/python3','-m','venv','--without-pip',str(self.prefix)],check=True,capture_output=True)
 def test_distro_venv_admits_and_executes_in_retired_isolation(self):
  runtime=CadRuntime(self.prefix/'bin/python')
  self.assertNotIn(Path('/usr'),[p for p,_,_ in runtime._pins])
  built=build_candidate((('model.py',b"from pathlib import Path;Path('part.step').write_bytes(b'actual-export')"),),'model.py',runtime)
  self.assertEqual(built['disposition'],'built',built['stderr']);self.assertEqual(built['step'],b'actual-export')
  self.assertTrue(built['isolation']['worker_exited']);self.assertEqual(built['isolation']['namespace_members_after'],[])
 def test_venv_link_to_unrelated_private_file_remains_rejected(self):
  secret=self.root/'unrelated-private';secret.write_text('not a runtime dependency')
  (self.prefix/'leaked').symlink_to(secret)
  with self.assertRaises(ValueError):CadRuntime(self.prefix/'bin/python')
 def test_admitted_venv_module_mutation_is_still_rejected(self):
  module=self.prefix/'runtime-marker.py';module.write_text('value=1')
  runtime=CadRuntime(self.prefix/'bin/python');module.write_text('value=2')
  with self.assertRaises(ValueError):runtime.check()
