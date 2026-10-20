"""CLI and canonical verification need both host-granted viewport observations."""
import dataclasses,hashlib,io,json,os,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from branchwrite.browser_capture import BrowserConfig
from branchwrite.execution import Executor,Grant,ToolRejected
from branchwrite.tool_registry import ToolRegistry,FileObservation
from branchwrite.run_cli import _config
from branchwrite.records import RuntimeLog,Artifact,decode,encode
from branchwrite.kernel import FrameKernel
from branchwrite.interpreter import Interpreter,Value
MENU=(('desktop',640,480),('phone',360,640))
class ViewportCliTests(unittest.TestCase):
 def setUp(self):
  self.pack=Path(os.environ['BW_BASIC_LOOP_PACK']);self.check=self.pack/'protected/checks.py';self.check_bytes=self.check.read_bytes();self.starter=self.pack/'fixtures/starter/H12'
  self.html=(self.starter/'index.html').read_bytes();self.css=(self.starter/'style.css').read_bytes();self.good_css=self.css.replace(b'main { width: 900px; }',b'main { width: 100%; }');self.assertNotEqual(self.css,self.good_css)
  self.executable=Path(os.environ['BW_BROWSER_EXECUTABLE'])
 def make(self,root,good=True):
  source=root/'source';shutil.copytree(self.starter,source)
  if good:(source/'style.css').write_bytes(self.good_css)
  e=Executor.create(source,root/'world',browser=BrowserConfig(self.executable,viewports=MENU))
  g=Grant(('index.html','style.css','app.js'),False,read_paths=('index.html','style.css','app.js','assets/sample.png'),capture_paths=('index.html',),interact_paths=('index.html',),asset_paths=('style.css','app.js','assets/sample.png'))
  return e,ToolRegistry(e,g),g
 def proposal(self,name,interact=True):
  args=dict(path='index.html')
  if interact:args['actions']=[dict(kind='click',target='increment',value=''),dict(kind='fill',target='name',value='Ada'),dict(kind='click',target='greet',value='')]
  args['viewport']=name
  return dict(tool='interact_page' if interact else 'capture_page',arguments=args)
 def spec(self):
  return dict(schema=1,interactive_captures=[dict(path='index.html',width=w,height=h) for _,w,h in MENU],inspection=dict(path=str(self.check),sha256=hashlib.sha256(self.check_bytes).hexdigest(),target='H12'))
 def config(self,e,g):
  return dict(schema=1,source=str(e.source),run_id='h12-viewports',grant={k:list(getattr(g,k)) for k in ['edit_paths','create_paths','read_paths','capture_paths','interact_paths','asset_paths']},browser=dict(executable=str(self.executable),width=640,height=480,timeout=15,viewports={name:[w,h] for name,w,h in MENU}),profiles={},verification=self.spec(),bindings={})
 def program(self,include_phone=True):
  steps=[('r','read_html'),('rc','read_css'),('d','desktop')]
  if include_phone:steps.append(('m','phone'))
  steps.append(('f','finish'));lines=['FLOW responsive']
  for label,binding in steps:lines+=['PLAN '+label+' from='+binding+' against=world -> p','ACT '+label+' plan=p -> outcome']
  return '\n'.join(lines+['VERIFY v input=outcome contract=interactive-page-inspection-and-finish -> verified','END',''])
 def proposals(self):
  return dict(read_html=dict(tool='read_file',arguments=dict(path='index.html')),read_css=dict(tool='read_file',arguments=dict(path='style.css')),desktop=self.proposal('desktop'),phone=self.proposal('phone'),finish=dict(tool='finish',arguments=dict(answer='observed both viewports')))
 def test_cli_config_admits_only_bounded_named_host_geometry(self):
  with tempfile.TemporaryDirectory() as t:
   e,r,g=self.make(Path(t));cfg=self.config(e,g);cfg['grant']['allow_tests']=False
   self.assertEqual(_config(json.dumps(cfg))['browser']['viewports'],{'desktop':[640,480],'phone':[360,640]})
   for bad in [None,[],{'phone':[360,640]},{'desktop':[640,480],'phone':[True,640]},{'desktop':[640,480],'phone':[360,640],'dup':[360,640]}]:
    cfg['browser']['viewports']=bad
    with self.subTest(bad=bad),self.assertRaises(ValueError):_config(json.dumps(cfg))
 def test_schema_requires_named_viewport_and_describes_actual_geometry(self):
  with tempfile.TemporaryDirectory() as t:
   e,r,g=self.make(Path(t))
   for tool in ['capture_page','interact_page']:
    variant=next(v for v in r.model_schema()['oneOf'] if v['properties']['tool']['enum']==[tool])
    args=variant['properties']['arguments'];self.assertIn('viewport',args['required'])
    self.assertEqual(args['properties']['viewport']['enum'],['desktop','phone'])
    self.assertIn('360',args['properties']['viewport']['description'])
   q=self.proposal('phone');q['arguments'].pop('viewport')
   with self.assertRaises(ToolRejected):r.parse(json.dumps(q))
   with self.assertRaises(ToolRejected):r.parse(json.dumps(self.proposal('unknown')))
 def test_actual_plan_and_receipt_bind_phone_geometry(self):
  with tempfile.TemporaryDirectory() as t:
   e,r,g=self.make(Path(t));plan=r.freeze(json.dumps(self.proposal('phone')),observations=(FileObservation(r.world,'index.html',hashlib.sha256(self.html).hexdigest()),))
   self.assertEqual(decode(plan.data)[4]['viewport'],'phone');out=r.execute(plan,'phone')
   self.assertEqual(out.metadata['viewport_name'],'phone');self.assertEqual(out.metadata['viewport'],(360,640))
   with Image.open(io.BytesIO(out.image.read_bytes())) as im:self.assertEqual(im.size,(360,640))
   self.assertIn(b'Hello, Ada!',out.stdout)
 def test_menu_geometry_changes_identity_and_stales_existing_plan(self):
  with tempfile.TemporaryDirectory() as t:
   e,r,g=self.make(Path(t));plan=r.freeze(json.dumps(self.proposal('phone')),observations=(FileObservation(r.world,'index.html',hashlib.sha256(self.html).hexdigest()),))
   e._browser=BrowserConfig(self.executable,viewports=(('desktop',640,480),('phone',400,640)))
   updated=ToolRegistry(e,g);self.assertNotEqual(r.identity,updated.identity)
   with patch('branchwrite.browser_capture.render_snapshot') as render:
    with self.assertRaisesRegex(ToolRejected,'configuration'):r.execute(plan,'stale')
   render.assert_not_called()
 def run_direct(self,root,include_phone=True,forge=False):
  e,r,g=self.make(root)
  with RuntimeLog(root/'ledger') as log:
   runtime=Interpreter(FrameKernel(log),r,verification=self.spec());runtime.start(self.program(include_phone),{k:Value('ToolProposal',json.dumps(v)) for k,v in self.proposals().items()})
   original=r.execute
   def execute(*args):
    out=original(*args)
    if forge and out.tool=='interact_page' and out.metadata['viewport_name']=='phone':
     out=dataclasses.replace(out,details=encode(dict(out.metadata,viewport_name='desktop')))
    return out
   with patch.object(r,'execute',side_effect=execute):result=runtime.run()
  return result.value
 def test_missing_phone_observation_cannot_finish(self):
  with tempfile.TemporaryDirectory() as t:self.assertFalse(self.run_direct(Path(t),False)['verified'])
 def test_relabelled_phone_receipt_cannot_finish(self):
  with tempfile.TemporaryDirectory() as t:self.assertFalse(self.run_direct(Path(t),forge=True)['verified'])
 def test_exact_duplicate_and_ungranted_geometry_remain_rejected(self):
  with tempfile.TemporaryDirectory() as t:
   e,r,g=self.make(Path(t))
   spec=self.spec();spec['interactive_captures'].append(dict(spec['interactive_captures'][0]))
   with RuntimeLog(Path(t)/'duplicate-ledger') as log:
    with self.assertRaises(ValueError):Interpreter(FrameKernel(log),r,verification=spec)
   spec=self.spec();spec['interactive_captures'][1]['width']=361
   with RuntimeLog(Path(t)/'ungranted-ledger') as log:
    with self.assertRaises(ValueError):Interpreter(FrameKernel(log),r,verification=spec)
 def test_real_cli_two_viewports_original_checks_and_offline_reopen(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);e,r,g=self.make(root);cfg=self.config(e,g);cfg['grant']['allow_tests']=False
   cfg['bindings']={k:dict(type='ToolProposal',value=json.dumps(v)) for k,v in self.proposals().items()}
   config=root/'host.json';config.write_text(json.dumps(cfg));program=root/'job.bw';program.write_text(self.program());state=root/'run'
   cmd=[sys.executable,'-B','-m','branchwrite','run',str(program),'--config',str(config),'--state',str(state)]
   first=subprocess.run(cmd,capture_output=True,text=True,timeout=45);self.assertEqual(first.returncode,0,first.stderr);self.assertTrue(json.loads(first.stdout)['verified'])
   with RuntimeLog(state/'ledger') as log:
    k=FrameKernel(log);result=decode(log.read_artifact(Artifact(*k.frame('program')['result'])))[2]
    v=result['bindings']['verified'][1];self.assertEqual(len(v['captures']),2);self.assertEqual(len(v['inspections']),2)
    self.assertEqual({(v['width'],v['height']) for v in v['captures']},{(640,480),(360,640)})
    self.assertTrue(all(v['same_capture'] and v['checker']['status']=='PASS' for v in v['inspections']))
   again=subprocess.run(cmd,capture_output=True,text=True,timeout=45);self.assertEqual(again.returncode,0,again.stderr);self.assertEqual(first.stdout,again.stdout)
   self.assertEqual((e.source/'style.css').read_bytes(),self.good_css);self.assertEqual(self.check.read_bytes(),self.check_bytes)
 def test_two_static_viewports_replay_and_pass_unchanged_checks(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);e,r,g=self.make(root);spec=self.spec()
   spec=dict(schema=1,inspected_captures=spec['interactive_captures'],inspection=spec['inspection'])
   proposals=self.proposals()
   for name in ['desktop','phone']:proposals[name]=self.proposal(name,False)
   program=self.program().replace('interactive-page-inspection-and-finish','page-inspection-and-finish')
   with RuntimeLog(root/'ledger') as log:
    runtime=Interpreter(FrameKernel(log),r,verification=spec);runtime.start(program,{k:Value('ToolProposal',json.dumps(v)) for k,v in proposals.items()});out=runtime.run().value
    self.assertTrue(out['verified']);checks=out['bindings']['verified'][1]
    self.assertEqual(len(checks['inspections']),2);self.assertTrue(all(c['same_capture'] and c['status']=='PASS' for c in checks['inspections']))
 def test_resource_change_between_sizes_invalidates_earlier_capture(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);e,r,g=self.make(root)
   with RuntimeLog(root/'ledger') as log:
    k=FrameKernel(log);runtime=Interpreter(k,r,verification=self.spec());runtime.start(self.program(),{k:Value('ToolProposal',json.dumps(v)) for k,v in self.proposals().items()})
    captured=False
    for _ in range(100):
     runtime.step()
     for f in k.frames():
      if f['state']=='Closed' and f['contract']==('ToolOutcome','record'):
       v=decode(log.read_artifact(Artifact(*f['result'])))[2]
       if v['tool']=='interact_page' and v['disposition']=='captured' and v['details']['viewport_name']=='desktop':captured=True
     if captured:break
    self.assertTrue(captured);(e.workspace/'style.css').write_bytes(self.good_css+b'\n/* same pixels,new resource version */')
    self.assertFalse(runtime.run().value['verified'])
 def test_generic_prefix_teaches_each_requested_viewport_without_changing_default(self):
  from branchwrite.coding_defaults import system_prefix
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);e,r,g=self.make(root)
   self.assertIn('each requested viewport',system_prefix(r.model_schema()))
   legacy=ToolRegistry(Executor.create(e.source,root/'legacy',browser=BrowserConfig(self.executable)),g)
   self.assertNotIn('each requested viewport',system_prefix(legacy.model_schema()))
   for variant in legacy.model_schema()['oneOf']:
    self.assertNotIn('viewport',variant['properties']['arguments']['properties'])
if __name__=='__main__':unittest.main()
