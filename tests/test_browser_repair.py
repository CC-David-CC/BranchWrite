"""H11 repairs need actual error feedback and unchanged independent checks."""
import dataclasses,hashlib,json,os,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from branchwrite.browser_capture import BrowserConfig,PageAction,PageInspection,render_snapshot
from branchwrite.browser_assets import BrowserAsset
from branchwrite.execution import Executor,Grant
from branchwrite.tool_registry import ToolRegistry
from branchwrite.records import RuntimeLog,Artifact,decode,encode
from branchwrite.kernel import FrameKernel
from branchwrite.interpreter import Interpreter,Value
class BrowserRepairTests(unittest.TestCase):
 def setUp(self):
  self.pack=Path(os.environ['BW_BASIC_LOOP_PACK']);self.check=self.pack/'protected/checks.py';self.check_bytes=self.check.read_bytes()
  self.starter=self.pack/'fixtures/starter/H11';self.html=(self.starter/'index.html').read_bytes();self.js=(self.starter/'app.js').read_bytes()
  self.good_js=self.js.replace(b'#missing-count',b'#count');self.assertNotEqual(self.js,self.good_js)
  self.browser=BrowserConfig(Path(os.environ['BW_BROWSER_EXECUTABLE']))
 def assets(self,good=False):
  return tuple(BrowserAsset(name,self.good_js if name=='app.js' and good else (self.starter/name).read_bytes()) for name in ['app.js','style.css','assets/sample.png'])
 def checked(self):
  return BrowserConfig(self.browser.executable,inspection=PageInspection(self.check,hashlib.sha256(self.check_bytes).hexdigest(),'H11'))
 def test_real_original_click_error_is_not_a_protected_pass(self):
  result=render_snapshot(self.html,BrowserConfig(self.browser.executable,actions=(PageAction('click','increment',''),)),assets=self.assets())
  self.assertTrue(result.runtime_errors);self.assertIn('null',' '.join(result.runtime_errors));self.assertTrue(result.isolation['worker_exited'])
  with self.assertRaisesRegex(ValueError,'execution'):render_snapshot(self.html,self.checked(),assets=self.assets())
 def test_one_reference_repair_passes_original_counter_literal_greeting_and_pixels(self):
  result=render_snapshot(self.html,self.checked(),assets=self.assets(True))
  self.assertEqual(result.inspection['status'],'PASS');self.assertEqual(result.runtime_errors,())
  self.assertEqual(result.inspection['actions'],[['click','increment'],['click','increment'],['fill','name=Ada'],['click','greet'],['fill','name=<b>Ada</b>'],['click','greet']])
  self.assertEqual(self.check.read_bytes(),self.check_bytes)
 def make(self,root):
  source=root/'source';shutil.copytree(self.starter,source)
  e=Executor.create(source,root/'world',browser=self.browser)
  g=Grant(('app.js',),False,read_paths=('index.html','app.js','style.css','assets/sample.png'),capture_paths=('index.html',),interact_paths=('index.html',),asset_paths=('app.js','style.css','assets/sample.png'))
  return e,ToolRegistry(e,g),g
 def spec(self,target='H11'):
  return dict(schema=1,interactive_captures=[dict(path='index.html',width=640,height=480)],inspection=dict(path=str(self.check),sha256=hashlib.sha256(self.check_bytes).hexdigest(),target=target))
 def proposals(self):
  return dict(read_html=dict(tool='read_file',arguments=dict(path='index.html')),read_js=dict(tool='read_file',arguments=dict(path='app.js')),click=dict(tool='interact_page',arguments=dict(path='index.html',actions=[dict(kind='click',target='increment',value='')])),edit=dict(tool='replace',arguments=dict(path='app.js',before='#missing-count',after='#count')),finish=dict(tool='finish',arguments=dict(answer='observed and repaired actual handler error')))
 def test_actual_cli_error_feedback_one_repair_verification_and_offline_reopen(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);e,r,g=self.make(root)
   cfg=dict(schema=1,source=str(e.source),run_id='h11-repair',grant={k:list(getattr(g,k)) for k in ['edit_paths','create_paths','read_paths','capture_paths','interact_paths','asset_paths']},browser=dict(executable=str(self.browser.executable),width=640,height=480,timeout=15),profiles={},verification=self.spec(),bindings={k:dict(type='ToolProposal',value=json.dumps(v)) for k,v in self.proposals().items()});cfg['grant']['allow_tests']=False
   steps=['FLOW repair']
   for label,binding in [('rh','read_html'),('rj','read_js'),('bad','click'),('edit','edit'),('rj2','read_js'),('rh2','read_html'),('good','click'),('done','finish')]:
    steps+=['PLAN '+label+' from='+binding+' against=world -> p','ACT '+label+' plan=p -> outcome']
    if label=='bad':steps+=['TRANSFORM error input=outcome contract=tool-feedback -> error']
   steps+=['VERIFY v input=outcome contract=interactive-page-inspection-and-finish -> verified','END','']
   f=root/'host.json';f.write_text(json.dumps(cfg));program=root/'job.bw';program.write_text('\n'.join(steps));state=root/'run'
   cmd=[sys.executable,'-B','-m','branchwrite','run',str(program),'--config',str(f),'--state',str(state)]
   first=subprocess.run(cmd,capture_output=True,text=True,timeout=30);self.assertEqual(first.returncode,0,first.stderr);self.assertTrue(json.loads(first.stdout)['verified'])
   with RuntimeLog(state/'ledger') as log:
    k=FrameKernel(log);outcomes=[decode(log.read_artifact(Artifact(*v['result'])))[2] for v in k.frames() if v['contract']==('ToolOutcome','record')]
    errors=[v for v in outcomes if v['disposition']=='browser_error'];self.assertEqual(len(errors),1)
    self.assertTrue(errors[0]['details']['isolation']['worker_exited']);self.assertTrue(log.read_artifact(Artifact(*errors[0]['image'])).startswith(b'\x89PNG'))
    result=decode(log.read_artifact(Artifact(*k.frame('program')['result'])))[2]
    feedback=json.loads(result['bindings']['error'][1]);self.assertEqual(feedback['exit_code'],1);self.assertIn('null',feedback['stderr']);self.assertTrue(feedback['capture']['runtime_errors'])
   self.assertEqual((e.source/'app.js').read_bytes(),self.js);self.assertEqual((state/'world/workspace/app.js').read_bytes(),self.good_js)
   again=subprocess.run(cmd,capture_output=True,text=True,timeout=30);self.assertEqual(again.returncode,0,again.stderr);self.assertEqual(first.stdout,again.stdout)
 def forged(self,interactive):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);e,r,g=self.make(root);(e.workspace/'app.js').write_bytes(self.good_js)
   proposals=self.proposals();tool='click' if interactive else 'capture';proposals['capture']=dict(tool='capture_page',arguments=dict(path='index.html'))
   spec=self.spec('H10') if interactive else dict(schema=1,files=[dict(path='index.html',sha256=hashlib.sha256(self.html).hexdigest())],captures=[dict(path='index.html',width=640,height=480)])
   policy='interactive-page-inspection-and-finish' if interactive else 'page-capture-and-finish'
   program='FLOW forged\nPLAN r from=read_html against=world -> p\nACT r plan=p\nPLAN c from='+tool+' against=world -> p\nACT c plan=p\nPLAN f from=finish against=world -> p\nACT f plan=p -> outcome\nVERIFY v input=outcome contract='+policy+' -> verified\nEND\n'
   original=r.execute
   def inject(*args):
    out=original(*args)
    if out.tool in ('capture_page','interact_page'):out=dataclasses.replace(out,details=encode(dict(out.metadata,runtime_errors=['injected error flag'])))
    return out
   with RuntimeLog(root/'ledger') as log:
    runtime=Interpreter(FrameKernel(log),r,verification=spec);runtime.start(program,{k:Value('ToolProposal',json.dumps(v)) for k,v in proposals.items()})
    with patch.object(r,'execute',side_effect=inject):result=runtime.run()
    self.assertFalse(result.value['verified'])
 def test_error_metadata_cannot_be_forged_into_static_success(self):self.forged(False)
 def test_error_metadata_cannot_be_forged_into_interactive_success(self):self.forged(True)
if __name__=='__main__':unittest.main()
