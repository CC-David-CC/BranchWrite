"""Real subprocess CLI workflow execution; no model/GPU claim."""
import json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
class RunCliTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.base=Path(self.temp.name)
  self.source=self.base/'source';self.source.mkdir();(self.source/'tests').mkdir();(self.source/'tests/__init__.py').write_text('')
  (self.source/'tests/test_new.py').write_text('import unittest\nfrom pathlib import Path\nclass TestNew(unittest.TestCase):\n def test_new(self): self.assertEqual(Path("new.txt").read_text(),"made")\n')
  self.state=self.base/'state';self.program=self.base/'job.bw';self.config=self.base/'host.json'
  self.cfg=dict(schema=1,source=str(self.source),run_id='cli-run',grant=dict(edit_paths=[],create_paths=['new.txt'],read_paths=[],allow_tests=True),bindings={},profiles={})
 def write(self,source):self.program.write_text(source);self.config.write_text(json.dumps(self.cfg))
 def cli(self,*args):
  return subprocess.run([sys.executable,'-B','-m','branchwrite',*args],capture_output=True,text=True,timeout=20)
 def test_one_command_real_create_test_finish_and_idempotent_second_process(self):
  self.cfg['bindings']={name:dict(type='ToolProposal',value=json.dumps(dict(tool=tool,arguments=args))) for name,tool,args in [('creation','create_file',dict(path='new.txt',content='made')),('test','run_tests',dict(suite='unit')),('done','finish',dict(answer='done'))]}
  self.write('FLOW job\nPLAN p from=creation against=world -> plan\nACT a plan=plan\nPLAN t from=test against=world -> plan\nACT tests plan=plan\nPLAN f from=done against=world -> plan\nACT finish plan=plan -> outcome\nVERIFY v input=outcome contract=unit-tests-and-finish -> verified\nEND\n')
  args=['run',str(self.program),'--config',str(self.config),'--state',str(self.state)]
  first=self.cli(*args);self.assertEqual(first.returncode,0,first.stderr);report=json.loads(first.stdout);self.assertTrue(report['verified'])
  self.assertEqual((self.state/'world/workspace/new.txt').read_bytes(),b'made');self.assertFalse((self.source/'new.txt').exists())
  before=(self.state/'ledger/events.bwl').read_bytes() if (self.state/'ledger/events.bwl').exists() else tuple((q.name,q.read_bytes()) for q in (self.state/'ledger').iterdir() if q.is_file())
  second=self.cli(*args);self.assertEqual(second.returncode,0,second.stderr);self.assertEqual(json.loads(second.stdout),report)
  after=(self.state/'ledger/events.bwl').read_bytes() if (self.state/'ledger/events.bwl').exists() else tuple((q.name,q.read_bytes()) for q in (self.state/'ledger').iterdir() if q.is_file())
  self.assertEqual(before,after)
 def test_step_then_new_process_run_resumes_same_ledger(self):
  self.write('FLOW job\nTEXT task\n|Hello\nEND\nEND\n')
  stepped=self.cli('step',str(self.program),'--config',str(self.config),'--state',str(self.state));self.assertEqual(stepped.returncode,3,stepped.stderr)
  finished=self.cli('run',str(self.program),'--config',str(self.config),'--state',str(self.state));self.assertEqual(finished.returncode,1,finished.stderr)
  self.assertEqual(json.loads(finished.stdout)['status'],'complete');self.assertFalse(json.loads(finished.stdout)['verified'])
 def test_unsupported_program_refused_before_creating_state(self):
  self.write('FLOW job\nSAVE x input=missing name=later\nEND\n')
  result=self.cli('run',str(self.program),'--config',str(self.config),'--state',str(self.state));self.assertEqual(result.returncode,2,result.stderr);self.assertFalse(self.state.exists())
 def test_config_change_on_restart_refused(self):
  self.write('FLOW job\nTEXT task\n|Hello\nEND\nEND\n')
  first=self.cli('step',str(self.program),'--config',str(self.config),'--state',str(self.state));self.assertEqual(first.returncode,3,first.stderr)
  self.cfg['bindings']['extra']=dict(type='Text',value='changed');self.config.write_text(json.dumps(self.cfg))
  result=self.cli('run',str(self.program),'--config',str(self.config),'--state',str(self.state));self.assertEqual(result.returncode,2,result.stderr)
 def test_config_cannot_supply_api_key_or_extra_unknown_grants(self):
  self.cfg['api_key']='should-never-be-in-manifest';self.write('FLOW job\nEND\n')
  result=self.cli('run',str(self.program),'--config',str(self.config),'--state',str(self.state));self.assertEqual(result.returncode,2);self.assertFalse(self.state.exists());self.assertNotIn('should-never-be-in-manifest',result.stderr)
 def test_state_symlink_refused(self):
  target=self.base/'target';target.mkdir();self.state.symlink_to(target,target_is_directory=True);self.write('FLOW job\nEND\n')
  result=self.cli('run',str(self.program),'--config',str(self.config),'--state',str(self.state));self.assertEqual(result.returncode,2);self.assertEqual(list(target.iterdir()),[])

class HttpRunCliTests(unittest.TestCase):
 def test_real_subprocess_model_http_edit_test_finish(self):
  import test_cow_client_flow as fixture
  from collections import defaultdict
  from serve.test_cow_presentation_flow import FlowModel
  class DiscoveredFlowModel(FlowModel):
   """Same byte/controller fixture, with current discovery's explicit IDs."""
   def __init__(self,*args):
    super().__init__(*args)
    self.profile.update(model_contract_id='a'*64,execution_profile_id='b'*64)
  case=fixture.CowClientFlowTests();self.addCleanup(case.doCleanups)
  case.model_factory=DiscoveredFlowModel
  case.connection_info=dict(model_contract_id='a'*64,execution_profile_id='b'*64,eos_tokens=[299])
  case.setUp()
  client=case._client('http','run-cli');namespace=client.create_namespace('CLI model','cli-model-ns')['namespace_id']
  client.load_context('cli-model',namespace,[dict(role='system',content='Choose registered tools.')],'cli-model-root')
  root=Path(case.temp.name);source=root/'source';source.mkdir();(source/'data.txt').write_bytes(b'original\n')
  (source/'tests').mkdir();(source/'tests/__init__.py').write_text('');(source/'tests/test_task.py').write_text('import unittest\nfrom pathlib import Path\nclass T(unittest.TestCase):\n def test_bytes(self): self.assertEqual(Path("data.txt").read_bytes(),b"correct\\n")\n')
  decisions=[dict(tool='read_file',arguments=dict(path='data.txt')),dict(tool='replace',arguments=dict(path='data.txt',before='original',after='correct')),dict(tool='run_tests',arguments=dict(suite='unit')),dict(tool='finish',arguments=dict(answer='done'))]
  stream=iter(tuple(json.dumps(x).encode())+(299,) for x in decisions);case.models[0].plans=defaultdict(lambda:next(stream))
  program=root/'work.bw';program.write_text('FLOW job\nTEXT task\n|Change data.txt to correct and run tests.\nEND\nREPEAT attempts max=8 until=verified exhausted=stop\nEXPAND decide from=current task=task profile=control -> proposed\nPLAN p from=proposed against=world -> plan\nACT a plan=plan -> outcome\nTRANSFORM source input=proposed contract=cow-source -> current\nTRANSFORM feedback input=outcome contract=tool-feedback -> task\nVERIFY check input=outcome contract=unit-tests-and-finish -> verified\nEND\nEND\n')
  cfg=dict(schema=1,source=str(source),run_id='http-cli',grant=dict(edit_paths=['data.txt'],read_paths=['data.txt'],create_paths=[],allow_tests=True),bindings={},profiles=dict(control=dict(request_tokens=1024)),cow=dict(endpoint_url=case.base_url,endpoint_pin='flow-model-free',model_contract_id='a'*64,execution_profile_id='b'*64,eos_tokens=[299],branch='cli-model',mode='ask'))
  config=root/'host.json';config.write_text(json.dumps(cfg));state=root/'run'
  command=[sys.executable,'-B','-m','branchwrite','run',str(program),'--config',str(config),'--state',str(state)]
  result=subprocess.run(command,capture_output=True,text=True,env={**os.environ,'BW_COW_API_KEY':'cpu-flow-secret'},timeout=20)
  self.assertEqual(result.returncode,0,result.stderr);self.assertTrue(json.loads(result.stdout)['verified']);self.assertEqual(len(case.trace),4)
  before=list(case.trace)
  # Closing the HTTP listener proves a completed CLI restart reads locally.
  # No new head lookup/rebase or model call is allowed.
  case._stop_server()
  again=subprocess.run(command,capture_output=True,text=True,env={**os.environ,'BW_COW_API_KEY':'cpu-flow-secret'},timeout=20)
  self.assertEqual(again.returncode,0,again.stderr);self.assertEqual(json.loads(again.stdout),json.loads(result.stdout));self.assertEqual(case.trace,before)
  self.assertNotIn(b'cpu-flow-secret',b''.join(q.read_bytes() for q in state.rglob('*') if q.is_file()))
