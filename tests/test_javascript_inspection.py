"""External JS keeps original DOM, pixels, real handlers and resource identity."""
import hashlib,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from branchwrite.browser_capture import BrowserConfig,PageInspection,render_snapshot
from branchwrite.browser_assets import BrowserAsset
from branchwrite.execution import Executor,Grant
from branchwrite.tool_registry import ToolRegistry
from branchwrite.records import RuntimeLog,Artifact,decode
from branchwrite.kernel import FrameKernel
from branchwrite.interpreter import Interpreter,Value

class JavascriptInspectionTests(unittest.TestCase):
 def setUp(self):
  self.pack=Path(os.environ['BW_BASIC_LOOP_PACK']);self.check=self.pack/'protected/checks.py';self.check_bytes=self.check.read_bytes()
  self.starter=(self.pack/'fixtures/starter/H10/index.html').read_bytes();self.png=(self.pack/'fixtures/starter/H10/assets/sample.png').read_bytes();self.css=(self.pack/'fixtures/starter/H10/style.css').read_bytes()
  self.js=self.starter.split(b'<script>',1)[1].split(b'</script>',1)[0];self.block=b'<script>'+self.js+b'</script>'
  self.good=self.starter.replace(self.block,b'<script src="app.js"></script>')
  self.browser=BrowserConfig(Path(os.environ['BW_BROWSER_EXECUTABLE']))
 def assets(self,js=None):
  return (BrowserAsset('style.css',self.css),BrowserAsset('app.js',self.js if js is None else js),BrowserAsset('assets/sample.png',self.png))
 def config(self):
  return BrowserConfig(self.browser.executable,inspection=PageInspection(self.check,hashlib.sha256(self.check_bytes).hexdigest(),'H10'))
 def test_external_js_preserves_real_counter_literal_greeting_and_pixels(self):
  result=render_snapshot(self.good,self.config(),assets=self.assets())
  self.assertEqual(result.inspection['status'],'PASS')
  self.assertEqual(result.inspection['actions'],[['click','increment'],['click','increment'],['fill','name=Ada'],['click','greet'],['fill','name=<b>Ada</b>'],['click','greet']])
  self.assertEqual({v['path'] for v in result.served_assets},{'style.css','app.js','assets/sample.png'})
  self.assertEqual(self.check.read_bytes(),self.check_bytes)
 def test_whole_static_png_matches_original_inline_script(self):
  original=render_snapshot(self.starter,self.browser,assets=(BrowserAsset('style.css',self.css),BrowserAsset('assets/sample.png',self.png)))
  extracted=render_snapshot(self.good,self.browser,assets=self.assets())
  self.assertEqual(extracted.png,original.png)
 def test_leftover_inline_script_fails_unchanged_checker(self):
  bad=self.good.replace(b'</body>',b'<script>void 0;</script></body>')
  result=render_snapshot(bad,self.config(),assets=self.assets());self.assertEqual(result.inspection['status'],'FAIL')
 def test_leftover_inline_event_attribute_fails_unchanged_checker(self):
  bad=self.good.replace(b'<button id="increment">',b'<button id="increment" onclick="void 0">')
  self.assertNotEqual(bad,self.good)
  result=render_snapshot(bad,self.config(),assets=self.assets());self.assertEqual(result.inspection['status'],'FAIL')
 def test_loaded_but_broken_counter_fails_real_interactions(self):
  js=self.js.replace(b'String(++count)',b'String(count)');self.assertNotEqual(js,self.js)
  result=render_snapshot(self.good,self.config(),assets=self.assets(js));self.assertEqual(result.inspection['status'],'FAIL')
 def make(self,root):
  source=root/'source';(source/'assets').mkdir(parents=True)
  for name,data in [('index.html',self.starter),('style.css',self.css),('assets/sample.png',self.png)]:(source/name).write_bytes(data)
  grant=Grant(('index.html','app.js'),False,read_paths=('index.html','style.css','app.js','assets/sample.png'),create_paths=('app.js',),capture_paths=('index.html',),interact_paths=('index.html',),asset_paths=('style.css','app.js','assets/sample.png'))
  e=Executor.create(source,root/'world',browser=self.browser);return e,ToolRegistry(e,grant),grant
 def proposals(self):
  return dict(read=dict(tool='read_file',arguments=dict(path='index.html')),create=dict(tool='create_file',arguments=dict(path='app.js',content=self.js.decode())),edit=dict(tool='replace',arguments=dict(path='index.html',before=self.block.decode(),after='<script src="app.js"></script>')),read_js=dict(tool='read_file',arguments=dict(path='app.js')),interact=dict(tool='interact_page',arguments=dict(path='index.html',actions=[dict(kind='click',target='increment',value='')])),finish=dict(tool='finish',arguments=dict(answer='observed external script')))
 def program(self):
  steps=[('r','read'),('c','create'),('e','edit'),('r2','read'),('rj','read_js'),('i','interact'),('f','finish')]
  lines=['FLOW javascript']
  for label,binding in steps:lines+=['PLAN '+label+' from='+binding+' against=world -> p','ACT '+label+' plan=p -> outcome']
  return '\n'.join(lines+['VERIFY v input=outcome contract=interactive-page-inspection-and-finish -> verified','END',''])
 def spec(self):
  return dict(schema=1,interactive_captures=[dict(path='index.html',width=640,height=480)],inspection=dict(path=str(self.check),sha256=hashlib.sha256(self.check_bytes).hexdigest(),target='H10'))
 def test_real_cli_create_edit_inspect_and_offline_reopen(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);e,r,g=self.make(root)
   cfg=dict(schema=1,source=str(e.source),run_id='h10-js',grant={k:list(getattr(g,k)) for k in ['edit_paths','create_paths','read_paths','capture_paths','interact_paths','asset_paths']},browser=dict(executable=str(self.browser.executable),width=640,height=480,timeout=15),profiles={},verification=self.spec(),bindings={k:dict(type='ToolProposal',value=json.dumps(v)) for k,v in self.proposals().items()})
   cfg['grant']['allow_tests']=False;config=root/'host.json';config.write_text(json.dumps(cfg));program=root/'job.bw';program.write_text(self.program());state=root/'cli-run'
   cmd=[sys.executable,'-B','-m','branchwrite','run',str(program),'--config',str(config),'--state',str(state)]
   first=subprocess.run(cmd,capture_output=True,text=True,timeout=30);self.assertEqual(first.returncode,0,first.stderr);self.assertTrue(json.loads(first.stdout)['verified'])
   self.assertEqual((state/'world/workspace/app.js').read_bytes(),self.js);self.assertEqual((state/'world/workspace/index.html').read_bytes(),self.good)
   self.assertEqual((state/'world/workspace/style.css').read_bytes(),self.css);self.assertFalse((e.source/'app.js').exists());self.assertEqual((e.source/'index.html').read_bytes(),self.starter)
   with RuntimeLog(state/'ledger') as log:self.assertEqual(log.read_artifact(Artifact(hashlib.sha256(self.js).hexdigest(),len(self.js))),self.js)
   again=subprocess.run(cmd,capture_output=True,text=True,timeout=30);self.assertEqual(again.returncode,0,again.stderr);self.assertEqual(first.stdout,again.stdout)
 def test_changed_js_after_capture_invalidates_completion_even_if_same_pixels(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);e,r,g=self.make(root)
   with RuntimeLog(root/'ledger') as log:
    k=FrameKernel(log);runtime=Interpreter(k,r,verification=self.spec());runtime.start(self.program(),{k:Value('ToolProposal',json.dumps(v)) for k,v in self.proposals().items()})
    captured=False
    for _ in range(100):
     runtime.step()
     if any(f['state']=='Closed' and f['contract']==('ToolOutcome','record') and decode(log.read_artifact(Artifact(*f['result'])))[2]['disposition']=='captured' for f in k.frames()):captured=True;break
    self.assertTrue(captured);(e.workspace/'app.js').write_bytes(self.js+b'\n/* same behavior,different bytes */')
    self.assertFalse(runtime.run().value['verified'])
if __name__=='__main__':unittest.main()
