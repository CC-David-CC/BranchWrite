"""Actual bounded Linux CAD worker; no mock execution or model claim."""
import tempfile,unittest
from pathlib import Path
from branchwrite.cad_execution import CadRuntime,build_candidate
from branchwrite.cad_inspect import inspect_step
from test_cad_geometry import spec
RUNTIME=Path('/home/dflanag3/spatial-artifacts/bw-build123d-20261020/cadvenv/bin/python')
SOURCE=b"""from build123d import *
p=Box(100,60,4,align=(Align.CENTER,Align.CENTER,Align.MIN))
for x in (-38,38):
 for y in (-18,18):p-=Pos(x,y)*Cylinder(2.5,4,align=(Align.CENTER,Align.CENTER,Align.MIN))
p-=Pos(47,0)*Box(6,10,4,align=(Align.CENTER,Align.CENTER,Align.MIN))
export_step(p,'part.step')
"""
class CadExecutionTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.runtime=CadRuntime(RUNTIME,timeout=30)
 def test_build_export_reopen_and_namespace_retirement(self):
  r=build_candidate((('model.py',SOURCE),),'model.py',self.runtime)
  self.assertEqual(r['disposition'],'built');self.assertEqual(r['exit_code'],0)
  self.assertTrue(r['isolation']['worker_exited']);self.assertEqual(r['isolation']['namespace_members_after'],[])
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'part.step';p.write_bytes(r['step']);self.assertEqual(inspect_step(p,spec())['status'],'PASS')
 def test_project_helpers_work_without_host_import_access(self):
  r=build_candidate((('model.py',b"import helper; from pathlib import Path; Path('part.step').write_text(helper.VALUE)"),('helper.py',b"VALUE='not STEP'")),'model.py',self.runtime)
  self.assertEqual(r['step'],b'not STEP') # Execution success alone is not geometry acceptance.
 def test_host_home_checker_and_network_are_unavailable(self):
  code=b"""import os,socket,pathlib
assert 'BW_COW_API_KEY' not in os.environ
assert not pathlib.Path('/home/dflanag3/.ssh').exists()
assert not pathlib.Path('/app/branchwrite/cad_inspect.py').exists()
try:socket.create_connection(('10.0.7.68',8099),timeout=.2)
except OSError:pass
else:raise AssertionError('network escaped')
pathlib.Path('part.step').write_text('boundaries checked')
"""
  r=build_candidate((('model.py',code),),'model.py',self.runtime);self.assertEqual(r['exit_code'],0,r['stderr'])
 def test_no_export_cannot_reuse_old_output(self):
  r=build_candidate((('model.py',b'pass'),('part.step',b'old STEP')),'model.py',self.runtime)
  self.assertEqual(r['disposition'],'missing_artifact');self.assertIsNone(r['step'])
 def test_link_output_rejected(self):
  r=build_candidate((('model.py',b"import os;os.symlink('/etc/passwd','part.step')"),),'model.py',self.runtime)
  self.assertEqual(r['disposition'],'output_rejected');self.assertIsNone(r['step'])
 def test_timeout_retires_processes(self):
  runtime=CadRuntime(RUNTIME,timeout=1)
  r=build_candidate((('model.py',b'import time;time.sleep(30)'),),'model.py',runtime)
  self.assertEqual(r['disposition'],'timeout');self.assertTrue(r['isolation']['worker_exited'])
 def test_invalid_paths_and_duplicate_inputs_fail_before_execution(self):
  for sources in [(('../model.py',SOURCE),),(('/model.py',SOURCE),),(('model.py',SOURCE),('model.py',SOURCE))]:
   with self.subTest(sources=sources):
    with self.assertRaises(ValueError):build_candidate(sources,'model.py',self.runtime)

 def test_fork_denied_but_threads_allowed(self):
  code=b"""import os,threading,pathlib
results=[]
t=threading.Thread(target=lambda:results.append(37));t.start();t.join()
assert results==[37]
try:pid=os.fork()
except PermissionError:pass
else:
 if pid==0:os._exit(0)
 os.waitpid(pid,0)
 raise AssertionError('candidate could create processes')
pathlib.Path('part.step').write_text('thread succeeded, fork denied')
"""
  r=build_candidate((('model.py',code),),'model.py',self.runtime)
  self.assertEqual(r['exit_code'],0,r['stderr'])
  self.assertEqual(r['step'],b'thread succeeded, fork denied')
 def test_output_flood_is_bounded_and_namespace_retired(self):
  r=build_candidate((('model.py',b"import os;os.write(1,b'x'*(2*1024*1024))"),),'model.py',self.runtime)
  self.assertEqual(r['disposition'],'output_limit')
  self.assertLessEqual(len(r['stdout']),1024*1024)
  self.assertTrue(r['isolation']['worker_exited'])
 def test_input_file_directory_collision_rejected(self):
  with self.assertRaises(ValueError):
   build_candidate((('model.py',b'pass'),('a',b'x'),('a/b.py',b'pass')),'model.py',self.runtime)
