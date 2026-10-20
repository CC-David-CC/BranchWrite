"""Screenshot caret hiding must not leave inline attributes on candidate input."""
import hashlib,os,tempfile,unittest
from pathlib import Path
from branchwrite.browser_capture import BrowserConfig,PageAction,PageInspection,render_snapshot
class ScreenshotDOMTests(unittest.TestCase):
 def test_capture_preserves_absent_empty_and_explicit_inline_style_attributes(self):
  with tempfile.TemporaryDirectory() as t:
   path=Path(t)/'checks.py'
   path.write_text('def structure(page,target,expect):\n assert page.locator("#bare").get_attribute("style") is None\n assert page.locator("#empty").get_attribute("style")==""\n assert page.locator("#red").get_attribute("style")=="color: red"\n assert page.locator("style").count()==0\ndef pixels(path,page,target,variant):\n pass\n')
   config=BrowserConfig(Path(os.environ['BW_BROWSER_EXECUTABLE']),inspection=PageInspection(path,hashlib.sha256(path.read_bytes()).hexdigest(),'H03'))
   result=render_snapshot(b'<input id="bare"><input id="empty" style=""><input id="red" style="color: red">',config)
   self.assertEqual(result.inspection['status'],'PASS')
   self.assertTrue(result.isolation['worker_exited'])
 def test_focused_input_caret_remains_deterministic_without_inline_residue(self):
  config=BrowserConfig(Path(os.environ['BW_BROWSER_EXECUTABLE']),actions=(PageAction('fill','name','repeatable text'),))
  first=render_snapshot(b'<input id="name">',config);second=render_snapshot(b'<input id="name">',config)
  self.assertEqual(first.png,second.png)
  self.assertEqual(first.actions,second.actions)
if __name__=='__main__':unittest.main()
