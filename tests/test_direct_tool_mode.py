"""Explicit direct tool decoding preserves default admission and native grammar."""
import copy,json,tempfile,unittest
from pathlib import Path
from branchwrite.coding_defaults import generation_profile,grammar_registry
from branchwrite.coding_cli import build_launch
from branchwrite.execution import Executor,Grant
from branchwrite.tool_registry import ToolRegistry

class DirectToolModeTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.root=Path(self.temp.name);self.source=self.root/'source';self.source.mkdir()
  (self.source/'a.py').write_text('old')
  self.tools=ToolRegistry(Executor.create(self.source,self.root/'world'),Grant(('a.py',),True,read_paths=('a.py',)))
 def test_default_bytes_and_explicit_standard_remain_identical(self):
  default=generation_profile()
  self.assertEqual(default,generation_profile(thinking_mode='standard'))
  self.assertEqual(default['output_format'],'thinking')
  self.assertEqual(default['grammar_state'],'BW_TOOLS')
  self.assertEqual(default['thinking_ladder'],'standard')
  self.assertNotIn('BW_TOOLS_DIRECT',grammar_registry(self.tools)['states'])
 def test_off_is_explicit_constrained_tools_with_same_sampling_and_budgets(self):
  standard=generation_profile();direct=generation_profile(thinking_mode='off')
  self.assertEqual(direct['output_format'],'constrained')
  self.assertEqual(direct['grammar_state'],'BW_TOOLS_DIRECT')
  self.assertNotIn('thinking_ladder',direct)
  for key in ['settings','request_tokens','max_requests','max_output_tokens']:
   self.assertEqual(direct[key],standard[key])
  for invalid in [None,False,'automatic','on']:
   with self.subTest(invalid=invalid),self.assertRaises(ValueError):generation_profile(thinking_mode=invalid)
 def test_actual_direct_grammar_forks_and_rejects_thinking_prefix(self):
  from test_thinking_grammar import ThinkingTokenizer
  from context_time_travel.grammar_first import GrammarEngine
  from context_time_travel.store import IntegrityError
  tokenizer=ThinkingTokenizer();payload=grammar_registry(self.tools,direct=True)
  direct=payload['states']['BW_TOOLS_DIRECT']
  self.assertEqual(direct,dict(format='gbnf',source=self.tools.model_gbnf()))
  prior=grammar_registry(self.tools)['states']
  self.assertEqual({k:v for k,v in payload['states'].items() if k!='BW_TOOLS_DIRECT'},prior)
  engine=GrammarEngine(tokenizer,payload['states'],[tokenizer.EOS])
  root=engine.start('BW_TOOLS_DIRECT','direct-tools',[],engine.vocab_size);saved=copy.deepcopy(root)
  for action in [dict(tool='read_file',arguments=dict(path='a.py')),dict(tool='finish',arguments=dict(answer='done'))]:
   session=engine.restore(root,[]);history=[]
   for token in json.dumps(action).encode():
    session._consume_selected(token,tokenizer.token_bytes(token),False);history.append(token)
    session=engine.restore(session.current_controller,history)
   self.assertTrue(session.is_complete())
   session._consume_selected(tokenizer.EOS,tokenizer.token_bytes(tokenizer.EOS),True)
   self.assertTrue(session.is_stopped())
  session=engine.restore(root,[])
  with self.assertRaises(IntegrityError):session._consume_selected(ord('<'),b'<',False)
  self.assertEqual(root,saved)
 def test_new_launch_pins_mode_and_does_not_mutate_default_launch(self):
  connection=dict(endpoint_url='http://127.0.0.1:12345',endpoint_pin='test',model_contract_id='model',execution_profile_id='profile',eos_tokens=[1])
  args=dict(branch='direct-mode',read_paths=['a.py'],edit_paths=['a.py'],test_commands=['python -m unittest'])
  standard=build_launch(self.source,'Repair it',connection,**args)
  direct=build_launch(self.source,'Repair it',connection,thinking_mode='off',**args)
  self.assertEqual(direct['config']['profiles']['control'],generation_profile(thinking_mode='off'))
  direct['config']['profiles']=copy.deepcopy(standard['config']['profiles'])
  self.assertEqual(direct,standard)

 def test_compact_instructions_are_an_independent_explicit_admission(self):
  from branchwrite.coding_defaults import controller_prefix
  from branchwrite.run_cli import _config
  from branchwrite.interpreter import AdmissionError
  schema=self.tools.model_schema()
  default=controller_prefix(schema)
  self.assertEqual(default,controller_prefix(schema,style='worked-examples'))
  compact=controller_prefix(schema,style='compact')
  self.assertLess(len(compact),2800)
  self.assertNotIn('## Worked example',compact)
  self.assertIn('read-only',compact);self.assertIn('exact unique',compact)
  connection=dict(endpoint_url='http://127.0.0.1:12345',endpoint_pin='test',model_contract_id='model',execution_profile_id='profile',eos_tokens=[1])
  args=dict(branch='compact-mode',read_paths=['a.py'],edit_paths=['a.py'],test_commands=['python -m unittest'])
  standard=build_launch(self.source,'Repair it',connection,**args)
  launch=build_launch(self.source,'Repair it',connection,instruction_style='compact',**args)
  self.assertEqual(launch['config']['profiles'],standard['config']['profiles'])
  self.assertEqual(launch['config']['cow'].pop('controller_prefix'),'compact')
  self.assertEqual(launch,standard)
  for invalid in ['unknown',False,None]:
   with self.subTest(style=invalid),self.assertRaises(ValueError):controller_prefix(schema,style=invalid)
  with self.assertRaisesRegex(ValueError,'retained prefixes'):
   build_launch(self.source,'Repair it',connection,instruction_style='compact',from_branch='retained',**args)
  bad=standard['config'];bad['cow']['controller_prefix']='unknown'
  with self.assertRaises(AdmissionError):_config(json.dumps(bad))
