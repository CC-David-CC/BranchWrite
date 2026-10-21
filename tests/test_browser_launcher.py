"""Launcher admission checks; real Chromium remains a separate integration test."""
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from branchwrite.browser_isolation import _validate_browser_launcher

class BrowserLauncherTests(unittest.TestCase):
    def test_user_owned_copy_cannot_become_a_trusted_launcher(self):
        self.assertNotEqual(os.getuid(),0, 'run launcher checks as the client user')
        with tempfile.TemporaryDirectory() as directory:
            copy=Path(directory)/'bwrap'
            shutil.copyfile('/usr/bin/bwrap',copy)
            copy.chmod(0o755)
            with self.assertRaisesRegex(ValueError,'root-owned'):
                _validate_browser_launcher(copy)
    def test_symlink_is_rejected_before_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            link=Path(directory)/'bwrap'
            link.symlink_to('/usr/bin/bwrap')
            with self.assertRaisesRegex(ValueError,'real file'):
                _validate_browser_launcher(link)
