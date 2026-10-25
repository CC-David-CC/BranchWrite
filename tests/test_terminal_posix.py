"""Normal POSIX shell paths inside the actual restricted BW namespace."""
from pathlib import Path
import shlex, tempfile, unittest, uuid
from branchwrite.execution import Executor, Grant
from branchwrite.terminal import ShellConfig


class TerminalPosixTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.source=self.root/'source';self.source.mkdir()
        (self.source/'note').write_text('unchanged')
        self.executor=Executor.create(self.source,self.root/'world',shell=ShellConfig(timeout=3))
        self.grant=Grant((),True,allow_shell=True)

    def command(self, name, body):
        return self.executor.run_shell(name,self.grant,'python3 -c '+shlex.quote(body))

    def test_python_shell_true_and_shebang_use_the_granted_shell(self):
        body="""import pathlib,subprocess,tempfile
assert pathlib.Path('/bin/sh').resolve()==pathlib.Path('/usr/bin/sh').resolve()
assert not pathlib.Path('/home').exists() and not pathlib.Path('/etc/shadow').exists()
one=subprocess.run('printf posix-shell',shell=True,check=True,capture_output=True,text=True)
assert one.stdout=='posix-shell'
with tempfile.TemporaryDirectory() as directory:
 p=pathlib.Path(directory)/'script';p.write_text('#!/bin/sh\\nprintf shebang-shell\\n');p.chmod(0o700)
 two=subprocess.run([str(p)],check=True,capture_output=True,text=True)
 assert two.stdout=='shebang-shell'
print('normal shell paths work')"""
        result=self.command('posix-shell',body)
        self.assertEqual(result.disposition,'exited')
        self.assertEqual(result.exit_code,0,result.stderr.path.read_bytes().decode(errors='replace'))
        self.assertEqual(result.stdout.path.read_bytes(),b'normal shell paths work\n')

    def test_bin_alias_does_not_make_system_binaries_writable(self):
        name='bw-posix-no-write-'+uuid.uuid4().hex
        target=Path('/usr/bin')/name;self.assertFalse(target.exists())
        result=self.executor.run_shell('readonly-alias',self.grant,'printf changed > /bin/'+name)
        self.assertNotEqual(result.exit_code,0)
        self.assertIn(b'Read-only file system',result.stderr.path.read_bytes())
        self.assertFalse(target.exists())

    def test_temporary_files_do_not_survive_another_invocation(self):
        first=self.executor.run_shell('make-temporary',self.grant,'printf fixture > /tmp/bw-ephemeral-test; cat /tmp/bw-ephemeral-test')
        second=self.executor.run_shell('fresh-temporary',self.grant,'test ! -e /tmp/bw-ephemeral-test')
        self.assertEqual(first.exit_code,0,first.stderr)
        self.assertEqual(first.stdout.path.read_bytes(),b'fixture')
        self.assertEqual(second.exit_code,0,second.stderr)
        self.assertEqual((self.source/'note').read_text(),'unchanged')

    def test_registered_unit_worker_supports_python_shell_true(self):
        (self.source/'tests').mkdir()
        (self.source/'tests/__init__.py').write_text('')
        (self.source/'tests/test_shell.py').write_text("import subprocess,unittest\nclass Shell(unittest.TestCase):\n def test_shell(self):\n  r=subprocess.run('printf worker-shell',shell=True,capture_output=True,text=True,check=True)\n  self.assertEqual(r.stdout,'worker-shell')\n")
        executor=Executor.create(self.source,self.root/'unit-world')
        result=executor.run_tests('unit-shell',self.grant)
        self.assertEqual(result.exit_code,0,result.stderr.path.read_bytes().decode(errors='replace'))


if __name__=='__main__':
    unittest.main()
