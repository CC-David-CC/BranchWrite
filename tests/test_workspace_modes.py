"""Owned workspace preserves ordinary file modes independently of umask."""
from pathlib import Path
import os,stat,tempfile,unittest
from branchwrite.execution import Executor
class WorkspaceModesTests(unittest.TestCase):
 def test_copy_preserves_basic_file_modes_under_restrictive_umask(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);source=root/'source';source.mkdir()
   modes=(0o664,0o640,0o740,0o444,0o600)
   for mode in modes:
    p=source/str(mode);p.write_bytes(b'unchanged');p.chmod(mode)
   old=os.umask(0o077)
   try:executor=Executor.create(source,root/'world')
   finally:os.umask(old)
   for mode in modes:
    with self.subTest(mode=oct(mode)):
     p=executor.workspace/str(mode)
     self.assertEqual(stat.S_IMODE(p.stat().st_mode),mode)
     self.assertEqual(p.read_bytes(),b'unchanged')
 def test_copy_preserves_nested_directory_basic_modes(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);source=root/'source';source.mkdir();nested=source/'nested'
   nested.mkdir();(nested/'file').write_bytes(b'x');nested.chmod(0o770)
   executor=Executor.create(source,root/'world')
   self.assertEqual(stat.S_IMODE((executor.workspace/'nested').stat().st_mode),0o770)
   self.assertEqual(stat.S_IMODE(executor.workspace.stat().st_mode),0o700)
