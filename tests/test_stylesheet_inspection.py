"""External stylesheet ownership and unchanged protected H09 checks."""
import hashlib,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from branchwrite.browser_capture import BrowserConfig,PageInspection,render_snapshot
from branchwrite.browser_assets import BrowserAsset
from branchwrite.execution import Executor,Grant,ToolRejected
from branchwrite.tool_registry import ToolRegistry,FileObservation
from branchwrite.records import RuntimeLog,Artifact,decode
from branchwrite.kernel import FrameKernel
from branchwrite.interpreter import Interpreter,Value

class StylesheetInspectionTests(unittest.TestCase):
 def setUp(self):
  self.pack=Path(os.environ['BW_BASIC_LOOP_PACK']);self.check=self.pack/'protected/checks.py';self.check_bytes=self.check.read_bytes()
  self.starter=(self.pack/'fixtures/starter/H09/index.html').read_bytes();self.png=(self.pack/'fixtures/starter/H09/assets/sample.png').read_bytes()
  self.css=self.starter.split(b'<style>',1)[1].split(b'</style>',1)[0]
  self.block=b'<style>'+self.css+b'</style>'
  self.good=self.starter.replace(self.block,b'<link rel="stylesheet" href="style.css">')
  self.browser=BrowserConfig(Path(os.environ['BW_BROWSER_EXECUTABLE']))
 def assets(self,css=None):
  return (BrowserAsset('style.css',self.css if css is None else css),BrowserAsset('assets/sample.png',self.png))
 def config(self):
  return BrowserConfig(self.browser.executable,inspection=PageInspection(self.check,hashlib.sha256(self.check_bytes).hexdigest(),'H09'))
 def test_real_external_css_preserves_pixels_image_and_controls(self):
  result=render_snapshot(self.good,self.config(),assets=self.assets())
  self.assertEqual(result.inspection['status'],'PASS')
  self.assertEqual(result.inspection['actions'],[['click','increment'],['click','increment'],['fill','name=Ada'],['click','greet'],['fill','name=<b>Ada</b>'],['click','greet']])
  self.assertEqual(result.asset_manifest,tuple(a.manifest for a in self.assets()))
  self.assertEqual({r['path'] for r in result.served_assets},{'style.css','assets/sample.png'})
  self.assertEqual(self.check.read_bytes(),self.check_bytes)
 def test_static_appearance_matches_original_entire_png(self):
  original=render_snapshot(self.starter,self.browser,assets=(BrowserAsset('assets/sample.png',self.png),))
  extracted=render_snapshot(self.good,self.browser,assets=self.assets())
  self.assertEqual(extracted.png,original.png)
 def test_inline_style_block_is_not_excused_by_a_valid_link(self):
  bad=self.good.replace(b'</head>',self.block+b'</head>')
  result=render_snapshot(bad,self.config(),assets=self.assets())
  self.assertEqual(result.inspection['status'],'FAIL')
 def test_intentional_empty_inline_attribute_is_still_rejected(self):
  bad=self.good.replace(b'<input id="name">',b'<input id="name" style="">')
  self.assertNotEqual(bad,self.good)
  result=render_snapshot(bad,self.config(),assets=self.assets())
  self.assertEqual(result.inspection['status'],'FAIL')
 def test_wrong_stylesheet_pixels_fail_original_assertions(self):
  css=self.css.replace(b'#2463eb',b'#111111')
  result=render_snapshot(self.good,self.config(),assets=self.assets(css))
  self.assertEqual(result.inspection['status'],'FAIL')
 def make(self,root):
  source=root/'source';(source/'assets').mkdir(parents=True);(source/'index.html').write_bytes(self.starter);(source/'assets/sample.png').write_bytes(self.png)
  grant=Grant(('index.html',),False,read_paths=('index.html','style.css','assets/sample.png'),create_paths=('style.css',),capture_paths=('index.html',),interact_paths=('index.html',),asset_paths=('style.css','assets/sample.png'))
  e=Executor.create(source,root/'world',browser=self.browser);return e,ToolRegistry(e,grant),grant
 def test_capture_before_stylesheet_creation_rejects_purely(self):
  with tempfile.TemporaryDirectory() as t:
   e,r,g=self.make(Path(t))
   with self.assertRaisesRegex(ToolRejected,'absent'):
    r.freeze(json.dumps(dict(tool='capture_page',arguments=dict(path='index.html'))),observations=(FileObservation(r.world,'index.html',hashlib.sha256(self.starter).hexdigest()),))
 def proposals(self):
  return dict(read=dict(tool='read_file',arguments=dict(path='index.html')),create=dict(tool='create_file',arguments=dict(path='style.css',content=self.css.decode())),edit=dict(tool='replace',arguments=dict(path='index.html',before=self.block.decode(),after='<link rel="stylesheet" href="style.css">')),read_css=dict(tool='read_file',arguments=dict(path='style.css')),interact=dict(tool='interact_page',arguments=dict(path='index.html',actions=[dict(kind='click',target='increment',value='')])),finish=dict(tool='finish',arguments=dict(answer='observed external styles')))
 def program(self):
  steps=[('r','read'),('c','create'),('e','edit'),('r2','read'),('rc','read_css'),('i','interact'),('f','finish')]
  lines=['FLOW stylesheet']
  for label,binding in steps:lines+=['PLAN '+label+' from='+binding+' against=world -> p','ACT '+label+' plan=p -> outcome']
  return '\n'.join(lines+['VERIFY v input=outcome contract=interactive-page-inspection-and-finish -> verified','END',''])
 def spec(self):
  return dict(schema=1,interactive_captures=[dict(path='index.html',width=640,height=480)],inspection=dict(path=str(self.check),sha256=hashlib.sha256(self.check_bytes).hexdigest(),target='H09'))
 def test_real_cli_create_edit_inspect_and_offline_completed_reopen(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);e,r,g=self.make(root)
   cfg=dict(schema=1,source=str(e.source),run_id='h09-css',grant={k:list(getattr(g,k)) for k in ['edit_paths','create_paths','read_paths','capture_paths','interact_paths','asset_paths']},browser=dict(executable=str(self.browser.executable),width=640,height=480,timeout=15),profiles={},verification=self.spec(),bindings={k:dict(type='ToolProposal',value=json.dumps(v)) for k,v in self.proposals().items()})
   cfg['grant']['allow_tests']=False
   config=root/'host.json';config.write_text(json.dumps(cfg));program=root/'job.bw';program.write_text(self.program());state=root/'cli-run';cmd=[sys.executable,'-B','-m','branchwrite','run',str(program),'--config',str(config),'--state',str(state)]
   first=subprocess.run(cmd,capture_output=True,text=True,timeout=30);self.assertEqual(first.returncode,0,first.stderr);self.assertTrue(json.loads(first.stdout)['verified'])
   self.assertEqual((state/'world/workspace/style.css').read_bytes(),self.css);self.assertEqual((state/'world/workspace/index.html').read_bytes(),self.good)
   self.assertEqual((e.source/'index.html').read_bytes(),self.starter);self.assertFalse((e.source/'style.css').exists())
   with RuntimeLog(state/'ledger') as log:self.assertEqual(log.read_artifact(Artifact(hashlib.sha256(self.css).hexdigest(),len(self.css))),self.css)
   again=subprocess.run(cmd,capture_output=True,text=True,timeout=30);self.assertEqual(again.returncode,0,again.stderr);self.assertEqual(first.stdout,again.stdout)
 def test_changed_stylesheet_after_capture_cannot_finish(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);e,r,g=self.make(root)
   with RuntimeLog(root/'ledger') as log:
    k=FrameKernel(log);runtime=Interpreter(k,r,verification=self.spec());runtime.start(self.program(),{k:Value('ToolProposal',json.dumps(v)) for k,v in self.proposals().items()})
    captured=False
    for _ in range(100):
     runtime.step()
     if any(f['state']=='Closed' and f['contract']==('ToolOutcome','record') and decode(log.read_artifact(Artifact(*f['result'])))[2]['disposition']=='captured' for f in k.frames()):captured=True;break
    self.assertTrue(captured)
    (e.workspace/'style.css').write_bytes(self.css+b'\n/* same pixels, different bytes */')
    self.assertFalse(runtime.run().value['verified'])

if __name__=='__main__':unittest.main()
