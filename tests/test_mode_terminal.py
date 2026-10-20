"""Actual terminal projection must honor file mode while remaining read-only."""
from pathlib import Path
import hashlib,os,tempfile,unittest
from branchwrite.execution import Executor,Grant
from branchwrite.terminal import ShellConfig
class ModeTerminalTests(unittest.TestCase):
 def test_readonly_projection_preserves_observed_mode_and_actual_execution(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);source=root/'source';source.mkdir()
   body=chr(10).join(['#!/usr/bin/env bash',"printf 'executed-probe\n'",'']).encode()
   (source/'task.sh').write_bytes(body);(source/'task.sh').chmod(0o640)
   e=Executor.create(source,root/'world',shell=ShellConfig(timeout=5,expected_hostname=os.uname().nodename))
   g=Grant((),False,read_paths=('task.sh',),allow_shell=True,mode_paths=('task.sh',),mode_mask=0o100)
   initial=e.run_shell('stat-before',g,'stat -c %a task.sh')
   self.assertEqual(initial.stdout.read_bytes(),b'640'+bytes([10]))
   denied=e.run_shell('direct-before',g,'./task.sh');self.assertEqual(denied.exit_code,126)
   e.set_mode('set-execute',g,'task.sh',hashlib.sha256(body).hexdigest(),'0740')
   final=e.run_shell('stat-after',g,'stat -c %a task.sh')
   self.assertEqual(final.stdout.read_bytes(),b'740'+bytes([10]))
   success=e.run_shell('direct-after',g,'./task.sh')
   self.assertEqual(success.exit_code,0);self.assertEqual(success.stdout.read_bytes(),b'executed-probe'+bytes([10]))
   write=e.run_shell('write-denied',g,"printf changed > task.sh")
   self.assertNotEqual(write.exit_code,0)
   self.assertEqual((e.workspace/'task.sh').read_bytes(),body)
if __name__=='__main__':unittest.main()
