"""Actual helper subprocesses: capture limits must not restrict command files."""
import base64,json,shlex,subprocess,sys,tempfile,unittest
from pathlib import Path
from branchwrite import remote_guest

class RemoteGuestTests(unittest.TestCase):
 def run_guest(self,command,timeout=3):
  request=dict(schema=1,operation_id='helper-test',command=command,timeout=timeout)
  p=subprocess.run([sys.executable,str(Path(remote_guest.__file__))],input=json.dumps(request).encode(),capture_output=True,timeout=timeout+8)
  self.assertEqual(p.returncode,0,p.stderr.decode(errors='replace'))
  reply=json.loads(p.stdout)
  self.assertEqual(reply['operation_id'],request['operation_id'])
  return reply,base64.b64decode(reply['stdout_b64']),base64.b64decode(reply['stderr_b64'])
 def test_large_command_file_write_is_not_a_capture_limit(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'apt-like-download'
   code="from pathlib import Path; Path("+repr(str(p))+").write_bytes(b'x'*(2*1024*1024)); print('written')"
   reply,out,err=self.run_guest(shlex.join([sys.executable,'-c',code]))
   self.assertEqual(reply['disposition'],'exited')
   self.assertEqual(reply['exit_code'],0,err)
   self.assertEqual(p.stat().st_size,2*1024*1024)
   self.assertEqual(out,b'written\n')
 def test_binary_streams_and_nonzero_exit_are_preserved(self):
  code="import os; os.write(1,bytes(range(256))); os.write(2,b'error\\x00tail'); raise SystemExit(23)"
  reply,out,err=self.run_guest(shlex.join([sys.executable,'-c',code]))
  self.assertEqual((reply['disposition'],reply['exit_code']),('exited',23))
  self.assertEqual(out,bytes(range(256)));self.assertEqual(err,b'error\x00tail')
 def test_stdout_and_stderr_limits_are_independent(self):
  for fd in [1,2]:
   with self.subTest(fd=fd):
    code="import os; os.write("+str(fd)+",b'z'*(4*1024*1024))"
    reply,out,err=self.run_guest(shlex.join([sys.executable,'-c',code]))
    self.assertEqual(reply['disposition'],'output_limit')
    self.assertEqual(len(out if fd==1 else err),remote_guest.LIMIT)
    self.assertLessEqual(len(out),remote_guest.LIMIT);self.assertLessEqual(len(err),remote_guest.LIMIT)
 def test_timeout_is_bounded_and_keeps_prior_output(self):
  code="import os,time; os.write(1,b'started'); time.sleep(10)"
  reply,out,err=self.run_guest(shlex.join([sys.executable,'-c',code]),timeout=.2)
  self.assertEqual(reply['disposition'],'timeout');self.assertEqual(out,b'started')
 def test_simultaneous_streams_do_not_deadlock(self):
  code="import os; [(os.write(1,b'a'*8192),os.write(2,b'b'*8192)) for _ in range(32)]"
  reply,out,err=self.run_guest(shlex.join([sys.executable,'-c',code]))
  self.assertEqual((reply['disposition'],reply['exit_code']),('exited',0))
  self.assertEqual(out,b'a'*(8192*32));self.assertEqual(err,b'b'*(8192*32))

 def test_version_two_exact_stdin_exceeds_shell_argument_limits(self):
  body=bytes(range(256))*8192
  request=dict(schema=2,operation_id='payload',command='cat',timeout=3,stdin_b64=base64.b64encode(body).decode())
  # cat intentionally exceeds the capture limit: command input is separately
  # bounded and is not confused with stdout truncation.
  p=subprocess.run([sys.executable,str(Path(remote_guest.__file__))],input=json.dumps(request).encode(),capture_output=True,timeout=8)
  self.assertEqual(p.returncode,0,p.stderr)
  reply=json.loads(p.stdout);self.assertEqual(reply['disposition'],'output_limit')
  self.assertEqual(base64.b64decode(reply['stdout_b64']),body[:remote_guest.LIMIT])
