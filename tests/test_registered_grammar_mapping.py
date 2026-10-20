"""Logical thinking states resolve through one immutable admitted mapping."""
from pathlib import Path
import tempfile,unittest
from branchwrite.cow_client import CowClient,OperationJournal,BranchHead
from branchwrite.model_dispatch import ModelAdapter,ModelContractError
from branchwrite.records import decode
from branchwrite.thinking_ladder import ladder
class RegisteredGrammarMappingTests(unittest.TestCase):
 def adapter(self,root,mapping):
  client=CowClient.http('http://127.0.0.1:1',journal=OperationJournal(root/'journal'),endpoint_pin='owned')
  return ModelAdapter(client,run_id='test',model_contract_id='model',execution_profile_id='profile',eos_tokens=(256,),grammar_mapping=mapping)
 def test_each_ladder_rung_and_saved_plan_use_its_registered_state(self):
  with tempfile.TemporaryDirectory() as td:
   rungs=ladder('standard');mapping={r.grammar_state:'g'+'a'*64+'_s'+str(i) for i,r in enumerate(rungs)}
   adapter=self.adapter(Path(td),mapping);head=BranchHead('main',0,'a'*64,'a'*64)
   for i,rung in enumerate(rungs):
    context=dict(schema=1,profile='control',mode='standard',rung=i,origin_model_frame='model-origin',handled_failures=tuple('failure'+str(j) for j in range(i)))
    plan=adapter.freeze(head,mode='answer',grammar_state=rung.grammar_state,output_format='thinking',planning=context)
    self.assertEqual(adapter.plan(plan)['config']['grammar_state'],mapping[rung.grammar_state])
 def test_caller_mapping_mutation_does_not_rebind_adapter(self):
  with tempfile.TemporaryDirectory() as td:
   mapping={'BW_TOOLS':'g'+'a'*64+'_s0'};adapter=self.adapter(Path(td),mapping)
   identity=adapter.identity;mapping['BW_TOOLS']='g'+'b'*64+'_s0'
   plan=adapter.freeze(BranchHead('main',0,'a'*64,'a'*64),mode='answer',grammar_state='BW_TOOLS',output_format='thinking')
   self.assertEqual(decode(plan.data)['config']['grammar_state'],'g'+'a'*64+'_s0')
   self.assertEqual(adapter.identity,identity)
 def test_unknown_state_is_not_sent_under_registered_admission(self):
  with tempfile.TemporaryDirectory() as td:
   adapter=self.adapter(Path(td),{'BW_TOOLS':'g'+'a'*64+'_s0'})
   with self.assertRaises(ModelContractError):
    adapter.freeze(BranchHead('main',0,'a'*64,'a'*64),mode='answer',grammar_state='UNKNOWN',output_format='thinking')

class RegistrationConfigTests(unittest.TestCase):
 def config(self):
  return dict(schema=1,source='/source',run_id='registration',grant=dict(edit_paths=[],read_paths=[],create_paths=[],allow_tests=True),bindings={},cow=dict(endpoint_url='http://127.0.0.1:1',endpoint_pin='owned',model_contract_id='m',execution_profile_id='p',eos_tokens=[256],branch='main',mode='ask',bootstrap='coding',grammar_registration='inline'))
 def test_explicit_inline_registration_admits_only_coding_bootstrap(self):
  import json
  from branchwrite.run_cli import _config
  from branchwrite.interpreter import AdmissionError
  config=self.config()
  self.assertEqual(_config(json.dumps(config))['cow']['grammar_registration'],'inline')
  del config['cow']['bootstrap']
  with self.assertRaises(AdmissionError):_config(json.dumps(config))
 def test_unknown_registration_modes_fail_closed(self):
  import json
  from branchwrite.run_cli import _config
  from branchwrite.interpreter import AdmissionError
  config=self.config();config['cow']['grammar_registration']='automatic-fallback'
  with self.assertRaises(AdmissionError):_config(json.dumps(config))
