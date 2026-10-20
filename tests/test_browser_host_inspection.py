"""Actual isolated Chromium checks for a host-owned task observer; no model/GPU."""
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from branchwrite.browser_capture import BrowserConfig,PageInspection,render_snapshot

CHECKER = """def structure(page,target,expect):
    expect(page.locator('#name')).to_have_css('font-weight','700')
    expect(page.locator('#verb')).to_have_css('font-style','italic')
    expect(page.locator('#verb')).to_have_css('text-decoration-line','underline')
def interact(page,target,expect,actions):
    page.locator('#hello').click()
    expect(page.locator('#message')).to_have_text('Hello, David!')
    actions.append(['click','hello'])
def pixels(path,page,target,phase):
    from PIL import Image
    with Image.open(path) as image:
        assert image.format=='PNG' and image.size==(640,480)
"""
PAGE = b"""<!doctype html><meta charset="utf-8"><strong id="name">Rex</strong>
<em id="verb" style="text-decoration:underline">runs</em>
<button id="hello" onclick="document.getElementById('message').textContent='Hello, David!'">Say hello</button><p id="message"></p>"""

class HostInspectionTests(unittest.TestCase):
    def inspect(self,payload,checker=CHECKER):
        with tempfile.TemporaryDirectory(prefix='bw-host-inspection-') as temp:
            source=Path(temp)/'checks.py';source.write_text(checker)
            inspection=PageInspection(source,hashlib.sha256(source.read_bytes()).hexdigest(),'custom')
            config=BrowserConfig(Path(os.environ['BW_BROWSER_EXECUTABLE']),inspection=inspection)
            return render_snapshot(payload,config)
    def test_real_computed_style_and_interaction_are_checked_in_the_sandbox(self):
        result=self.inspect(PAGE)
        self.assertEqual(result.inspection['status'],'PASS',result.inspection)
        self.assertEqual(result.inspection['actions'],[['click','hello']])
        self.assertEqual(result.served_sha256,hashlib.sha256(PAGE).hexdigest())
        self.assertTrue(result.isolation['chromium_sandbox'])
        self.assertTrue(result.isolation['worker_exited'])
        self.assertEqual(result.isolation['namespace_members_after'],[])
    def test_missing_underline_is_a_failed_inspection(self):
        result=self.inspect(PAGE.replace(b'text-decoration:underline',b'text-decoration:none'))
        self.assertEqual(result.inspection['status'],'FAIL',result.inspection)
        self.assertEqual(result.inspection['actions'],[])
    def test_italic_alone_does_not_pass_bold_name_requirement(self):
        result=self.inspect(PAGE.replace(b'<strong id="name">Rex</strong>',b'<em id="name">Rex</em>'))
        self.assertEqual(result.inspection['status'],'FAIL',result.inspection)

    def test_custom_checks_cannot_publish_an_invalid_action_receipt(self):
        invalid=CHECKER.replace("actions.append(['click','hello'])", "actions.append(dict(action='click',target='hello'))")
        with self.assertRaisesRegex(ValueError,'inspection result'):
            self.inspect(PAGE,invalid)
