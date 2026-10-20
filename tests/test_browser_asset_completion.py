"""Completion must bind all resource bytes, not HTML or pixels alone."""
import hashlib,io,json,os,subprocess,sys,tempfile,unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from PIL import Image,PngImagePlugin
from branchwrite.browser_capture import BrowserConfig
from branchwrite.execution import Executor,Grant
from branchwrite.tool_registry import ToolRegistry
from branchwrite.records import RuntimeLog,Artifact,decode
from branchwrite.kernel import FrameKernel
from branchwrite.interpreter import Interpreter,Value

PAGE=b'<body style="margin:0"><img id="icon" src="../assets/marker.png"><button id="go">Go</button><output id="count">0</output><script>go.onclick=()=>count.textContent=String(Number(count.textContent)+1)</script></body>'
class AssetCompletionTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
  self.source=self.root/'source';(self.source/'pages').mkdir(parents=True);(self.source/'assets').mkdir()
  b=io.BytesIO();Image.new('RGB',(16,12),(11,173,91)).save(b,format='PNG');self.png=b.getvalue()
  (self.source/'pages/start.html').write_bytes(PAGE);(self.source/'assets/marker.png').write_bytes(self.png)
  self.browser=BrowserConfig(Path(os.environ['BW_BROWSER_EXECUTABLE']))
  self.executor=Executor.create(self.source,self.root/'world',browser=self.browser)
  self.grant=Grant((),False,read_paths=('pages/start.html','assets/marker.png'),capture_paths=('pages/start.html',),interact_paths=('pages/start.html',),asset_paths=('assets/marker.png',))
  self.registry=ToolRegistry(self.executor,self.grant)
  self.log=RuntimeLog(self.root/'ledger');self.addCleanup(self.close);self.kernel=FrameKernel(self.log)
  self.spec=dict(schema=1,files=[dict(path='pages/start.html',sha256=hashlib.sha256(PAGE).hexdigest())],captures=[dict(path='pages/start.html',width=640,height=480)])
 def close(self):
  if not self.log._closed:self.log.close()
 def bindings(self):
  return {name:Value('ToolProposal',json.dumps(dict(tool=tool,arguments=args))) for name,tool,args in [('read','read_file',dict(path='pages/start.html')),('capture','capture_page',dict(path='pages/start.html')),('click','interact_page',dict(path='pages/start.html',actions=[dict(kind='click',target='go',value='')])),('finish','finish',dict(answer='actually inspected'))]}
 def program(self,interactive=False):
  tool='click' if interactive else 'capture';contract='interactive-page-inspection-and-finish' if interactive else 'page-capture-and-finish'
  return 'FLOW assets\nPLAN r from=read against=world -> plan\nACT r plan=plan\nPLAN c from='+tool+' against=world -> plan\nACT c plan=plan\nPLAN f from=finish against=world -> plan\nACT f plan=plan -> outcome\nVERIFY v input=outcome contract='+contract+' -> verified\nEND\n'
 def runtime(self,spec=None):
  r=Interpreter(self.kernel,self.registry,verification=self.spec if spec is None else spec);return r
 def until_capture(self,r):
  for _ in range(100):
   r.step()
   if any(f['state']=='Closed' and f['contract']==('ToolOutcome','record') and decode(self.log.read_artifact(Artifact(*f['result'])))[2]['disposition']=='captured' for f in self.kernel.frames()):return
  self.fail('actual capture never completed')
 def alternate_png(self):
  image=Image.open(io.BytesIO(self.png));b=io.BytesIO();meta=PngImagePlugin.PngInfo();meta.add_text('variant','different bytes, same pixels');image.save(b,format='PNG',pnginfo=meta);return b.getvalue()
 def test_static_completion_records_current_bundle(self):
  r=self.runtime();r.start(self.program(),self.bindings());result=r.run()
  self.assertTrue(result.value['verified'])
  capture=result.value['bindings']['verified'][1]['captures'][0]
  self.assertEqual(capture['asset_manifest'][0]['sha256'],hashlib.sha256(self.png).hexdigest())
  self.assertEqual(capture['document_path'],'pages/start.html')
 def test_changed_asset_same_html_and_pixels_invalidates_capture(self):
  r=self.runtime();r.start(self.program(),self.bindings());self.until_capture(r)
  changed=self.alternate_png();self.assertNotEqual(changed,self.png)
  self.assertEqual(Image.open(io.BytesIO(changed)).tobytes(),Image.open(io.BytesIO(self.png)).tobytes())
  (self.executor.workspace/'assets/marker.png').write_bytes(changed)
  self.assertFalse(r.run().value['verified'])
 def test_missing_asset_invalidates_capture(self):
  r=self.runtime();r.start(self.program(),self.bindings());self.until_capture(r)
  (self.executor.workspace/'assets/marker.png').unlink()
  self.assertFalse(r.run().value['verified'])
 def test_forged_asset_receipt_is_not_accepted(self):
  real=self.executor.capture_page
  def wrong(*a,**k):return replace(real(*a,**k),asset_manifest=())
  r=self.runtime();r.start(self.program(),self.bindings())
  with patch.object(self.executor,'capture_page',side_effect=wrong):
   self.assertFalse(r.run().value['verified'])
 def interactive_spec(self):
  checker=self.root/'checks.py'
  checker.write_text('def structure(page,target,expect):\n assert page.locator("#icon").evaluate("e=>e.naturalWidth")==16\ndef pixels(path,page,target,variant):\n from PIL import Image\n with Image.open(path) as im: assert im.convert("RGB").getpixel((3,3))==(11,173,91)\ndef interact(page,target,expect,actions):\n page.locator("#go").click()\n actions.append(("click","go"))\n expect(page.locator("#count")).to_have_text("1")\n')
  return dict(schema=1,interactive_captures=[dict(path='pages/start.html',width=640,height=480)],inspection=dict(path=str(checker),sha256=hashlib.sha256(checker.read_bytes()).hexdigest(),target='H06'))
 def test_interaction_and_independent_checker_use_the_same_bundle(self):
  r=self.runtime(self.interactive_spec());r.start(self.program(True),self.bindings());result=r.run()
  self.assertTrue(result.value['verified'])
  v=result.value['bindings']['verified'][1]
  self.assertTrue(v['inspections'][0]['same_capture'])
  self.assertEqual(v['inspections'][0]['asset_manifest'][0]['sha256'],hashlib.sha256(self.png).hexdigest())
  self.assertEqual(v['inspections'][0]['checker']['status'],'PASS')
 def test_asset_changed_after_interaction_blocks_checker(self):
  from branchwrite import verification
  actual=verification.replay_interaction
  def changed(*a,**kw):
   rendered=actual(*a,**kw);(self.executor.workspace/'assets/marker.png').write_bytes(self.alternate_png());return rendered
  r=self.runtime(self.interactive_spec());r.start(self.program(True),self.bindings())
  with patch.object(verification,'replay_interaction',side_effect=changed),patch.object(verification,'inspect_captured_page',side_effect=AssertionError('stale bundle must not reach checker')):
   self.assertFalse(r.run().value['verified'])
 def test_real_cli_assets_and_completed_reopen_without_browser_work(self):
  self.close()
  cfg=dict(schema=1,source=str(self.source),run_id='asset-cli',grant=dict(edit_paths=[],create_paths=[],read_paths=['pages/start.html','assets/marker.png'],capture_paths=['pages/start.html'],asset_paths=['assets/marker.png'],allow_tests=False),browser=dict(executable=str(self.browser.executable),width=640,height=480,timeout=15),profiles={},verification=self.spec,bindings={k:dict(type=v.type,value=v.data) for k,v in self.bindings().items()})
  f=self.root/'host.json';f.write_text(json.dumps(cfg));program=self.root/'job.bw';program.write_text(self.program());state=self.root/'cli-run'
  cmd=[sys.executable,'-B','-m','branchwrite','run',str(program),'--config',str(f),'--state',str(state)]
  first=subprocess.run(cmd,capture_output=True,text=True,timeout=30);self.assertEqual(first.returncode,0,first.stderr);self.assertTrue(json.loads(first.stdout)['verified'])
  with RuntimeLog(state/'ledger') as log:self.assertEqual(log.read_artifact(Artifact(hashlib.sha256(self.png).hexdigest(),len(self.png))),self.png)
  again=subprocess.run(cmd,capture_output=True,text=True,timeout=30);self.assertEqual(again.returncode,0,again.stderr);self.assertEqual(first.stdout,again.stdout)

if __name__=='__main__':unittest.main()
