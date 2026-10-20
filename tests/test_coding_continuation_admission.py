"""A new coding run can append an explicit tool update to retained context."""
import json,unittest
from branchwrite.run_cli import _config
from branchwrite.interpreter import AdmissionError
class CodingContinuationAdmissionTests(unittest.TestCase):
 def config(self):
  return dict(schema=1,source='/source',run_id='next-task',grant=dict(edit_paths=[],read_paths=[],create_paths=[],allow_tests=False),bindings=dict(task=dict(type='Text',value='UNIQUE_TASK')),cow=dict(endpoint_url='http://127.0.0.1:1',endpoint_pin='owned',model_contract_id='model',execution_profile_id='profile',eos_tokens=[256],branch='forked',mode='append_user',grammar_registration='inline'))
 def test_explicit_user_continuation_accepts_inline_registration(self):
  config=self.config()
  self.assertEqual(_config(json.dumps(config))['cow']['mode'],'append_user')
 def test_ask_without_new_bootstrap_does_not_guess_a_continuation_boundary(self):
  config=self.config();config['cow']['mode']='ask'
  with self.assertRaises(AdmissionError):_config(json.dumps(config))
 def test_tool_update_contains_current_schema_and_task_exactly_once(self):
  from branchwrite.coding_defaults import continuation_input
  content=continuation_input('UNIQUE_TASK',dict(tool_marker='current-tools'),command_requirements=(('python3 -m unittest','exited',0),))
  self.assertIn('current-tools',content);self.assertIn('python3 -m unittest',content)
  self.assertIn('not evidence',content);self.assertEqual(content.count('UNIQUE_TASK'),1)
 def test_ordered_model_parts_keep_their_order(self):
  from branchwrite.coding_defaults import continuation_input
  parts=[dict(type='image',image_id='a'*64),dict(type='text',text='UNIQUE_TASK')]
  content=continuation_input(parts,dict(tool_marker='current-tools'))
  self.assertEqual(content[0],parts[0])
  self.assertIn('current-tools',content[1]['text'])
  self.assertEqual(content[1]['text'].count('UNIQUE_TASK'),1)
  self.assertEqual(parts[1]['text'],'UNIQUE_TASK')

 def test_maximum_valid_part_count_is_preserved(self):
  from branchwrite.coding_defaults import continuation_input
  parts=[dict(type='image',image_id='a'*64) for _ in range(8)]+[dict(type='text',text='question'+str(i)) for i in range(9)]
  content=continuation_input(parts,dict(tool_marker='current-tools'))
  self.assertEqual(len(content),17)
  self.assertEqual(content[:8],parts[:8])
  self.assertEqual(parts[8]['text'],'question0')
