"""Real tool/CLI interaction receipts; scripted proposals, not autonomous GPU evidence."""
import hashlib,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from branchwrite.browser_capture import BrowserConfig,PageAction
from branchwrite.execution import Executor,Grant,ToolRejected
from branchwrite.tool_registry import ToolRegistry,FileObservation,EffectIndeterminate
from branchwrite.records import RuntimeLog,Artifact,decode
from branchwrite.kernel import FrameKernel,ResultContract
from branchwrite.tool_dispatch import admit_tool,dispatch_tool,ReconciliationRequired
from branchwrite.run_cli import _config
from tests.test_page_actions import PAGE
class InteractToolTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
  self.source=self.root/'source';self.source.mkdir();(self.source/'index.html').write_bytes(PAGE)
  self.browser=BrowserConfig(Path(os.environ['BW_BROWSER_EXECUTABLE']))
  self.executor=Executor.create(self.source,self.root/'world',browser=self.browser)
  self.sha=hashlib.sha256(PAGE).hexdigest();self.actions=[dict(kind='click',target='inc',value='')]
 def grant(self):return Grant((),False,read_paths=('index.html',),capture_paths=('index.html',),interact_paths=('index.html',))
 def registry(self):return ToolRegistry(self.executor,self.grant())
 def proposal(self,actions=None):return json.dumps(dict(tool='interact_page',arguments=dict(path='index.html',actions=self.actions if actions is None else actions)))
 def plan(self,r):return r.freeze(self.proposal(),observations=(FileObservation(r.world,'index.html',self.sha),))
 def test_capture_grant_does_not_expose_or_allow_interactions(self):
  r=ToolRegistry(self.executor,Grant((),False,read_paths=('index.html',),capture_paths=('index.html',)))
  self.assertNotIn('interact_page',r.model_gbnf())
  with self.assertRaises(ToolRejected):r.freeze(self.proposal())
 def test_interact_grant_requires_capture_and_read(self):
  for kwargs in [dict(read_paths=('index.html',)),dict(capture_paths=('index.html',)),{}]:
   with self.assertRaises(ToolRejected):Grant((),False,interact_paths=('index.html',),**kwargs)
 def test_direct_executor_without_interact_grant_refuses_before_browser(self):
  with patch('branchwrite.browser_capture.render_snapshot') as render:
   with self.assertRaises(ToolRejected):self.executor.interact_page('no',Grant((),False,capture_paths=('index.html',)),'index.html',self.sha,self.actions)
  render.assert_not_called()
 def test_hidden_actions_in_static_browser_config_are_rejected(self):
  browser=BrowserConfig(self.browser.executable,actions=(PageAction('click','inc',''),))
  e=Executor.create(self.source,self.root/'other',browser=browser)
  with patch('branchwrite.browser_capture.render_snapshot') as render:
   with self.assertRaises(ToolRejected):e.capture_page('hidden',Grant((),False,capture_paths=('index.html',)),'index.html',self.sha)
  render.assert_not_called()
  with self.assertRaises(ToolRejected):ToolRegistry(e,self.grant())
 def test_actual_action_is_bound_to_source_and_plan(self):
  r=self.registry();plan=self.plan(r);self.actions[0]['target']='absent'
  result=r.execute(plan,'real-click')
  self.assertEqual(result.tool,'interact_page');self.assertEqual(result.disposition,'captured')
  self.assertEqual(result.metadata['actions'],[dict(kind='click',target='inc',value='')])
  self.assertIn(b'1',result.stdout);self.assertTrue(result.image.read_bytes().startswith(b'\x89PNG'))
  self.assertEqual(result.observation.sha256,self.sha);self.assertTrue(result.metadata['isolation']['worker_exited'])
  self.assertEqual((self.source/'index.html').read_bytes(),PAGE)
 def test_source_read_witness_is_required(self):
  r=self.registry()
  with self.assertRaisesRegex(ToolRejected,'read'):r.freeze(self.proposal())
 def test_source_changed_after_plan_rejects_before_browser(self):
  r=self.registry();plan=self.plan(r);(self.executor.workspace/'index.html').write_bytes(PAGE+b'changed')
  with patch('branchwrite.browser_capture.render_snapshot') as render:
   with self.assertRaisesRegex(ToolRejected,'stale'):r.execute(plan,'stale')
  render.assert_not_called()
 def test_malformed_and_excessive_recipes_are_rejected_before_execution(self):
  r=self.registry()
  for actions in [[],self.actions*17,[dict(kind='eval',target='inc',value='')],[dict(kind='click',target='inc',value='',extra='x')],dict(kind='click'),[dict(kind='fill',target='name',value='z'*4097)]]:
   with self.subTest(actions=str(actions)[:80]),self.assertRaises(ToolRejected):r.parse(self.proposal(actions))
 def test_schema_exposes_bounded_exact_action_structure(self):
  r=self.registry();schema=r.model_schema();v=next(x for x in schema['oneOf'] if x['properties']['tool']['enum']==['interact_page'])
  action=v['properties']['arguments']['properties']['actions']
  self.assertEqual((action['minItems'],action['maxItems']),(1,16));self.assertEqual(len(action['items']['oneOf']),2)
  for variant in action['items']['oneOf']:
   self.assertFalse(variant['additionalProperties']);self.assertEqual(set(variant['required']),{'kind','target','value'})
 def test_browser_runtime_source_is_bound_to_registry_identity(self):
  original=self.registry().identity
  read=Path.read_bytes
  def changed(path):
   value=read(path)
   return value+b'\\n' if path.name=='browser_worker.py' else value
  with patch.object(Path,'read_bytes',changed):updated=self.registry().identity
  self.assertNotEqual(original,updated)
 def test_after_browser_receipt_failure_is_not_resent(self):
  r=self.registry()
  with RuntimeLog(self.root/'ledger') as log:
   k=FrameKernel(log);k.create_root('root','attempt',log.put_artifact(b'FLOW root\nEND\n'),log.put_artifact(b'input'),ResultContract('Root','record'))
   admit_tool(k,r,'root',expected_epoch=0,child_id='click',attempt_id='click-attempt',slot='out',next_pc=1,proposal=self.proposal(),observations=(FileObservation(r.world,'index.html',self.sha),))
   with patch.object(self.executor,'_artifact',side_effect=OSError('injected publication failure')):
    with self.assertRaises(EffectIndeterminate):dispatch_tool(k,r,'click')
   self.assertEqual(k.frame('click')['state'],'Waiting')
   with patch.object(r,'execute',side_effect=AssertionError('must not resend')):
    with self.assertRaises(ReconciliationRequired):dispatch_tool(k,r,'click')
 def config(self):
  return dict(schema=1,source=str(self.source),run_id='interaction-cli',grant=dict(edit_paths=[],create_paths=[],read_paths=['index.html'],capture_paths=['index.html'],interact_paths=['index.html'],allow_tests=False),
   browser=dict(executable=str(self.browser.executable),width=640,height=480,timeout=15),profiles={},bindings={})
 def test_cli_grant_admission_is_explicit(self):
  cfg=self.config();self.assertIn('interact_paths',_config(json.dumps(cfg))['grant'])
  cfg['grant']['capture_paths']=[]
  with self.assertRaisesRegex(ValueError,'capture'):_config(json.dumps(cfg))
 def test_real_cli_keeps_action_receipt_image_feedback_and_offline_reopen(self):
  cfg=self.config()
  proposals=dict(read=dict(tool='read_file',arguments=dict(path='index.html')),click=json.loads(self.proposal()),finish=dict(tool='finish',arguments=dict(answer='observed actual click')))
  cfg['bindings']={k:dict(type='ToolProposal',value=json.dumps(v)) for k,v in proposals.items()}
  cfg['verification']=dict(schema=1,files=[dict(path='index.html',sha256=self.sha)])
  program='FLOW browse\nPLAN r from=read against=world -> plan\nACT r plan=plan\nPLAN c from=click against=world -> plan\nACT c plan=plan -> outcome\nTRANSFORM feedback input=outcome contract=tool-feedback -> feedback\nPLAN f from=finish against=world -> plan\nACT f plan=plan -> done\nVERIFY v input=done contract=file-readback-and-finish -> verified\nEND\n'
  f=self.root/'host.json';f.write_text(json.dumps(cfg));workflow=self.root/'browse.bw';workflow.write_text(program)
  state=self.root/'run';cmd=[sys.executable,'-B','-m','branchwrite','run',str(workflow),'--config',str(f),'--state',str(state)]
  first=subprocess.run(cmd,capture_output=True,text=True,timeout=30);self.assertEqual(first.returncode,0,first.stderr)
  result=json.loads(first.stdout);self.assertEqual(len(result['artifacts']),1)
  with RuntimeLog(state/'ledger') as log:
   k=FrameKernel(log);outcomes=[decode(log.read_artifact(Artifact(*f['result'])))[2] for f in k.frames() if f['contract']==('ToolOutcome','record')]
   click=next(v for v in outcomes if v['tool']=='interact_page');self.assertEqual(click['details']['actions'],self.actions)
   self.assertEqual(hashlib.sha256(log.read_artifact(Artifact(*click['image']))).hexdigest(),result['artifacts'][0]['sha256'])
   root=decode(log.read_artifact(Artifact(*k.frame('program')['result'])))[2]
   feedback=json.loads(root['bindings']['feedback'][1]);self.assertEqual(feedback['capture']['actions'],self.actions);self.assertIn('1',feedback['stdout'])
  again=subprocess.run(cmd,capture_output=True,text=True,timeout=30)
  self.assertEqual(again.returncode,0,again.stderr);self.assertEqual(first.stdout,again.stdout)
if __name__=='__main__':unittest.main()
