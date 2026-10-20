"""Actual sandboxed page capture through the generic CLI and verifier.

Synthetic tool proposals test host routing here. Autonomous Q4 H01 is separate.
"""
import hashlib,io,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from branchwrite.execution import Executor,Grant
from branchwrite.browser_capture import BrowserConfig
from branchwrite.tool_registry import ToolRegistry
from branchwrite.records import RuntimeLog,Artifact,decode
from branchwrite.kernel import FrameKernel
from branchwrite.interpreter import Interpreter,Value,AdmissionError

PAGE=b'<!doctype html><style>body{margin:0}.block{width:40px;height:50px;background:rgb(22,163,74)}</style><div class="block"></div>'
class CaptureCompletionTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.base=Path(self.temp.name)
  self.source=self.base/'source';self.source.mkdir();(self.source/'index.html').write_bytes(PAGE)
  self.browser=BrowserConfig(Path(os.environ['BW_BROWSER_EXECUTABLE']))
  self.executor=Executor.create(self.source,self.base/'world',browser=self.browser)
  self.registry=ToolRegistry(self.executor,Grant((),False,read_paths=('index.html',),capture_paths=('index.html',)))
  self.log=RuntimeLog(self.base/'log');self.addCleanup(self.close);self.kernel=FrameKernel(self.log)
  self.sha=hashlib.sha256(PAGE).hexdigest()
  self.spec=dict(schema=1,files=[dict(path='index.html',sha256=self.sha)],captures=[dict(path='index.html',width=640,height=480)])
 def close(self):
  if not self.log._closed:self.log.close()
 def bindings(self):
  return {name:Value('ToolProposal',json.dumps(dict(tool=tool,arguments=args))) for name,tool,args in [
   ('read','read_file',dict(path='index.html')),('capture','capture_page',dict(path='index.html')),('finish','finish',dict(answer='captured'))]}
 def program(self,capture=True,feedback=False):
  lines=['FLOW page','PLAN r from=read against=world -> plan','ACT r plan=plan -> outcome']
  if capture:
   lines+=['PLAN c from=capture against=world -> plan','ACT c plan=plan -> outcome']
   if feedback:lines+=['TRANSFORM f input=outcome contract=tool-feedback -> feedback']
  lines+=['PLAN f from=finish against=world -> plan','ACT f plan=plan -> outcome','VERIFY v input=outcome contract=page-capture-and-finish -> verified','END']
  return '\n'.join(lines)+'\n'
 def test_actual_capture_and_source_are_required_for_completion(self):
  runtime=Interpreter(self.kernel,self.registry,verification=self.spec);runtime.start(self.program(),self.bindings());result=runtime.run()
  self.assertTrue(result.value['verified']);v=result.value['bindings']['verified'][1];self.assertEqual(v['policy'],'page-capture-and-finish')
  capture=v['captures'][0];self.assertEqual(capture['source_sha256'],self.sha)
  body=self.log.read_artifact(Artifact(capture['image_sha256'],capture['image_bytes']))
  from PIL import Image
  with Image.open(io.BytesIO(body)) as image:self.assertEqual(image.size,(640,480));self.assertEqual(image.convert('RGB').getpixel((10,10)),(22,163,74))
  self.assertEqual((self.source/'index.html').read_bytes(),PAGE)
 def test_finish_after_read_without_capture_is_not_a_pass(self):
  runtime=Interpreter(self.kernel,self.registry,verification=self.spec);runtime.start(self.program(False),self.bindings())
  self.assertFalse(runtime.run().value['verified'])
 def test_capture_metadata_is_in_tool_feedback(self):
  runtime=Interpreter(self.kernel,self.registry,verification=self.spec);runtime.start(self.program(feedback=True),self.bindings());r=runtime.run()
  feedback=json.loads(r.value['bindings']['feedback'][1]);self.assertEqual(feedback['image']['media_type'],'image/png')
  self.assertEqual(feedback['capture']['served_sha256'],self.sha);self.assertEqual(feedback['capture']['viewport'],[640,480])
  self.assertEqual(feedback['image']['sha256'],r.value['bindings']['verified'][1]['captures'][0]['image_sha256'])
 def test_file_changed_after_capture_cannot_pass(self):
  runtime=Interpreter(self.kernel,self.registry,verification=self.spec);runtime.start(self.program(),self.bindings())
  while self.kernel.frame('program')['pc']<4:runtime.step()
  while self.kernel.frame('program')['state']=='Waiting':runtime.step()
  (self.executor.workspace/'index.html').write_bytes(PAGE+b'changed')
  self.assertFalse(runtime.run().value['verified'])
 def test_incompatible_viewport_or_missing_capture_grant_rejected(self):
  import copy
  wrong=copy.deepcopy(self.spec);wrong['captures'][0]['width']=641
  with self.assertRaises((AdmissionError,ValueError)):Interpreter(self.kernel,self.registry,verification=wrong)
  other=ToolRegistry(self.executor,Grant((),False,read_paths=('index.html',)))
  with self.assertRaises((AdmissionError,ValueError)):Interpreter(self.kernel,other,verification=self.spec)
 def test_file_policy_cannot_satisfy_capture_contract(self):
  spec=dict(schema=1,files=self.spec['files']);runtime=Interpreter(self.kernel,self.registry,verification=spec)
  with self.assertRaisesRegex(AdmissionError,'capture policy'):runtime.start(self.program(),self.bindings())

class CaptureCliTests(unittest.TestCase):
 def config(self,root):
  source=root/'source';source.mkdir();(source/'index.html').write_bytes(PAGE);sha=hashlib.sha256(PAGE).hexdigest()
  return dict(schema=1,source=str(source),run_id='capture-cli',grant=dict(edit_paths=[],read_paths=['index.html'],create_paths=[],capture_paths=['index.html'],allow_tests=False),browser=dict(executable=os.environ['BW_BROWSER_EXECUTABLE'],width=640,height=480,timeout=15),verification=dict(schema=1,files=[dict(path='index.html',sha256=sha)],captures=[dict(path='index.html',width=640,height=480)]),profiles={},bindings={name:dict(type='ToolProposal',value=json.dumps(dict(tool=tool,arguments=args))) for name,tool,args in [('read','read_file',dict(path='index.html')),('capture','capture_page',dict(path='index.html')),('finish','finish',dict(answer='actual image'))]})
 def command(self,root,cfg):
  config=root/'host.json';config.write_text(json.dumps(cfg));program=root/'job.bw'
  program.write_text('FLOW page\nPLAN r from=read against=world -> plan\nACT r plan=plan\nPLAN c from=capture against=world -> plan\nACT c plan=plan\nPLAN f from=finish against=world -> plan\nACT f plan=plan -> outcome\nVERIFY v input=outcome contract=page-capture-and-finish -> verified\nEND\n')
  return [sys.executable,'-B','-m','branchwrite','run',str(program),'--config',str(config),'--state',str(root/'run')]
 def test_actual_cli_returns_png_path_source_and_replays_without_browser_work(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);cfg=self.config(root);cmd=self.command(root,cfg)
   first=subprocess.run(cmd,capture_output=True,text=True,timeout=30);self.assertEqual(first.returncode,0,first.stderr)
   result=json.loads(first.stdout);self.assertTrue(result['verified']);self.assertEqual(len(result['artifacts']),1)
   image=result['artifacts'][0];self.assertEqual(image['media_type'],'image/png');self.assertEqual(image['source_sha256'],cfg['verification']['files'][0]['sha256'])
   png=Path(image['path']).read_bytes();self.assertEqual(hashlib.sha256(png).hexdigest(),image['sha256']);self.assertTrue(png.startswith(b'\x89PNG\r\n\x1a\n'))
   # Capture operation artifacts stay byte-identical on process restart. The
   # completed CLI has no new browser dispatch and returns its saved results.
   world=root/'run/world';before={str(p.relative_to(world)):p.read_bytes() for p in world.rglob('*') if p.is_file()}
   second=subprocess.run(cmd,capture_output=True,text=True,timeout=30);self.assertEqual(second.returncode,0,second.stderr);self.assertEqual(first.stdout,second.stdout)
   self.assertEqual(before,{str(p.relative_to(world)):p.read_bytes() for p in world.rglob('*') if p.is_file()})
 def test_missing_browser_or_forbidden_options_fail_before_state_creation(self):
  from branchwrite.run_cli import _config
  with tempfile.TemporaryDirectory() as t:
   cfg=self.config(Path(t))
   for mutation in ['missing','sandbox','inspection','missing-read']:
    import copy
    bad=copy.deepcopy(cfg)
    if mutation=='missing':del bad['browser']
    elif mutation=='missing-read':bad['grant']['read_paths']=[]
    else:bad['browser'][mutation]=False
    with self.subTest(mutation=mutation),self.assertRaises((AdmissionError,ValueError)):_config(json.dumps(bad))
