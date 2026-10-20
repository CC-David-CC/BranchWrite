"""Initial setup must not clone all /usr or overwrite an existing runtime."""
import importlib.util,tempfile,unittest
from pathlib import Path

class PrivateClientInstallTests(unittest.TestCase):
 def factory(self):
  path=Path(__file__).parents[1]/'tools/install_private_client.py'
  spec=importlib.util.spec_from_file_location('bw_private_install',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
 def test_distro_python_refused_before_creating_a_private_copy(self):
  with tempfile.TemporaryDirectory() as tmp:
   target=Path(tmp)/'python'
   with self.assertRaisesRegex(ValueError,'standalone'):
    self.factory().copy_standalone_python(Path('/usr/bin/python3'),target)
   self.assertFalse(target.exists())
 def test_existing_destination_never_overwritten(self):
  with tempfile.TemporaryDirectory() as tmp:
   target=Path(tmp)/'python';target.mkdir();marker=target/'keep';marker.write_text('unchanged')
   with self.assertRaises(FileExistsError):self.factory().copy_standalone_python(Path('/usr/bin/python3'),target)
   self.assertEqual(marker.read_text(),'unchanged')
