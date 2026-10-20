"""Protected DOM checks run on the existing real capture, not a second browser."""
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from branchwrite.browser_capture import BrowserConfig, render_snapshot

PAGE = (b'<!doctype html><style>body{background:white}.square{width:80px;height:80px;'
        b'background:#2463eb}</style><h1>Loop Lab</h1><div id="row"><div id="a" '
        b'class="square"></div></div>')


class HtmlInspectionTests(unittest.TestCase):
    def inspector(self, digest=None):
        from branchwrite.browser_capture import PageInspection
        path = Path(os.environ['BW_BASIC_LOOP_PACK']) / 'protected/checks.py'
        return PageInspection(path, digest or hashlib.sha256(path.read_bytes()).hexdigest(), 'H03')

    def config(self, inspection):
        return BrowserConfig(Path(os.environ['BW_BROWSER_EXECUTABLE']), inspection=inspection)

    def test_same_real_capture_passes_supplied_dom_and_pixel_assertions(self):
        result = render_snapshot(PAGE, self.config(self.inspector()))
        self.assertEqual(result.inspection['status'], 'PASS')
        self.assertEqual(result.inspection['target'], 'H03')
        self.assertEqual(result.inspection['inspector_sha256'], self.inspector().sha256)
        self.assertTrue(result.isolation['worker_exited'])

    def test_wrong_heading_retains_actual_png_and_is_a_task_failure(self):
        result = render_snapshot(PAGE.replace(b'Loop Lab', b'Wrong heading'), self.config(self.inspector()))
        self.assertEqual(result.inspection['status'], 'FAIL')
        self.assertTrue(result.png.startswith(b'\x89PNG\r\n\x1a\n'))
        self.assertTrue(result.inspection['error'])
        self.assertTrue(result.isolation['worker_exited'])

    def test_changed_inspector_rejects_before_starting_a_worker(self):
        config = self.config(self.inspector('0' * 64))
        with patch('subprocess.Popen') as start:
            with self.assertRaisesRegex(ValueError, 'inspection'):
                render_snapshot(PAGE, config)
        start.assert_not_called()


if __name__ == '__main__':
    unittest.main()
