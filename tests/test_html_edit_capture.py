"""Real isolated browser checks for old/new H04/H05 source identities."""
import hashlib
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from branchwrite.execution import Executor, Grant
from validation.run_basic_loop_edit import capture_revision
from validation.run_basic_loop_html import checked_pack


class HtmlEditCaptureTests(unittest.TestCase):
    def check_target(self, target, before, after):
        pack, inventory = checked_pack(Path(os.environ['BW_BASIC_LOOP_PACK']))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            executor = Executor.create(pack/('fixtures/starter/'+target), root/'tool')
            args = SimpleNamespace(target=target, browser=Path(os.environ['BW_BROWSER_EXECUTABLE']))
            repo = Path(__file__).resolve().parents[1]
            original = (executor.workspace/'index.html').read_bytes()
            initial, image_before = capture_revision(repo, executor, root, 'before', args, pack, inventory)
            self.assertEqual(initial['capture']['inspection_status'], 'FAIL')
            self.assertEqual(initial['cli_exit'], 1)
            executor.replace('edit', Grant(('index.html',), False), 'index.html',
                             hashlib.sha256(original).hexdigest(), before, after)
            result, image_after = capture_revision(repo, executor, root, 'after', args, pack, inventory)
            self.assertEqual(result['capture']['inspection_status'], 'PASS')
            self.assertEqual(result['cli_exit'], 0)
            self.assertTrue(initial['cli_absent'] and result['cli_absent'])
            self.assertNotEqual(image_before, image_after)
            self.assertNotEqual(initial['capture']['source_sha256'], result['capture']['source_sha256'])
            self.assertEqual((pack/('fixtures/starter/'+target+'/index.html')).read_bytes(), original)

    def test_h04_green_revision_is_a_new_render_not_the_blue_capture(self):
        self.check_target('H04', b'#2463eb', b'#16a34a')

    def test_h05_horizontal_revision_is_a_new_render_not_the_stacked_capture(self):
        self.check_target('H05', b'flex-direction: column', b'flex-direction: row')
