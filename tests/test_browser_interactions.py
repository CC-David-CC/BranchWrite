"""Real isolated Chromium counter actions; supplied checks remain unchanged."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib
import unittest
from branchwrite.browser_capture import BrowserConfig, PageInspection, render_snapshot


class BrowserInteractionTests(unittest.TestCase):
    def setUp(self):
        self.pack = Path(os.environ['BW_BASIC_LOOP_PACK'])
        self.check = self.pack/'protected/checks.py'
        self.check_bytes = self.check.read_bytes()
        self.payload = (self.pack/'fixtures/starter/H06/index.html').read_bytes()
        self.controls = (b'<button id="increment">Add one</button><output id="count">0</output>'
            b'<script>document.querySelector("#increment").addEventListener("click",()=>{'
            b'const n=document.querySelector("#count");n.textContent=String(Number(n.textContent)+1);});</script>')
        self.good = self.payload.replace(b'</main>', self.controls+b'</main>')
        self.config = BrowserConfig(Path(os.environ['BW_BROWSER_EXECUTABLE']), inspection=PageInspection(
            self.check, hashlib.sha256(self.check.read_bytes()).hexdigest(), 'H06'))

    def test_real_clicks_run_twice_and_leave_source_unchanged(self):
        result = render_snapshot(self.good, self.config)
        self.assertEqual(result.inspection['status'], 'PASS')
        self.assertEqual(result.inspection['actions'], [['click','increment'],['click','increment']])
        self.assertEqual(result.served_sha256, hashlib.sha256(self.good).hexdigest())
        self.assertTrue(result.png.startswith(b'\x89PNG\r\n\x1a\n'))
        self.assertTrue(result.isolation['worker_exited'])
        self.assertEqual(result.isolation['namespace_members_after'], [])
        self.assertEqual(self.check.read_bytes(), self.check_bytes)

    def test_painted_counter_without_a_handler_fails_real_interaction(self):
        payload = self.good.replace(b'Number(n.textContent)+1', b'Number(n.textContent)+0')
        result = render_snapshot(payload, self.config)
        self.assertEqual(result.inspection['status'], 'FAIL')
        self.assertEqual(result.inspection['actions'], [['click','increment']])
        self.assertIn('Actual value: 0', result.inspection['error'])
        self.assertTrue(result.png.startswith(b'\x89PNG'))
        self.assertTrue(result.isolation['worker_exited'])

    def test_wrong_increment_is_not_a_successful_click(self):
        result = render_snapshot(self.good.replace(b'Number(n.textContent)+1', b'Number(n.textContent)+2'), self.config)
        self.assertEqual(result.inspection['status'], 'FAIL')
        self.assertEqual(result.inspection['actions'], [['click','increment']])
        self.assertIn('Actual value: 2', result.inspection['error'])

    def test_click_cannot_hide_corrupted_squares_behind_the_initial_png(self):
        payload = self.good.replace(b'n.textContent=String(Number(n.textContent)+1);',
            b'n.textContent=String(Number(n.textContent)+1);document.querySelector("#a").style.background="red";')
        result = render_snapshot(payload, self.config)
        self.assertEqual(result.inspection['status'], 'FAIL')
        self.assertEqual(result.inspection['actions'], [['click','increment'],['click','increment']])
        self.assertTrue(result.isolation['worker_exited'])

    def test_cli_preserves_actual_action_witness(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'source';source.mkdir();(source/'index.html').write_bytes(self.good)
            output=root/'capture'
            command=[sys.executable,'-B',str(Path(__file__).resolve().parents[1]/'tools/capture_page.py'),
                '--source',str(source),'--expected-sha256',hashlib.sha256(self.good).hexdigest(),
                '--browser',str(self.config.executable),'--output',str(output),
                '--check-module',str(self.check),'--check-sha256',self.config.inspection.sha256,'--check-target','H06']
            process=subprocess.run(command,capture_output=True,timeout=30)
            self.assertEqual(process.returncode,0,process.stderr.decode())
            record=tomllib.loads(process.stdout.decode())
            self.assertEqual(json.loads(record['inspection_actions_json']), [['click','increment'],['click','increment']])
            self.assertEqual(record['inspection_status'],'PASS')
            self.assertEqual(record['image_sha256'],hashlib.sha256((output/'capture.png').read_bytes()).hexdigest())
