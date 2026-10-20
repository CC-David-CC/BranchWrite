"""Real namespace and Chromium witnesses; synthetic screenshots cannot pass."""
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest

from branchwrite.browser_capture import BrowserConfig


class BrowserIsolationTests(unittest.TestCase):
    def config(self, **kwargs):
        return BrowserConfig(Path(os.environ['BW_BROWSER_EXECUTABLE']), **kwargs)

    def test_actual_namespace_cannot_read_host_secret_or_connect_to_host_listener(self):
        from branchwrite.browser_isolation import isolation_command
        with tempfile.TemporaryDirectory() as directory, socket.socket() as listener:
            secret = Path(directory) / 'secret'
            secret.write_text('HOST_ONLY_CANARY')
            listener.bind(('127.0.0.1', 0))
            listener.listen()
            script = '''import json,os,socket,sys
s=socket.socket();s.settimeout(.2)
try:s.connect(('127.0.0.1',int(sys.argv[2])));connected=True
except OSError:connected=False
print(json.dumps(dict(secret_exists=os.path.exists(sys.argv[1]),connected=connected,
    env_secret=os.environ.get('BW_ISOLATION_CANARY'),pid_ns=os.readlink('/proc/self/ns/pid'),
    net_ns=os.readlink('/proc/self/ns/net'),uid=os.getuid())))
'''
            command = isolation_command(self.config())
            delimiter = len(command) - 1 - command[::-1].index('--')
            command[delimiter + 1:] = [sys.executable, '-I', '-B', '-c', script,
                                      str(secret), str(listener.getsockname()[1])]
            result = subprocess.run(command, capture_output=True, timeout=10,
                                    env={**os.environ, 'BW_ISOLATION_CANARY': 'MUST_NOT_INHERIT'})
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            witness = json.loads(result.stdout)
            self.assertFalse(witness['secret_exists'])
            self.assertFalse(witness['connected'])
            self.assertIsNone(witness['env_secret'])
            self.assertNotEqual(witness['pid_ns'], os.readlink('/proc/self/ns/pid'))
            self.assertNotEqual(witness['net_ns'], os.readlink('/proc/self/ns/net'))
            self.assertNotEqual(witness['uid'], 0, 'Chromium must keep its own sandbox enabled')

    def test_actual_chromium_capture_binds_isolation_and_exact_source(self):
        from branchwrite.browser_capture import render_snapshot
        page = b'<!doctype html><style>body{margin:0;background:white}</style><h1>Loop Lab</h1>'
        rendered = render_snapshot(page, self.config())
        self.assertEqual(rendered.served_sha256, hashlib.sha256(page).hexdigest())
        witness = rendered.isolation
        self.assertEqual(witness['schema'], 1)
        self.assertEqual(witness['kind'], 'bubblewrap-browser-v1')
        self.assertNotEqual(witness['net_ns'], os.readlink('/proc/self/ns/net'))
        self.assertNotEqual(witness['pid_ns'], os.readlink('/proc/self/ns/pid'))
        self.assertTrue(witness['worker_exited'])
        self.assertTrue(witness['chromium_sandbox'])
        self.assertTrue(rendered.png.startswith(b'\x89PNG\r\n\x1a\n'))

    def test_deadline_reaps_an_owned_namespace_with_a_spawned_child(self):
        from branchwrite.browser_isolation import isolation_command
        from branchwrite.execution import Executor
        command = isolation_command(self.config())
        delimiter = len(command) - 1 - command[::-1].index('--')
        script = '''import os,subprocess,sys,time
subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'])
print(os.readlink('/proc/self/ns/pid'),flush=True)
time.sleep(30)
'''
        command[delimiter + 1:] = [sys.executable, '-I', '-B', '-c', script]
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, start_new_session=True, close_fds=True)
        started = time.monotonic()
        out, err, timed_out, limited, _ = Executor._capture(process, started + 1, 4096)
        self.assertTrue(timed_out, err.decode())
        self.assertFalse(limited)
        self.assertLess(time.monotonic() - started, 4)
        namespace = out.decode().strip()
        self.assertTrue(namespace.startswith('pid:['), err.decode())
        self.assertIsNotNone(process.returncode)
        members = []
        for p in Path('/proc').iterdir():
            if p.name.isdecimal():
                try:
                    if os.readlink(p / 'ns/pid') == namespace:
                        members.append(p.name)
                except (FileNotFoundError, PermissionError, ProcessLookupError):
                    pass
        self.assertEqual(members, [], 'owned descendants must die with the namespace')


if __name__ == '__main__':
    unittest.main()
