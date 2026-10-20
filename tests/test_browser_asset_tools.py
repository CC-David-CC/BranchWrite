"""Host asset grants and source/resource binding; scripted tools, real browser."""
import io,hashlib,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from branchwrite.browser_capture import BrowserConfig,render_snapshot
from branchwrite.browser_assets import BrowserAsset
from branchwrite.execution import Executor,Grant,ToolRejected
from branchwrite.tool_registry import ToolRegistry,FileObservation
from branchwrite.records import RuntimeLog,Artifact,decode

class AssetToolTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
  self.source=self.root/'source';(self.source/'pages').mkdir(parents=True);(self.source/'assets').mkdir()
  self.html=b'<body style="margin:0"><img src="../assets/marker.png"><button id="go">Go</button><p id="state">0</p><script>go.onclick=()=>state.textContent="clicked"</script></body>'
  self.png=self.image((11,173,91));(self.source/'pages/start.html').write_bytes(self.html);(self.source/'assets/marker.png').write_bytes(self.png)
  self.browser=BrowserConfig(Path(os.environ['BW_BROWSER_EXECUTABLE']))
  self.executor=Executor.create(self.source,self.root/'world',browser=self.browser)
 def image(self,color):
  b=io.BytesIO();Image.new('RGB',(16,12),color).save(b,format='PNG');return b.getvalue()
 def grant(self,assets=('assets/marker.png',)):
  return Grant((),False,read_paths=('pages/start.html','assets/marker.png'),capture_paths=('pages/start.html',),interact_paths=('pages/start.html',),asset_paths=assets)
 def registry(self):return ToolRegistry(self.executor,self.grant())
 def proposal(self,tool='capture_page'):
  args=dict(path='pages/start.html')
  if tool=='interact_page':args['actions']=[dict(kind='click',target='go',value='')]
  return json.dumps(dict(tool=tool,arguments=args))
 def plan(self,r,tool='capture_page'):
  return r.freeze(self.proposal(tool),observations=(FileObservation(r.world,'pages/start.html',hashlib.sha256(self.html).hexdigest()),))
 def test_nested_document_preserves_relative_resource_url(self):
  result=render_snapshot(self.html,self.browser,document_path='pages/start.html',assets=(BrowserAsset('assets/marker.png',self.png),))
  self.assertTrue(result.url.endswith('/pages/start.html'))
  self.assertEqual(result.document_path,'pages/start.html')
  self.assertEqual(result.served_assets[0]['sha256'],hashlib.sha256(self.png).hexdigest())
  with Image.open(io.BytesIO(result.png)) as im:self.assertEqual(im.getpixel((3,3))[:3],(11,173,91))
 def test_document_path_cannot_alias_asset(self):
  with self.assertRaises(ValueError):
   render_snapshot(b'<p>x</p>',self.browser,document_path='a.js',assets=(BrowserAsset('a.js',b'x'),))
 def test_asset_grant_requires_explicit_read_permission(self):
  with self.assertRaisesRegex(ToolRejected,'read'):Grant((),False,asset_paths=('assets/marker.png',))
 def test_asset_allowlist_is_bounded_and_canonical(self):
  for names in [('assets/../marker.png',),('assets/marker.png',)*2,tuple(f'{i}.png' for i in range(65))]:
   with self.subTest(count=len(names)),self.assertRaises(ToolRejected):
    Grant((),False,asset_paths=names,read_paths=names)
 def test_read_permission_alone_does_not_serve_resources(self):
  r=ToolRegistry(self.executor,self.grant(assets=()))
  plan=self.plan(r)
  with self.assertRaises(Exception):r.execute(plan,'no-resource-permission')
 def test_plan_contains_actual_asset_preimage(self):
  r=self.registry();plan=self.plan(r);row=decode(plan.data)
  self.assertEqual({x[0]:x[1] for x in row[5]},dict([('pages/start.html',hashlib.sha256(self.html).hexdigest()),('assets/marker.png',hashlib.sha256(self.png).hexdigest())]))
 def test_asset_change_after_plan_rejects_before_browser(self):
  r=self.registry();plan=self.plan(r);(self.executor.workspace/'assets/marker.png').write_bytes(self.image((200,0,0)))
  with patch('branchwrite.browser_capture.render_snapshot') as render:
   with self.assertRaisesRegex(ToolRejected,'stale'):r.execute(plan,'stale-resource')
  render.assert_not_called()
 def test_asset_symlink_after_admission_rejects_before_browser(self):
  r=self.registry();plan=self.plan(r);path=self.executor.workspace/'assets/marker.png';path.unlink();path.symlink_to(self.source/'assets/marker.png')
  with patch('branchwrite.browser_capture.render_snapshot') as render:
   with self.assertRaises(ToolRejected):r.execute(plan,'link-resource')
  render.assert_not_called()
 def test_actual_tool_receipt_roots_exact_asset_bytes_in_existing_ledger(self):
  r=self.registry();out=r.execute(self.plan(r),'captured')
  with RuntimeLog(self.root/'ledger') as log:
   value,refs=out.publish(log)
   manifest=value['details']['asset_manifest']
   self.assertEqual(manifest,[BrowserAsset('assets/marker.png',self.png).manifest])
   self.assertEqual(value['details']['document_path'],'pages/start.html')
   ref=Artifact(hashlib.sha256(self.png).hexdigest(),len(self.png))
   self.assertIn(ref,refs);self.assertEqual(log.read_artifact(ref),self.png)
   self.assertTrue(value['image'])
 def test_allowlist_contributes_to_tool_identity(self):
  r=self.registry();other=ToolRegistry(self.executor,self.grant(assets=()))
  self.assertNotEqual(r.identity,other.identity)
 def test_direct_executor_requires_granted_resources(self):
  g=self.grant()
  out=self.executor.capture_page('direct',g,'pages/start.html',hashlib.sha256(self.html).hexdigest())
  self.assertEqual(out.asset_manifest,(BrowserAsset('assets/marker.png',self.png).manifest,))
  self.assertEqual(out.assets[0].read_bytes(),self.png)
 def test_cli_admits_only_explicit_readable_asset_grants(self):
  from branchwrite.run_cli import _config
  cfg=dict(schema=1,source=str(self.source),run_id='assets',grant=dict(edit_paths=[],create_paths=[],read_paths=['pages/start.html','assets/marker.png'],capture_paths=['pages/start.html'],asset_paths=['assets/marker.png'],allow_tests=False),browser=dict(executable=str(self.browser.executable),width=640,height=480,timeout=15),bindings={},profiles={})
  self.assertEqual(_config(json.dumps(cfg))['grant']['asset_paths'],['assets/marker.png'])
  cfg['grant']['read_paths']=['pages/start.html']
  with self.assertRaisesRegex(ValueError,'read'):_config(json.dumps(cfg))

if __name__=='__main__':unittest.main()
