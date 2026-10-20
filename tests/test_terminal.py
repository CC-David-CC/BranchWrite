"""Real Linux terminal boundaries; no model or reference-worker substitution."""
from pathlib import Path
import hashlib,json,os,sys,tempfile,time,unittest
from unittest.mock import patch
from branchwrite.execution import Executor,Grant,ToolRejected
class TerminalTests(unittest.TestCase):
 def make(self,root,code,*,timeout=3,reads=('marker.txt',),name='probe'):
  from branchwrite.terminal import NamedCommand
  source=root/'source';source.mkdir();(source/'marker.txt').write_bytes(b"marker-123\n");(source/'hidden.txt').write_bytes(b"must-not-be-mounted\n")
  command=NamedCommand(name,('/usr/bin/python3','-I','-B','-c',code),timeout)
  executor=Executor.create(source,root/'run',commands=(command,))
  grant=Grant((),False,read_paths=reads,command_names=(name,))
  return executor,grant
 def test_actual_separate_streams_literal_bytes_and_nonzero_status(self):
  with tempfile.TemporaryDirectory() as t:
   e,g=self.make(Path(t),"import os;os.write(1,\"hello 'Ubuntu' $HOME\\nΔ\\n\".encode());os.write(2,b'stderr-only\\n');raise SystemExit(7)")
   r=e.run_command('streams',g,'probe')
   self.assertEqual((r.disposition,r.exit_code),('exited',7))
   self.assertEqual(r.stdout.read_bytes(),"hello 'Ubuntu' $HOME\nΔ\n".encode())
   self.assertEqual(r.stderr.read_bytes(),b'stderr-only\n')
   self.assertTrue(r.details['isolation']['worker_exited'])
   self.assertEqual(r.details['isolation']['namespace_members_after'],[])
 def test_definition_is_immutable_bounded_and_not_a_shell_string(self):
  from dataclasses import FrozenInstanceError
  from branchwrite.terminal import NamedCommand
  q=NamedCommand('host',('/usr/bin/hostname',),3)
  with self.assertRaises(FrozenInstanceError):q.name='other'
  for args in [('bad name',('/usr/bin/hostname',),3),('bad','/usr/bin/hostname',3),('bad',('hostname',),3),('bad',('/tmp/program',),3),('bad',('/usr/bin/hostname',None),3),('bad',('/usr/bin/hostname',),True),('bad',('/usr/bin/hostname',),float('nan')),('bad',('/usr/bin/hostname',),121)]:
   with self.subTest(args=args),self.assertRaises(ValueError):NamedCommand(*args)
 def test_duplicate_and_malformed_catalogue_reject_before_workspace_creation(self):
  from branchwrite.terminal import NamedCommand
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);source=root/'source';source.mkdir();q=NamedCommand('host',('/usr/bin/hostname',))
   for index,commands in enumerate([(q,q),[q],('not-a-command',)]):
    run=root/('invalid-'+str(index))
    with self.assertRaises(ToolRejected):Executor.create(source,run,commands=commands)
    self.assertFalse(run.exists())
 def test_ungranted_or_unknown_command_rejects_before_spawn(self):
  with tempfile.TemporaryDirectory() as t:
   e,g=self.make(Path(t),"print('not reached')")
   before=list(e.run_dir.rglob('*'))
   with patch('subprocess.Popen') as spawn:
    for grant,name in [(Grant((),False),'probe'),(g,'unknown')]:
     with self.assertRaises(ToolRejected):e.run_command('denied',grant,name)
   spawn.assert_not_called();self.assertEqual(before,list(e.run_dir.rglob('*')))
 def test_argv_is_literal_without_implicit_shell_expansion(self):
  from branchwrite.terminal import NamedCommand
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);s=root/'source';s.mkdir()
   q=NamedCommand('literal',('/usr/bin/printf','%s\n','$HOME','$(touch /tmp/not-a-command)'),3)
   e=Executor.create(s,root/'run',commands=(q,));r=e.run_command('literal',Grant((),False,command_names=('literal',)),'literal')
   self.assertEqual(r.exit_code,0);self.assertEqual(r.stdout.read_bytes(),b'$HOME\n$(touch /tmp/not-a-command)\n')
 def test_actual_host_uid_cwd_and_granted_marker_are_bound(self):
  code="import json,os;from pathlib import Path;print(json.dumps(dict(hostname=os.uname().nodename,uid=os.getuid(),euid=os.geteuid(),gid=os.getgid(),cwd=os.getcwd(),marker=Path('marker.txt').read_text(),release=Path('/etc/os-release').read_text())))"
  with tempfile.TemporaryDirectory() as t:
   e,g=self.make(Path(t),code);r=e.run_command('identity',g,'probe');v=json.loads(r.stdout.read_bytes())
   self.assertEqual(r.exit_code,0);self.assertEqual(v['hostname'],os.uname().nodename)
   self.assertEqual((v['uid'],v['euid'],v['gid']),(os.getuid(),os.geteuid(),os.getgid()))
   self.assertEqual(v['cwd'],str(e.workspace));self.assertEqual(v['marker'],'marker-123\n')
   self.assertEqual(v['release'],Path('/etc/os-release').read_text())
   self.assertEqual(r.details['execution_host']['hostname'],os.uname().nodename)
   self.assertEqual(r.details['inputs'][0]['sha256'],hashlib.sha256(b'marker-123\n').hexdigest())
 def test_ungranted_files_home_devices_network_and_credentials_absent(self):
  code="""import os,socket
from pathlib import Path
assert not Path('hidden.txt').exists()
assert not Path('/home/dflanag3/.ssh').exists()
assert not list(Path('/dev').glob('nvidia*'))
assert os.environ.get('BW_TEST_SECRET') is None
s=socket.socket();s.settimeout(.2)
try:s.connect(('1.1.1.1',443))
except OSError:pass
else:raise AssertionError('network escaped')
print('isolated')
"""
  with tempfile.TemporaryDirectory() as t:
   e,g=self.make(Path(t),code)
   with patch.dict(os.environ,{'BW_TEST_SECRET':'not-for-child'}):r=e.run_command('isolated',g,'probe')
   self.assertEqual(r.exit_code,0,r.stderr.read_bytes());self.assertEqual(r.stdout.read_bytes(),b'isolated\n')
 def test_granted_input_is_readonly_and_original_bytes_unchanged(self):
  code="from pathlib import Path\ntry:Path('marker.txt').write_text('bad')\nexcept OSError:print('readonly')\nelse:raise AssertionError('write unexpectedly allowed')"
  with tempfile.TemporaryDirectory() as t:
   e,g=self.make(Path(t),code);r=e.run_command('readonly',g,'probe')
   self.assertEqual(r.exit_code,0,r.stderr.read_bytes());self.assertEqual(r.stdout.read_bytes(),b'readonly\n')
   self.assertEqual((e.workspace/'marker.txt').read_bytes(),b'marker-123\n')
 def test_timeout_is_bounded_and_namespace_retires(self):
  with tempfile.TemporaryDirectory() as t:
   e,g=self.make(Path(t),"import time;print('started',flush=True);time.sleep(60)",timeout=.2)
   started=time.monotonic();r=e.run_command('timeout',g,'probe')
   self.assertEqual(r.disposition,'timeout');self.assertLess(time.monotonic()-started,5)
   self.assertEqual(r.stdout.read_bytes(),b'started\n');self.assertEqual(r.details['isolation']['namespace_members_after'],[])
 def test_signal_exit_is_not_converted_to_success(self):
  with tempfile.TemporaryDirectory() as t:
   e,g=self.make(Path(t),"import os,signal;os.kill(os.getpid(),signal.SIGTERM)")
   r=e.run_command('signal',g,'probe');self.assertEqual((r.disposition,r.exit_code),('exited',-15))
 def test_output_limit_is_reported_and_namespace_retires(self):
  with tempfile.TemporaryDirectory() as t:
   e,g=self.make(Path(t),"import os\nwhile True:os.write(1,b'x'*65536)")
   r=e.run_command('overflow',g,'probe')
   self.assertEqual(r.disposition,'output_limit');self.assertEqual(len(r.stdout.read_bytes()),1024*1024)
   self.assertEqual(r.details['isolation']['namespace_members_after'],[])
 def test_detached_descendant_cannot_survive_namespace_retirement(self):
  code="import subprocess;subprocess.Popen(['/usr/bin/python3','-I','-B','-c','import os,time;os.setsid();time.sleep(60)'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);print('parent done')"
  with tempfile.TemporaryDirectory() as t:
   e,g=self.make(Path(t),code);r=e.run_command('descendant',g,'probe')
   self.assertEqual(r.exit_code,0,r.stderr.read_bytes());self.assertEqual(r.stdout.read_bytes(),b'parent done\n')
   self.assertEqual(r.details['isolation']['namespace_members_after'],[])
 def test_symlink_and_hardlink_inputs_are_not_mounted(self):
  for kind in ['symlink','hardlink']:
   with self.subTest(kind=kind),tempfile.TemporaryDirectory() as t:
    e,g=self.make(Path(t),"print('not reached')");f=e.workspace/'marker.txt';f.unlink()
    if kind=='symlink':f.symlink_to(e.source/'marker.txt')
    else:os.link(e.source/'marker.txt',f)
    with patch('subprocess.Popen') as spawn:
     with self.assertRaises((ToolRejected,OSError)):e.run_command('alias',g,'probe')
    spawn.assert_not_called()
 def test_unknown_namespace_retirement_cannot_publish_result(self):
  with tempfile.TemporaryDirectory() as t:
   e,g=self.make(Path(t),"print('observed')")
   with patch('branchwrite.browser_isolation.await_namespace_retirement',return_value=[123]):
    with self.assertRaises(ValueError):e.run_command('unknown',g,'probe')
   self.assertFalse(any(e.artifacts.iterdir()))
if __name__=='__main__':unittest.main()
