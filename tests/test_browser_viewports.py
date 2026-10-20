"""Host-granted viewport selection uses actual pixels and unchanged worlds."""
from pathlib import Path
import dataclasses,hashlib,io,os,tempfile,unittest
from unittest.mock import patch
from PIL import Image
from branchwrite.browser_capture import BrowserConfig
from branchwrite.execution import Executor,Grant,ToolRejected,BrowserExecutionError
MENU=(('desktop',640,480),('phone',360,640))
PAGE=b'<style>body{margin:0}div{width:100vw;height:80px;background:blue}</style><div></div><button id="inc">Add</button><output id="count">0</output><script>let n=0;document.querySelector("#inc").onclick=()=>document.querySelector("#count").textContent=String(++n);</script>'
class BrowserViewportTests(unittest.TestCase):
 def browser(self,menu=MENU):return BrowserConfig(Path(os.environ['BW_BROWSER_EXECUTABLE']),viewports=menu)
 def make(self,root,page=PAGE):
  source=root/'source';source.mkdir();(source/'index.html').write_bytes(page)
  e=Executor.create(source,root/'world',browser=self.browser())
  g=Grant((),False,read_paths=('index.html',),capture_paths=('index.html',),interact_paths=('index.html',))
  return e,g
 def size(self,result):
  with Image.open(io.BytesIO(result.image.read_bytes())) as im:return im.size
 def test_menu_is_immutable_canonical_and_geometry_is_bounded(self):
  a=self.browser(tuple(reversed(MENU)));self.assertEqual(a.viewports,MENU)
  for menu in [None,[],(('bad name',640,480),),(('phone',360,640),),(('desktop',True,480),),(('desktop',2048,2048),),MENU+(('other',360,640),),MENU+(('phone',800,600),),tuple(('p'+str(i),640-i,480) for i in range(9))]:
   with self.subTest(menu=menu),self.assertRaises(ValueError):self.browser(menu)
 def test_selection_does_not_mutate_default_or_grant_arbitrary_geometry(self):
  browser=self.browser();phone=browser.for_viewport('phone')
  self.assertEqual((phone.width,phone.height),(360,640));self.assertEqual((browser.width,browser.height),(640,480))
  self.assertEqual(browser.name_for_size(360,640),'phone');self.assertEqual(browser.at_size(360,640),phone)
  with self.assertRaises(ValueError):browser.for_viewport('unknown')
  with self.assertRaises(ValueError):browser.at_size(361,640)
 def test_real_phone_and_desktop_captures_bind_actual_png_geometry(self):
  with tempfile.TemporaryDirectory() as t:
   e,g=self.make(Path(t));sha=hashlib.sha256(PAGE).hexdigest()
   phone=e.capture_page('phone',g,'index.html',sha,viewport='phone')
   desktop=e.capture_page('desktop',g,'index.html',sha,viewport='desktop')
   self.assertEqual((phone.viewport,phone.viewport_name,self.size(phone)),((360,640),'phone',(360,640)))
   self.assertEqual((desktop.viewport,desktop.viewport_name,self.size(desktop)),((640,480),'desktop',(640,480)))
   self.assertNotEqual(phone.image.sha256,desktop.image.sha256);self.assertEqual((e.source/'index.html').read_bytes(),PAGE)
   self.assertTrue(phone.isolation['worker_exited']);self.assertTrue(desktop.isolation['worker_exited'])
 def test_real_phone_interaction_preserves_action_and_source_receipts(self):
  with tempfile.TemporaryDirectory() as t:
   e,g=self.make(Path(t))
   out=e.interact_page('phone-click',g,'index.html',hashlib.sha256(PAGE).hexdigest(),[dict(kind='click',target='inc',value='')],viewport='phone')
   self.assertIn('1',out.text);self.assertEqual(out.viewport_name,'phone');self.assertEqual(self.size(out),(360,640))
   self.assertEqual(out.actions,({'kind':'click','target':'inc','value':''},));self.assertEqual(out.served_sha256,hashlib.sha256(PAGE).hexdigest())
 def test_ungranted_viewport_rejects_before_browser_and_artifact_creation(self):
  with tempfile.TemporaryDirectory() as t:
   e,g=self.make(Path(t))
   with patch('branchwrite.browser_capture.render_snapshot') as render:
    with self.assertRaises(ToolRejected):e.capture_page('unknown',g,'index.html',hashlib.sha256(PAGE).hexdigest(),viewport='unknown')
   render.assert_not_called();self.assertEqual(list(e.artifacts.iterdir()),[])
 def test_phone_error_stays_in_memory_until_exact_viewport_publication(self):
  page=PAGE+b'<script>document.querySelector("#inc").onclick=()=>{throw new Error("phone failure")}</script>'
  with tempfile.TemporaryDirectory() as t:
   e,g=self.make(Path(t),page)
   with self.assertRaises(BrowserExecutionError) as raised:e.interact_page('error',g,'index.html',hashlib.sha256(page).hexdigest(),[dict(kind='click',target='inc',value='')],viewport='phone')
 def test_phone_error_cannot_be_relabelled_as_desktop(self):
  page=PAGE+b'<script>document.querySelector("#inc").onclick=()=>{throw new Error("phone failure")}</script>'
  with tempfile.TemporaryDirectory() as t:
   e,g=self.make(Path(t),page)
   with self.assertRaises(BrowserExecutionError) as raised:e.interact_page('error',g,'index.html',hashlib.sha256(page).hexdigest(),[dict(kind='click',target='inc',value='')],viewport='phone')
   self.assertEqual(list(e.artifacts.iterdir()),[])
   with self.assertRaisesRegex(ValueError,'viewport'):e._publish_browser_error(raised.exception,'error','index.html',viewport='desktop')
   self.assertEqual(list(e.artifacts.iterdir()),[])
   out=e._publish_browser_error(raised.exception,'error','index.html',viewport='phone')
   self.assertEqual(out.viewport_name,'phone');self.assertEqual(self.size(out),(360,640));self.assertTrue(out.runtime_errors)
if __name__=='__main__':unittest.main()
