"""Real browser errors need complete receipts and proven retirement."""
import hashlib,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from branchwrite.browser_capture import BrowserConfig,PageAction,render_snapshot
from branchwrite.browser_assets import BrowserAsset
from branchwrite.execution import Executor,Grant
from branchwrite.tool_registry import ToolRegistry,FileObservation,EffectIndeterminate
from branchwrite.tool_dispatch import admit_tool,dispatch_tool,ReconciliationRequired
from branchwrite.kernel import FrameKernel,ResultContract
from branchwrite.records import RuntimeLog,Artifact
PAGE=b'<button id="inc">Add</button><output id="count">0</output><script src="app.js"></script>'
BROKEN=b"document.querySelector('#inc').onclick=()=>{document.querySelector('#absent').textContent='1'};"
class BrowserErrorTests(unittest.TestCase):
 def browser(self,actions=()):return BrowserConfig(Path(os.environ['BW_BROWSER_EXECUTABLE']),actions=actions)
 def assets(self):return (BrowserAsset('app.js',BROKEN),)
 def make(self,root):
  source=root/'source';source.mkdir();(source/'index.html').write_bytes(PAGE);(source/'app.js').write_bytes(BROKEN)
  e=Executor.create(source,root/'world',browser=self.browser())
  g=Grant(('index.html','app.js'),False,read_paths=('index.html','app.js'),capture_paths=('index.html',),interact_paths=('index.html',),asset_paths=('app.js',))
  return e,ToolRegistry(e,g)
 def proposal(self):return json.dumps(dict(tool='interact_page',arguments=dict(path='index.html',actions=[dict(kind='click',target='inc',value='')])))
 def observe(self,r):return (FileObservation(r.world,'index.html',hashlib.sha256(PAGE).hexdigest()),)
 def spawn(self,k,r):
  k.create_root('root','attempt',k.log.put_artifact(b'FLOW root\nEND\n'),k.log.put_artifact(b'input'),ResultContract('Root','record'))
  admit_tool(k,r,'root',expected_epoch=0,child_id='click',attempt_id='click-attempt',slot='out',next_pc=1,proposal=self.proposal(),observations=self.observe(r))
 def test_real_click_exception_keeps_png_text_exact_actions_and_retirement(self):
  a=PageAction('click','inc','');result=render_snapshot(PAGE,self.browser((a,)),assets=self.assets())
  self.assertTrue(result.runtime_errors);self.assertIn('null',' '.join(result.runtime_errors))
  self.assertEqual(result.actions,(a.wire,));self.assertIn('0',result.text)
  self.assertTrue(result.png.startswith(b'\x89PNG'));self.assertEqual(result.served_sha256,hashlib.sha256(PAGE).hexdigest())
  self.assertTrue(result.isolation['worker_exited']);self.assertEqual(result.isolation['namespace_members_after'],[])
  self.assertEqual(result.asset_manifest,(self.assets()[0].manifest,))
 def test_initial_script_exception_is_also_a_bounded_observation(self):
  result=render_snapshot(b'<p>original page</p><script>throw new Error("startup failure")</script>',self.browser())
  self.assertEqual(result.runtime_errors,('startup failure',));self.assertEqual(result.actions,());self.assertTrue(result.isolation['worker_exited'])
 def test_error_count_and_each_message_are_bounded(self):
  page=b''.join(b'<script>throw new Error("'+str(i).encode()+b':'+b'x'*3000+b'")</script>' for i in range(20))
  result=render_snapshot(page,self.browser());self.assertEqual(len(result.runtime_errors),16)
  self.assertTrue(all(0<len(v)<=1024 for v in result.runtime_errors))
 def test_actual_registry_returns_error_exit_and_exact_resource_artifacts(self):
  with tempfile.TemporaryDirectory() as t:
   e,r=self.make(Path(t));plan=r.freeze(self.proposal(),observations=self.observe(r));out=r.execute(plan,'actual-error')
   self.assertEqual(out.disposition,'browser_error');self.assertEqual(out.exit_code,1)
   self.assertIn(b'null',out.stderr);self.assertTrue(out.metadata['runtime_errors']);self.assertTrue(out.metadata['isolation']['worker_exited'])
   self.assertEqual(out.metadata['served_sha256'],hashlib.sha256(PAGE).hexdigest());self.assertEqual(out.observation.sha256,hashlib.sha256(PAGE).hexdigest())
   self.assertEqual(out.assets[0].read_bytes(),BROKEN);self.assertTrue(out.image.read_bytes().startswith(b'\x89PNG'))
 def test_settled_error_dispatch_reopens_without_executing_again(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);e,r=self.make(root)
   with RuntimeLog(root/'ledger') as log:
    k=FrameKernel(log);self.spawn(k,r);first=dispatch_tool(k,r,'click');self.assertEqual(first['disposition'],'browser_error');self.assertEqual(k.frame('click')['state'],'Closed')
    self.assertTrue(log.read_artifact(Artifact(*first['image'])).startswith(b'\x89PNG'))
   with RuntimeLog(root/'ledger') as log:
    k=FrameKernel(log)
    with patch.object(r,'execute',side_effect=AssertionError('must not redispatch')):again=dispatch_tool(k,r,'click')
    self.assertEqual(again,first)
 def test_failed_artifact_publication_stays_unresolved_and_cannot_resend(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);e,r=self.make(root)
   with RuntimeLog(root/'ledger') as log:
    k=FrameKernel(log);self.spawn(k,r)
    with patch.object(e,'_artifact',side_effect=OSError('injected publication failure')):
     with self.assertRaises(EffectIndeterminate):dispatch_tool(k,r,'click')
    self.assertEqual(k.frame('click')['state'],'Waiting')
    with patch.object(r,'execute',side_effect=AssertionError('must not resend')):
     with self.assertRaises(ReconciliationRequired):dispatch_tool(k,r,'click')
 def test_unproven_namespace_retirement_stays_unresolved(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);e,r=self.make(root)
   with RuntimeLog(root/'ledger') as log:
    k=FrameKernel(log);self.spawn(k,r)
    with patch('branchwrite.browser_isolation.await_namespace_retirement',return_value=[999999]):
     with self.assertRaises(EffectIndeterminate):dispatch_tool(k,r,'click')
    self.assertEqual(k.frame('click')['state'],'Waiting')
 def test_worker_failure_never_becomes_a_settled_javascript_error(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);e,r=self.make(root)
   with RuntimeLog(root/'ledger') as log:
    k=FrameKernel(log);self.spawn(k,r)
    with patch('branchwrite.browser_capture.render_snapshot',side_effect=ValueError('worker failed without receipt')):
     with self.assertRaises(EffectIndeterminate):dispatch_tool(k,r,'click')
    self.assertEqual(k.frame('click')['state'],'Waiting')
 def test_malformed_runtime_error_wire_records_are_rejected(self):
  original=Executor._capture
  for bad in [None,'error',[True],[''],['x'*1025],['x']*17]:
   def corrupt(*args,**kw):
    out,err,timed,limited,other=original(*args,**kw);head,sep,png=out.partition(b'\n');value=json.loads(head);value['runtime_errors']=bad
    return json.dumps(value).encode()+sep+png,err,timed,limited,other
   with self.subTest(bad=str(bad)[:50]),patch.object(Executor,'_capture',side_effect=corrupt):
    with self.assertRaisesRegex(ValueError,'runtime error'):render_snapshot(b'<p>clean</p>',self.browser())
 def test_failed_canonical_publication_keeps_original_intent_unresolved(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);e,r=self.make(root)
   with RuntimeLog(root/'ledger') as log:
    k=FrameKernel(log);self.spawn(k,r)
    with patch.object(log,'put_artifact',side_effect=OSError('injected canonical publication failure')):
     with self.assertRaises(EffectIndeterminate) as raised:dispatch_tool(k,r,'click')
    # Publication follows execution: the typed contract retains the original
    # operation and I/O cause. It must never look like a safe pre-effect retry.
    self.assertIsInstance(raised.exception.__cause__,OSError)
    self.assertIn('injected canonical publication failure',str(raised.exception.__cause__))
    self.assertEqual(raised.exception.operation_id,k.frame('click')['dispatch'][0])
    self.assertEqual(raised.exception.plan_sha256,k.frame('click')['inputs'][0])
    self.assertEqual(k.frame('click')['state'],'Waiting')
    with patch.object(r,'execute',side_effect=AssertionError('must not resend')):
     with self.assertRaises(ReconciliationRequired) as resumed:dispatch_tool(k,r,'click')
    self.assertEqual(resumed.exception.operation_id,raised.exception.operation_id)
 def test_direct_executor_raises_typed_error_with_complete_capture(self):
  from branchwrite.execution import BrowserExecutionError
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);e,r=self.make(root)
   with self.assertRaises(BrowserExecutionError) as raised:
    e.interact_page('direct-error',r._grant,'index.html',hashlib.sha256(PAGE).hexdigest(),[dict(kind='click',target='inc',value='')])
   capture=raised.exception.capture
   self.assertEqual(list(e.artifacts.iterdir()),[])
   self.assertTrue(capture.runtime_errors);self.assertTrue(capture.isolation['worker_exited'])
   self.assertTrue(capture.png.startswith(b'\x89PNG'))
 def test_typed_error_cannot_claim_unproven_cleanup(self):
  import dataclasses
  from branchwrite.execution import BrowserExecutionError
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);e,r=self.make(root)
   with self.assertRaises(BrowserExecutionError) as raised:
    e.interact_page('direct-error',r._grant,'index.html',hashlib.sha256(PAGE).hexdigest(),[dict(kind='click',target='inc',value='')])
   capture=raised.exception.capture
   bad=dataclasses.replace(capture,isolation=dict(capture.isolation,worker_exited=False))
   error=raised.exception
   with self.assertRaisesRegex(ValueError,'settled'):
    BrowserExecutionError(bad,executor=e,operation_id=error.operation_id,source_path=error.source_path,source_bytes=error.source_bytes,assets=error.assets,elapsed_seconds=error.elapsed_seconds)
 def test_failed_capture_cannot_publish_through_foreign_executor_or_operation(self):
  from branchwrite.execution import BrowserExecutionError
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);e,r=self.make(root)
   with self.assertRaises(BrowserExecutionError) as raised:
    e.interact_page('original',r._grant,'index.html',hashlib.sha256(PAGE).hexdigest(),[dict(kind='click',target='inc',value='')])
   other=Executor.create(e.source,root/'other',browser=self.browser())
   with self.assertRaisesRegex(ValueError,'another operation or world'):other._publish_browser_error(raised.exception,'original','index.html')
   with self.assertRaisesRegex(ValueError,'another operation or world'):e._publish_browser_error(raised.exception,'different','index.html')
   self.assertEqual(list(e.artifacts.iterdir()),[]);self.assertEqual(list(other.artifacts.iterdir()),[])
if __name__=='__main__':unittest.main()
