"""Same-recipe pixels plus independent unchanged protected checks, no model."""
import copy,hashlib,json,os,subprocess,sys,tempfile,unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from branchwrite.browser_capture import BrowserConfig,PageAction
from branchwrite.execution import Executor,Grant
from branchwrite.tool_registry import ToolRegistry
from branchwrite.records import RuntimeLog,Artifact,decode
from branchwrite.kernel import FrameKernel
from branchwrite.interpreter import Interpreter,Value,AdmissionError
class InteractivePagePolicyTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
  self.pack=Path(os.environ['BW_BASIC_LOOP_PACK']);self.check=self.pack/'protected/checks.py';self.check_bytes=self.check.read_bytes()
  starter=(self.pack/'fixtures/starter/H06/index.html').read_bytes()
  controls=b'<button id="increment">Add one</button><output id="count">0</output><script>document.querySelector("#increment").onclick=()=>{const n=document.querySelector("#count");n.textContent=String(Number(n.textContent)+1);};</script>'
  self.good=starter.replace(b'</main>',controls+b'</main>')
  self.source=self.root/'source';self.source.mkdir();(self.source/'index.html').write_bytes(self.good)
  self.browser=BrowserConfig(Path(os.environ['BW_BROWSER_EXECUTABLE']))
  self.executor=Executor.create(self.source,self.root/'world',browser=self.browser)
  self.registry=ToolRegistry(self.executor,Grant(('index.html',),False,read_paths=('index.html',),capture_paths=('index.html',),interact_paths=('index.html',)))
  self.log=RuntimeLog(self.root/'ledger');self.addCleanup(self.close);self.kernel=FrameKernel(self.log)
  self.spec=dict(schema=1,interactive_captures=[dict(path='index.html',width=640,height=480)],inspection=dict(path=str(self.check),sha256=hashlib.sha256(self.check_bytes).hexdigest(),target='H06'))
 def close(self):
  if not self.log._closed:self.log.close()
 def bindings(self,payload=None):
  sha=hashlib.sha256(self.good if payload is None else payload).hexdigest()
  values=dict(read=dict(tool='read_file',arguments=dict(path='index.html')),
   click=dict(tool='interact_page',arguments=dict(path='index.html',actions=[dict(kind='click',target='increment',value='')])),
   capture=dict(tool='capture_page',arguments=dict(path='index.html')),finish=dict(tool='finish',arguments=dict(answer='clicked and inspected')))
  return {k:Value('ToolProposal',json.dumps(v)) for k,v in values.items()}
 def program(self,tool='click',contract='interactive-page-inspection-and-finish'):
  return 'FLOW page\nPLAN r from=read against=world -> plan\nACT r plan=plan\nPLAN c from='+tool+' against=world -> plan\nACT c plan=plan -> outcome\nPLAN f from=finish against=world -> plan\nACT f plan=plan -> done\nVERIFY v input=done contract='+contract+' -> verified\nEND\n'
 def runtime(self,spec=None):return Interpreter(self.kernel,self.registry,verification=self.spec if spec is None else spec)
 def test_one_model_click_and_independent_two_checker_clicks_are_distinct_valid_evidence(self):
  runtime=self.runtime();runtime.start(self.program(),self.bindings());r=runtime.run();v=r.value['bindings']['verified'][1]
  self.assertTrue(r.value['verified']);self.assertEqual(v['policy'],'interactive-page-inspection-and-finish')
  self.assertTrue(v['inspections'][0]['same_capture']);self.assertEqual(v['inspections'][0]['checker']['actions'],[['click','increment'],['click','increment']])
  self.assertEqual(v['captures'][0]['actions'],[dict(kind='click',target='increment',value='')])
  self.assertNotEqual(v['inspections'][0]['protected_image'][0],v['captures'][0]['image_sha256'])
  self.assertTrue(self.log.read_artifact(Artifact(*v['inspections'][0]['protected_image'])).startswith(b'\x89PNG'))
  self.assertEqual(self.check.read_bytes(),self.check_bytes)
 def test_checker_alone_cannot_replace_model_interaction(self):
  runtime=self.runtime();runtime.start(self.program(tool='capture'),self.bindings())
  with patch('branchwrite.verification.inspect_captured_page',side_effect=AssertionError('missing model interaction')):
   self.assertFalse(runtime.run().value['verified'])
 def test_broken_handler_fails_unchanged_protected_assertions(self):
  bad=self.good.replace(b'Number(n.textContent)+1',b'Number(n.textContent)+0')
  (self.executor.workspace/'index.html').write_bytes(bad);runtime=self.runtime();runtime.start(self.program(),self.bindings(bad));r=runtime.run()
  self.assertFalse(r.value['verified']);v=r.value['bindings']['verified'][1]
  self.assertEqual(v['inspections'][0]['checker']['status'],'FAIL');self.assertTrue(v['inspections'][0]['same_capture'])
 def test_altered_action_receipt_cannot_pass_original_plan(self):
  actual=self.executor.interact_page
  def wrong(*a,**kw):return replace(actual(*a,**kw),actions=({'kind':'click','target':'increment','value':''},)*2)
  runtime=self.runtime();runtime.start(self.program(),self.bindings())
  with patch.object(self.executor,'interact_page',side_effect=wrong),patch('branchwrite.verification.inspect_captured_page',side_effect=AssertionError('plan differs')):
   self.assertFalse(runtime.run().value['verified'])
 def test_different_replay_png_cannot_pass(self):
  from branchwrite import verification
  actual=verification.replay_interaction
  def wrong(*a,**kw):return replace(actual(*a,**kw),png=b'not the same PNG')
  runtime=self.runtime();runtime.start(self.program(),self.bindings())
  with patch.object(verification,'replay_interaction',side_effect=wrong):
   r=runtime.run();self.assertFalse(r.value['verified']);self.assertFalse(r.value['bindings']['verified'][1]['inspections'][0]['same_capture'])
 def test_unretired_original_browser_cannot_pass(self):
  actual=self.executor.interact_page
  def wrong(*a,**kw):
   r=actual(*a,**kw);return replace(r,isolation={**r.isolation,'worker_exited':False})
  runtime=self.runtime();runtime.start(self.program(),self.bindings())
  with patch.object(self.executor,'interact_page',side_effect=wrong),patch('branchwrite.verification.inspect_captured_page',side_effect=AssertionError('not retired')):
   self.assertFalse(runtime.run().value['verified'])
 def test_changed_source_after_interaction_cannot_use_old_read_or_image(self):
  actual=self.executor.interact_page
  def changed(*a,**kw):
   r=actual(*a,**kw);(self.executor.workspace/'index.html').write_bytes(self.good+b'changed');return r
  runtime=self.runtime();runtime.start(self.program(),self.bindings())
  with patch.object(self.executor,'interact_page',side_effect=changed),patch('branchwrite.verification.inspect_captured_page',side_effect=AssertionError('stale source')):
   self.assertFalse(runtime.run().value['verified'])
 def test_unretired_replay_cannot_pass(self):
  from branchwrite import verification
  actual=verification.replay_interaction
  def wrong(*a,**kw):
   r=actual(*a,**kw);return replace(r,isolation={**r.isolation,'worker_exited':False})
  runtime=self.runtime();runtime.start(self.program(),self.bindings())
  with patch.object(verification,'replay_interaction',side_effect=wrong):
   self.assertFalse(runtime.run().value['verified'])
 def test_protected_pass_without_retired_namespace_cannot_pass(self):
  from branchwrite import verification
  actual=verification.inspect_captured_page
  def wrong(*a,**kw):
   r=actual(*a,**kw);return replace(r,isolation={**r.isolation,'worker_exited':False})
  runtime=self.runtime();runtime.start(self.program(),self.bindings())
  with patch.object(verification,'inspect_captured_page',side_effect=wrong):
   r=runtime.run();self.assertFalse(r.value['verified']);self.assertEqual(r.value['bindings']['verified'][1]['inspections'][0]['checker']['status'],'PASS')
 def test_static_contract_remains_static(self):
  spec=copy.deepcopy(self.spec);spec['inspected_captures']=spec.pop('interactive_captures')
  runtime=self.runtime(spec);runtime.start(self.program(contract='page-inspection-and-finish'),self.bindings())
  with patch('branchwrite.verification.inspect_captured_page',side_effect=AssertionError('no static capture')):
   self.assertFalse(runtime.run().value['verified'])
 def test_wrong_policy_and_missing_interaction_grant_reject_at_admission(self):
  spec=copy.deepcopy(self.spec);spec['inspected_captures']=spec.pop('interactive_captures')
  runtime=self.runtime(spec)
  with self.assertRaises(AdmissionError):runtime.start(self.program(),self.bindings())
  other=ToolRegistry(self.executor,Grant((),False,read_paths=('index.html',),capture_paths=('index.html',)))
  with self.assertRaises((ValueError,AdmissionError)):Interpreter(self.kernel,other,verification=self.spec)
  self.assertEqual(self.log.event_count,0)
 def test_actual_cli_returns_interaction_image_and_reopens_without_browser(self):
  cfg=dict(schema=1,source=str(self.source),run_id='interactive-policy-cli',grant=dict(edit_paths=['index.html'],create_paths=[],read_paths=['index.html'],capture_paths=['index.html'],interact_paths=['index.html'],allow_tests=False),browser=dict(executable=str(self.browser.executable),width=640,height=480,timeout=15),profiles={},verification=self.spec,bindings={k:dict(type=v.type,value=v.data) for k,v in self.bindings().items()})
  path=self.root/'host.json';path.write_text(json.dumps(cfg));program=self.root/'page.bw';program.write_text(self.program());state=self.root/'run'
  cmd=[sys.executable,'-B','-m','branchwrite','run',str(program),'--config',str(path),'--state',str(state)]
  first=subprocess.run(cmd,capture_output=True,text=True,timeout=30);self.assertEqual(first.returncode,0,first.stderr);value=json.loads(first.stdout)
  self.assertTrue(value['verified']);self.assertEqual(len(value['artifacts']),1)
  again=subprocess.run(cmd,capture_output=True,text=True,timeout=30);self.assertEqual(again.returncode,0,again.stderr);self.assertEqual(first.stdout,again.stdout)
if __name__=='__main__':unittest.main()
