"""Actual OS cancellation/status distinctions; no model or mocked processes."""
from pathlib import Path
import json,subprocess,tempfile,time,unittest
import test_terminal

class CancellationContractTests(unittest.TestCase):
 def test_waiting_child_times_out_and_entire_namespace_retires(self):
  code="import subprocess; p=subprocess.Popen(['/usr/bin/sleep','30']); print(p.pid,flush=True); p.wait()"
  with tempfile.TemporaryDirectory() as td:
   executor,grant=test_terminal.TerminalTests.make(self,Path(td),code,timeout=.3)
   started=time.monotonic()
   result=executor.run_command('child-timeout',grant,'probe')
   self.assertEqual(result.disposition,'timeout')
   self.assertNotEqual(result.exit_code,0)
   self.assertTrue(result.stdout.read_bytes().strip().isdigit())
   self.assertTrue(result.details['isolation']['worker_exited'])
   self.assertEqual(result.details['isolation']['namespace_members_after'],[])
   self.assertLess(time.monotonic()-started,5)
 def test_worker_spawn_failure_is_not_shell_command_not_found(self):
  worker=Path(__file__).resolve().parents[1]/'branchwrite/terminal_worker.py'
  payload=dict(argv=['/definitely-absent-bw-executable-7375'],timeout=1)
  actual=subprocess.run(['/usr/bin/python3','-B',str(worker)],input=json.dumps(payload).encode(),capture_output=True,timeout=5,check=True)
  row=json.loads(actual.stdout)
  self.assertEqual(row['disposition'],'spawn_error')
  self.assertIsNone(row['exit_code'])
  self.assertIn('No such file',__import__('base64').b64decode(row['stderr']).decode())
 def test_shell_missing_command_remains_real_exit127(self):
  code="import subprocess; raise SystemExit(subprocess.run(['/usr/bin/bash','--noprofile','--norc','-c','definitely_absent_bw_command_7375']).returncode)"
  with tempfile.TemporaryDirectory() as td:
   executor,grant=test_terminal.TerminalTests.make(self,Path(td),code)
   result=executor.run_command('missing-shell-command',grant,'probe')
   self.assertEqual((result.disposition,result.exit_code),('exited',127))
