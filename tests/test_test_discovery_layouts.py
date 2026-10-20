"""Real sandbox discovery for ordinary and package-style test trees."""
import hashlib,tempfile,unittest
from pathlib import Path
from branchwrite.execution import Executor,Grant

class DiscoveryLayoutTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
 def make(self,test,*,package=False,helper=None):
  source=self.root/'source';(source/'tests').mkdir(parents=True)
  (source/'app.py').write_text('def add(a,b): return a+b\n')
  (source/'tests/test_app.py').write_text(test)
  if package:(source/'tests/__init__.py').touch()
  if helper is not None:(source/'tests/support.py').write_text(helper)
  return source,Executor.create(source,self.root/'world')
 def files(self,path):return {str(p.relative_to(path)):hashlib.sha256(p.read_bytes()).hexdigest() for p in path.rglob('*') if p.is_file()}
 def test_package_free_tests_import_project_and_preserve_all_bytes(self):
  source,e=self.make('import unittest\nfrom app import add\nclass Test(unittest.TestCase):\n def test_add(self): self.assertEqual(add(2,3),5)\n')
  before=self.files(source);world=self.files(e.workspace);r=e.run_tests('plain-pass',Grant((),True))
  self.assertEqual(r.exit_code,0,r.stderr.read_bytes());self.assertIn(b'Ran 1 test',r.stderr.read_bytes())
  self.assertFalse((e.workspace/'tests/__init__.py').exists());self.assertEqual(self.files(source),before);self.assertEqual(self.files(e.workspace),world)
 def test_package_free_assertion_failure_is_executed_not_import_failure(self):
  _,e=self.make('import unittest\nfrom app import add\nclass Test(unittest.TestCase):\n def test_wrong(self): self.assertEqual(add(2,3),9)\n')
  r=e.run_tests('plain-fail',Grant((),True));text=r.stderr.read_bytes()
  self.assertEqual(r.exit_code,1);self.assertIn(b'Ran 1 test',text);self.assertIn(b'AssertionError',text);self.assertNotIn(b'Start directory is not importable',text)
 def test_packaged_relative_imports_still_work(self):
  _,e=self.make('import unittest\nfrom .support import value\nfrom app import add\nclass Test(unittest.TestCase):\n def test_relative(self): self.assertEqual(add(value,1),5)\n',package=True,helper='value=4\n')
  r=e.run_tests('package-relative',Grant((),True));self.assertEqual(r.exit_code,0,r.stderr.read_bytes());self.assertIn(b'Ran 1 test',r.stderr.read_bytes())
 def test_package_free_tests_keep_readonly_and_host_boundaries(self):
  sentinel=self.root/'private-secret';sentinel.write_text('not mounted')
  test='import unittest\nfrom pathlib import Path\nclass Test(unittest.TestCase):\n def test_boundary(self):\n  self.assertFalse(Path('+repr(str(sentinel))+').exists())\n  with self.assertRaises(OSError): Path("app.py").write_text("changed")\n'
  source,e=self.make(test);before=self.files(e.workspace);r=e.run_tests('plain-boundary',Grant((),True))
  self.assertEqual(r.exit_code,0,r.stderr.read_bytes());self.assertEqual(self.files(e.workspace),before);self.assertEqual(sentinel.read_text(),'not mounted')

 def test_empty_suite_is_a_clear_nonzero_result(self):
  _,e=self.make('import unittest\n')
  r=e.run_tests('empty-suite',Grant((),True));self.assertEqual(r.exit_code,1)
  self.assertIn(b'no test cases',r.stderr.read_bytes().lower())
