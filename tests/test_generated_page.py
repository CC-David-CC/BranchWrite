"""Generated-page verification on actual filesystem and sandboxed Chromium.

Tool proposals here are synthetic routing fixtures, not autonomous model evidence.
Protected assertions remain unchanged outside the candidate workspace.
"""
import hashlib,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from branchwrite.execution import Executor,Grant
from branchwrite.browser_capture import BrowserConfig
from branchwrite.tool_registry import ToolRegistry
from branchwrite.records import RuntimeLog
from branchwrite.kernel import FrameKernel
from branchwrite.interpreter import Interpreter,Value,AdmissionError
PAGE=b'<!doctype html><style>body{background:white}.square{width:80px;height:80px;background:#2463eb}</style><h1>Loop Lab</h1><div id="row"><div id="a" class="square"></div></div>'
class GeneratedPageTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.base=Path(self.temp.name)
  self.source=self.base/'source';self.source.mkdir()
  self.browser=BrowserConfig(Path(os.environ['BW_BROWSER_EXECUTABLE']))
  self.executor=Executor.create(self.source,self.base/'world',browser=self.browser)
  self.registry=ToolRegistry(self.executor,Grant((),False,create_paths=('index.html',),read_paths=('index.html',),capture_paths=('index.html',)))
  self.log=RuntimeLog(self.base/'ledger');self.addCleanup(self.close);self.kernel=FrameKernel(self.log)
  inspector=Path(os.environ['BW_BASIC_LOOP_PACK'])/'protected/checks.py'
  self.spec=dict(schema=1,inspected_captures=[dict(path='index.html',width=640,height=480)],inspection=dict(path=str(inspector),sha256=hashlib.sha256(inspector.read_bytes()).hexdigest(),target='H03'))
 def close(self):
  if not self.log._closed:self.log.close()
 def bindings(self,page=PAGE):
  sha=hashlib.sha256(page).hexdigest()
  return {name:Value('ToolProposal',json.dumps(dict(tool=tool,arguments=args))) for name,tool,args in [
   ('create','create_file',dict(path='index.html',content=page.decode())),
   ('read','read_file',dict(path='index.html')),('capture','capture_page',dict(path='index.html')),
   ('finish','finish',dict(answer='created and captured'))]}
 def program(self,read=True,capture=True):
  lines=['FLOW page','PLAN c from=create against=world -> plan','ACT c plan=plan']
  if read:lines+=['PLAN r from=read against=world -> plan','ACT r plan=plan']
  if capture:lines+=['PLAN s from=capture against=world -> plan','ACT s plan=plan']
  lines+=['PLAN f from=finish against=world -> plan','ACT f plan=plan -> outcome','VERIFY v input=outcome contract=page-inspection-and-finish -> verified','END']
  return '\n'.join(lines)+'\n'
 def runtime(self,spec=None):return Interpreter(self.kernel,self.registry,verification=self.spec if spec is None else spec)
 def test_unknown_created_bytes_pass_only_after_real_dom_pixels_and_same_capture(self):
  runtime=self.runtime();runtime.start(self.program(),self.bindings());result=runtime.run()
  v=result.value['bindings']['verified'][1];self.assertTrue(result.value['verified'])
  self.assertEqual(v['policy'],'page-inspection-and-finish');self.assertEqual(v['inspections'][0]['status'],'PASS')
  self.assertEqual(v['inspections'][0]['image_sha256'],v['captures'][0]['image_sha256'])
  self.assertTrue(v['inspections'][0]['isolation']['worker_exited'])
  self.assertFalse((self.source/'index.html').exists())
 def test_wrong_generated_heading_fails_protected_assertions_without_changing_source(self):
  page=PAGE.replace(b'Loop Lab',b'Wrong heading');runtime=self.runtime();runtime.start(self.program(),self.bindings(page));r=runtime.run()
  self.assertFalse(r.value['verified']);v=r.value['bindings']['verified'][1]
  self.assertEqual(v['inspections'][0]['status'],'FAIL');self.assertEqual((self.executor.workspace/'index.html').read_bytes(),page)
 def test_wrong_generated_color_fails_original_pixel_or_dom_checks(self):
  page=PAGE.replace(b'#2463eb',b'#ef4444');runtime=self.runtime();runtime.start(self.program(),self.bindings(page));r=runtime.run()
  self.assertFalse(r.value['verified']);self.assertEqual(r.value['bindings']['verified'][1]['inspections'][0]['status'],'FAIL')
 def missing_witness(self,read,capture):
  from branchwrite import verification
  runtime=self.runtime();runtime.start(self.program(read,capture),self.bindings())
  with patch.object(verification,'inspect_captured_page',side_effect=AssertionError('missing witness must not inspect')):
   r=runtime.run();self.assertFalse(r.value['verified'])
 def test_without_read_never_runs_protected_browser(self):self.missing_witness(False,True)
 def test_without_capture_never_runs_protected_browser(self):self.missing_witness(True,False)
 def test_without_both_never_runs_protected_browser(self):self.missing_witness(False,False)
 def test_changed_source_after_capture_fails_without_running_protected_browser(self):
  from branchwrite import verification
  runtime=self.runtime();runtime.start(self.program(),self.bindings())
  while self.kernel.frame('program')['pc']<6:runtime.step()
  while self.kernel.frame('program')['state']=='Waiting':runtime.step()
  (self.executor.workspace/'index.html').write_bytes(PAGE+b'changed')
  with patch.object(verification,'inspect_captured_page',side_effect=AssertionError('stale capture must not inspect')):
   self.assertFalse(runtime.run().value['verified'])
 def test_invalid_checker_digest_or_candidate_owned_checker_reject_before_root(self):
  import copy
  for mode in ['digest','candidate']:
   spec=copy.deepcopy(self.spec)
   if mode=='digest':spec['inspection']['sha256']='0'*64
   else:
    q=self.source/'checks.py';q.write_bytes(Path(spec['inspection']['path']).read_bytes());spec['inspection']['path']=str(q)
   with self.subTest(mode=mode),self.assertRaises((AdmissionError,ValueError)):self.runtime(spec)
  self.assertEqual(self.log.event_count,0)
 def test_missing_capture_grant_or_wrong_viewport_reject_before_root(self):
  import copy
  wrong=copy.deepcopy(self.spec);wrong['inspected_captures'][0]['width']=641
  with self.assertRaises((AdmissionError,ValueError)):self.runtime(wrong)
  registry=ToolRegistry(self.executor,Grant((),False,create_paths=('index.html',),read_paths=('index.html',)))
  with self.assertRaises((AdmissionError,ValueError)):Interpreter(self.kernel,registry,verification=self.spec)
  self.assertEqual(self.log.event_count,0)
 def test_completed_workflow_reopen_does_not_repeat_browser_or_file_effects(self):
  runtime=self.runtime();runtime.start(self.program(),self.bindings());first=runtime.run();self.close()
  self.log=RuntimeLog(self.base/'ledger');self.kernel=FrameKernel(self.log);runtime=self.runtime()
  with patch.object(self.executor,'capture_page',side_effect=AssertionError('completed capture cannot repeat')):
   runtime.start(self.program(),self.bindings());second=runtime.run()
  self.assertEqual(first.value,second.value)

 def cli(self,page=PAGE):
  import subprocess,sys
  cfg=dict(schema=1,source=str(self.source),run_id='generated-page-cli',
   grant=dict(edit_paths=[],create_paths=['index.html'],read_paths=['index.html'],capture_paths=['index.html'],allow_tests=False),
   browser=dict(executable=str(self.browser.executable),width=640,height=480,timeout=15),
   verification=self.spec,profiles={},bindings={name:dict(type=value.type,value=value.data) for name,value in self.bindings(page).items()})
  config=self.base/'host.json';config.write_text(json.dumps(cfg));program=self.base/'page.bw';program.write_text(self.program())
  command=[sys.executable,'-B','-m','branchwrite','run',str(program),'--config',str(config),'--state',str(self.base/'cli-run')]
  return subprocess.run(command,capture_output=True,text=True,timeout=45),command
 def test_real_cli_creates_inspects_and_reopens_same_actual_artifacts(self):
  import subprocess
  first,command=self.cli();self.assertEqual(first.returncode,0,first.stderr);r=json.loads(first.stdout)
  self.assertTrue(r['verified']);self.assertEqual(len(r['artifacts']),1)
  self.assertEqual(hashlib.sha256(Path(r['artifacts'][0]['path']).read_bytes()).hexdigest(),r['artifacts'][0]['sha256'])
  second=subprocess.run(command,capture_output=True,text=True,timeout=45)
  self.assertEqual(second.returncode,0,second.stderr);self.assertEqual(first.stdout,second.stdout)
  self.assertFalse((self.source/'index.html').exists())
 def test_real_cli_wrong_page_returns_task_failure_and_keeps_capture(self):
  first,_=self.cli(PAGE.replace(b'Loop Lab',b'Wrong heading'))
  self.assertEqual(first.returncode,1,first.stderr);r=json.loads(first.stdout);self.assertFalse(r['verified'])
  self.assertEqual(len(r['artifacts']),1);self.assertTrue(Path(r['artifacts'][0]['path']).read_bytes().startswith(b'\x89PNG'))

 def test_protected_pass_on_different_png_bytes_does_not_accept_original_capture(self):
  from dataclasses import replace
  from branchwrite import verification
  real=verification.inspect_captured_page
  def different(*args):
   rendered=real(*args);return replace(rendered,png=rendered.png+b'extra')
  runtime=self.runtime();runtime.start(self.program(),self.bindings())
  with patch.object(verification,'inspect_captured_page',side_effect=different):
   r=runtime.run()
  self.assertFalse(r.value['verified']);self.assertFalse(r.value['bindings']['verified'][1]['inspections'][0]['same_capture'])
 def test_incomplete_protected_worker_exit_witness_cannot_accept(self):
  from dataclasses import replace
  from branchwrite import verification
  real=verification.inspect_captured_page
  def incomplete(*args):
   rendered=real(*args);return replace(rendered,isolation=dict(rendered.isolation,worker_exited=False))
  runtime=self.runtime();runtime.start(self.program(),self.bindings())
  with patch.object(verification,'inspect_captured_page',side_effect=incomplete):
   self.assertFalse(runtime.run().value['verified'])
