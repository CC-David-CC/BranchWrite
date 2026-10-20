"""New coding defaults and actual CLI context bootstrap; CPU fixture scoped."""
import json,os,subprocess,sys,unittest
from pathlib import Path
from branchwrite.coding_defaults import generation_profile,system_prefix,workflow_source
from branchwrite.run_cli import _config
class CodingDefaultsTests(unittest.TestCase):
 def test_explicit_dry_minp_preset_and_thinking_admission(self):
  profile=generation_profile('dry-min-p');self.assertEqual(profile['settings'],dict(temperature=0.7,min_p=0.05,top_k=60,top_p=0.95,dry_multiplier=0.8,dry_base=1.75,dry_allowed_length=2,dry_penalty_last_n=256))
  self.assertEqual(profile['output_format'],'thinking');self.assertEqual(profile['grammar_state'],'BW_TOOLS')
  profile['settings']['temperature']=2;self.assertEqual(generation_profile('dry-min-p')['settings']['temperature'],0.7)
 def test_reusable_prefix_contains_three_examples_and_live_schema(self):
  text=system_prefix({'oneOf':[{'live-schema-marker':True}]})
  self.assertEqual(text.count('## Worked example '),3);self.assertIn('live-schema-marker',text)
  self.assertGreater(len(text),40000);self.assertIn('observation.source_sha256',text)
 def test_default_workflow_is_generic_and_parseable(self):
  from branchwrite.language import parse,render
  source=workflow_source();self.assertEqual(render(parse(source)),source)
  self.assertIn('profile=control',source);self.assertNotIn('calc.py',source)
 def test_omitted_profiles_select_default_but_explicit_profile_is_preserved(self):
  base=dict(schema=1,source='/source',run_id='defaults',grant=dict(edit_paths=[],read_paths=[],create_paths=[],allow_tests=True),bindings={})
  self.assertEqual(_config(json.dumps(base))['profiles']['control'],generation_profile())
  explicit=dict(control=dict(settings=dict(temperature=0),request_tokens=4));base['profiles']=explicit
  self.assertEqual(_config(json.dumps(base))['profiles'],explicit)
 def test_actual_cli_bootstrap_uses_examples_then_completes_and_reopens(self):
  import test_cow_client_flow as fixture
  from collections import defaultdict
  from hashlib import sha256
  case=fixture.CowClientFlowTests();self.addCleanup(case.doCleanups);case.setUp()
  root=Path(case.temp.name);source=root/'source';source.mkdir();(source/'data.txt').write_bytes(b'original\n')
  (source/'tests').mkdir();(source/'tests/__init__.py').write_text('');(source/'tests/test_data.py').write_text('import unittest\nfrom pathlib import Path\nclass T(unittest.TestCase):\n def test_data(self): self.assertEqual(Path("data.txt").read_bytes(),b"correct\\n")\n')
  actions=[dict(tool='read_file',arguments=dict(path='data.txt')),dict(tool='replace',arguments=dict(path='data.txt',before='original',after='correct')),dict(tool='run_tests',arguments=dict(suite='unit')),dict(tool='finish',arguments=dict(answer='done'))]
  stream=iter(tuple(json.dumps(x).encode())+(299,) for x in actions);case.models[0].plans=defaultdict(lambda:next(stream))
  cfg=dict(schema=1,source=str(source),run_id='bootstrap-cli',grant=dict(edit_paths=['data.txt'],read_paths=['data.txt'],create_paths=[],allow_tests=True),bindings=dict(task=dict(type='Text',value='Fix data.txt to correct and test.')),
   # The synthetic CPU fixture is greedy/text only. New default policy is
   # inspected above and tested on real Q4, never falsely simulated here.
   profiles=dict(control=dict(output_format='text',settings=dict(temperature=0),request_tokens=1024)),
   cow=dict(endpoint_url=case.base_url,endpoint_pin='flow-model-free',model_contract_id='flow-model',execution_profile_id='flow-profile',eos_tokens=[299],branch='new-coding',mode='ask',bootstrap='coding'))
  config=root/'host.json';config.write_text(json.dumps(cfg));program=root/'coding.bw';program.write_text(workflow_source());state=root/'run'
  cmd=[sys.executable,'-B','-m','branchwrite','run',str(program),'--config',str(config),'--state',str(state)]
  env={**os.environ,'BW_COW_API_KEY':'cpu-flow-secret'}
  result=subprocess.run(cmd,capture_output=True,text=True,env=env,timeout=30);self.assertEqual(result.returncode,0,result.stderr)
  client=case._client('http','inspect-bootstrap');history=client.history('new-coding');self.assertIn('## Worked example 3',history.messages[0]['text'])
  self.assertTrue(json.loads(result.stdout)['verified']);self.assertEqual(len(case.trace),4)
  case._stop_server();again=subprocess.run(cmd,capture_output=True,text=True,env=env,timeout=30)
  self.assertEqual(again.returncode,0,again.stderr);self.assertEqual(json.loads(again.stdout),json.loads(result.stdout))

 def test_bad_workflow_types_reject_before_bootstrap_prefix_computation(self):
  import test_cow_client_flow as fixture
  case=fixture.CowClientFlowTests();self.addCleanup(case.doCleanups);case.setUp()
  root=Path(case.temp.name);source=root/'source';source.mkdir()
  cfg=dict(schema=1,source=str(source),run_id='bad-bootstrap',grant=dict(edit_paths=[],read_paths=[],create_paths=[],allow_tests=True),bindings={},
   profiles=dict(control=dict(output_format='text',settings=dict(temperature=0),request_tokens=1024)),
   cow=dict(endpoint_url=case.base_url,endpoint_pin='flow-model-free',model_contract_id='flow-model',execution_profile_id='flow-profile',eos_tokens=[299],branch='bad-coding',mode='ask',bootstrap='coding'))
  config=root/'host.json';config.write_text(json.dumps(cfg));program=root/'coding.bw';program.write_text(workflow_source())
  result=subprocess.run([sys.executable,'-B','-m','branchwrite','run',str(program),'--config',str(config),'--state',str(root/'run')],env={**os.environ,'BW_COW_API_KEY':'cpu-flow-secret'},capture_output=True,text=True,timeout=20)
  self.assertEqual(result.returncode,2,result.stderr);self.assertEqual(case.models[0].stats['forward_tokens'],0)
