"""Domain CLI/session plumbing; fixture driver is not live model evidence."""
import json,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
from branchwrite.interactive_session import SessionService
from test_interactive_session import FixtureDriver

class InteractiveDomainTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.project=self.root/'project';self.project.mkdir();self.state=self.root/'session';self.driver=FixtureDriver();self.output=[]
  self.connection=dict(endpoint_url='http://127.0.0.1:8099',endpoint_pin='a'*64,model_contract_id='b'*64,execution_profile_id='c'*64,eos_tokens=[2])
  self.cad=dict(python='/operator/cad/bin/python',osmesa='/operator/osmesa',timeout=60,requirements=json.loads((Path(__file__).parents[1]/'acceptance/cad/plate-v1.json').read_text()))
  self.blender=dict(distribution='/operator/blender',mcp_python='/operator/mcp/bin/python',timeout=120,require_animation=True)
 def open(self,**options):
  service=SessionService(self.project,self.state,self.connection,runner=self.driver,**options);service.start(self.output.append);self.addCleanup(service.close);return service
 def finished(self,service,count):
  end=time.monotonic()+10
  while time.monotonic()<end:
   rows=service.snapshot.get('history',[])
   if len(rows)>=count and rows[-1].get('result') is not None and not service.running:return rows
   if service.snapshot.get('needs_recovery'):self.fail(str(service.snapshot))
   time.sleep(.02)
  self.fail(str(service.snapshot))
 def test_cad_work_keeps_fixed_requirements_and_caller_cannot_mutate_them(self):
  expected=json.loads(json.dumps(self.cad));service=self.open(cad=self.cad)
  self.cad['requirements']['width']=999
  service.submit('Build the required plate',mode='work',kind='send');self.finished(service,1)
  cfg=self.driver.calls[0][1]['config'];self.assertEqual(cfg['cad'],expected);self.assertTrue(cfg['verification']['cad'])
 def test_blender_work_uses_same_worker_and_plan_has_no_domain_execution(self):
  service=self.open(blender=self.blender)
  service.submit('Make the robot scene',mode='work',kind='send');self.finished(service,1)
  self.assertEqual(self.driver.calls[0][1]['config']['blender'],self.blender)
  service.submit('Explain the scene',mode='plan',kind='send');self.finished(service,2)
  cfg=self.driver.calls[-1][1]['config'];self.assertNotIn('blender',cfg);self.assertNotIn('cad',cfg);self.assertTrue(cfg['verification']['read_only'])
 def test_conflicting_domains_reject_before_session_state_creation(self):
  with self.assertRaises(ValueError):SessionService(self.project,self.state,self.connection,cad=self.cad,blender=self.blender)
  self.assertFalse(self.state.exists())
 def test_cli_session_exposes_operator_domain_configuration(self):
  from branchwrite.__main__ import main
  with patch('branchwrite.interactive_cli.run',return_value=0) as run:
   self.assertEqual(main(['session',str(self.project),'--cad-config','/operator/cad.json']),0)
   self.assertEqual(run.call_args.kwargs['cad_config'],Path('/operator/cad.json'))
 def test_saved_exports_are_visible_and_survive_session_reopen(self):
  class ExportDriver(FixtureDriver):
   def __call__(self,*args):
    result=super().__call__(*args);result['exports']=[dict(name='scene.blend',path='/saved/immutable/scene',sha256='d'*64,bytes=128,media_type='application/x-blender',source_id='e'*64,tool_frame='test-frame')];return result
  self.driver=ExportDriver();service=self.open(blender=self.blender)
  service.submit('Build the scene',mode='work',kind='send');rows=self.finished(service,1)
  self.assertEqual(rows[0]['result']['exports'][0]['name'],'scene.blend')
  self.assertTrue(any('/saved/immutable/scene' in line for line in self.output))
  service.close();reopened=self.open(blender=self.blender)
  end=time.monotonic()+5
  while not reopened.snapshot.get('history') and time.monotonic()<end:time.sleep(.02)
  self.assertEqual(reopened.snapshot['history'][0]['result']['exports'],rows[0]['result']['exports'])

 def test_recovery_uses_original_domain_launch_without_regranting_new_work(self):
  self.driver.fail_once=True;service=self.open(cad=self.cad)
  service.submit('Build the plate',mode='work',kind='send')
  end=time.monotonic()+10
  while not service.snapshot.get('needs_recovery') and time.monotonic()<end:time.sleep(.02)
  self.assertTrue(service.snapshot.get('needs_recovery'));first=self.driver.calls[0]
  service.close();reopened=self.open()
  end=time.monotonic()+10
  while not reopened.snapshot.get('needs_recovery') and time.monotonic()<end:time.sleep(.02)
  self.assertTrue(reopened.snapshot.get('needs_recovery'))
  reopened.submit('continue',mode='continue',kind='queue')
  end=time.monotonic()+10
  while time.monotonic()<end:
   rows=reopened.snapshot.get('history',[])
   if rows and rows[0].get('result') is not None and not reopened.running:break
   time.sleep(.02)
  self.assertIsNotNone(reopened.snapshot['history'][0]['result']);self.assertFalse(reopened.snapshot['needs_recovery'])
  self.assertEqual(self.driver.calls[1],first)
  self.assertEqual(self.driver.calls[1][1]['config']['cad'],self.cad)

 def test_reopen_with_new_domain_preserves_files_tip_and_previous_launch(self):
  service=self.open(cad=self.cad)
  service.submit('Build the plate',mode='work',kind='send');rows=self.finished(service,1)
  first=rows[0]['result'];first_launch=json.loads(json.dumps(self.driver.calls[0][1]))
  (self.project/'model.py').write_text('# accepted earlier CAD source\n')
  service.close();reopened=self.open(blender=self.blender)
  reopened.submit('Build a separate scene',mode='work',kind='send');rows=self.finished(reopened,2)
  launch=self.driver.calls[1][1];cfg=launch['config']
  self.assertEqual(cfg['blender'],self.blender);self.assertNotIn('cad',cfg)
  self.assertEqual(launch['fork']['snapshot'],first['context']['tip'])
  self.assertEqual(launch['fork']['source_branch'],first['context']['branch'])
  self.assertEqual((Path(cfg['source'])/'model.py').read_text(),'# accepted earlier CAD source\n')
  self.assertEqual((self.project/'model.py').read_text(),'# accepted earlier CAD source\n')
  self.assertEqual(self.driver.calls[0][1],first_launch,'new domain cannot rewrite an admitted launch')
  self.assertEqual(rows[0]['result'],first)
