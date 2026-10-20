import json,tempfile,unittest
from pathlib import Path
from branchwrite.coding_defaults import system_prefix
from branchwrite.run_cli import _config
from branchwrite.interpreter import AdmissionError

def schema():
 return dict(oneOf=[dict(properties=dict(tool=dict(enum=[x]))) for x in ['read_file','run_shell','finish']])
class ContextPrefixIntegrationTests(unittest.TestCase):
 def test_pack_text_is_appended_without_replacing_the_tool_contract(self):
  from branchwrite.context_pack import build_pack,PackError
  with tempfile.TemporaryDirectory() as tmp:
   base=Path(tmp);approved=base/'approved';approved.mkdir()
   (approved/'fact.txt').write_text('Recorded executor is a reference, not a live observation.\n')
   receipt=build_pack(root=approved,facts=['fact.txt'],output=base/'packs',as_of='2026-10-18T12:00:00Z')
   path=base/'packs'/receipt['pack_id']
   original=system_prefix(schema())
   text=system_prefix(schema(),context_pack=path,context_pack_id=receipt['pack_id'])
   self.assertTrue(text.startswith(original))
   self.assertIn('Recorded executor is a reference',text)
   with self.assertRaises(PackError):system_prefix(schema(),context_pack=path,context_pack_id='0'*64)
   (approved/'fact.txt').write_text('new facts')
   with self.assertRaises(PackError):system_prefix(schema(),context_pack=path,context_pack_id=receipt['pack_id'])
 def test_explicit_pack_requires_a_hash_pin(self):
  with self.assertRaises(ValueError):
   system_prefix(schema(),context_pack='/does/not/exist')
 def test_config_accepts_only_pinned_absolute_pack_for_new_coding_root(self):
  config=dict(schema=1,source='/tmp/source',run_id='pack-test',grant=dict(edit_paths=[],read_paths=[],create_paths=[],allow_tests=False),bindings={},cow=dict(endpoint_url='http://127.0.0.1:1',endpoint_pin='pin',model_contract_id='m',execution_profile_id='e',eos_tokens=[1],branch='test',mode='ask',bootstrap='coding'),context_pack=dict(path='/tmp/pack',pack_id='a'*64))
  self.assertEqual(_config(json.dumps(config))['context_pack'],config['context_pack'])
  for invalid in [dict(path='relative',pack_id='a'*64),dict(path='/tmp/p',pack_id='oops'),dict(path='/tmp/p',pack_id='a'*64,grant=True)]:
   config['context_pack']=invalid
   with self.assertRaises(AdmissionError):_config(json.dumps(config))
 def test_pack_cannot_be_attached_to_an_existing_unrelated_root(self):
  config=dict(schema=1,source='/tmp/source',run_id='pack-test',grant=dict(edit_paths=[],read_paths=[],create_paths=[],allow_tests=False),bindings={},context_pack=dict(path='/tmp/pack',pack_id='a'*64))
  with self.assertRaises(AdmissionError):_config(json.dumps(config))
if __name__=='__main__':unittest.main()
