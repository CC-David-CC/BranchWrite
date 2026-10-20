"""Another ordinary CLI must not write bytecode into an admitted package."""
import os,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
from branchwrite.cad_execution import _pins
from branchwrite.terminal import _stat_key

class CliRuntimeImmutabilityTests(unittest.TestCase):
 def test_help_after_initial_import_keeps_actual_package_bytes_and_metadata(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);package=root/'branchwrite'
   shutil.copytree(Path(__file__).parents[1]/'branchwrite',package,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
   env=dict(os.environ,PYTHONPATH=str(root));env.pop('PYTHONDONTWRITEBYTECODE',None)
   # Normal first startup imports the package before runtime admission.
   first=subprocess.run([sys.executable,'-c','import branchwrite'],cwd=root,env=env,capture_output=True,text=True)
   self.assertEqual(first.returncode,0,first.stderr)
   pins=_pins((package,));before={str(p):key for p,key,_ in pins}
   helper=subprocess.run([sys.executable,'-m','branchwrite','--help'],cwd=root,env=env,capture_output=True,text=True)
   self.assertEqual(helper.returncode,0,helper.stderr);self.assertIn('session',helper.stdout)
   after={str(p):key for p,key,_ in _pins((package,))}
   self.assertEqual(before,after,'parallel help changed the admitted runtime')
   # This does not exempt real code or cache changes from integrity checks.
   target=package/'language.py';target.write_bytes(target.read_bytes()+b'\n# changed source\n')
   self.assertNotEqual(before[str(target)],_stat_key(target.stat()))
 def test_precompiled_setup_allows_B_client_then_ordinary_help(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);package=root/'branchwrite'
   shutil.copytree(Path(__file__).parents[1]/'branchwrite',package,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
   env=dict(os.environ,PYTHONPATH=str(root));env.pop('PYTHONDONTWRITEBYTECODE',None)
   # Initial setup compiles the bootstrap even when the first client uses -B.
   import py_compile
   py_compile.compile(str(package/'__init__.py'),doraise=True)
   first=subprocess.run([sys.executable,'-B','-c','import branchwrite'],cwd=root,env=env,capture_output=True,text=True)
   self.assertEqual(first.returncode,0,first.stderr)
   pins=_pins((package,));before={str(p):key for p,key,_ in pins}
   helper=subprocess.run([sys.executable,'-m','branchwrite','--help'],cwd=root,env=env,capture_output=True,text=True)
   self.assertEqual(helper.returncode,0,helper.stderr);self.assertIn('session',helper.stdout)
   after={str(p):key for p,key,_ in _pins((package,))}
   self.assertEqual(before,after,'parallel help changed the admitted runtime')
   # This does not exempt real code or cache changes from integrity checks.
   target=package/'language.py';target.write_bytes(target.read_bytes()+b'\n# changed source\n')
   self.assertNotEqual(before[str(target)],_stat_key(target.stat()))
