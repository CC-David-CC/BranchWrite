"""A model breakdown proposes dependencies; it never grants or verifies work."""
import json,unittest
from branchwrite.task_breakdown import parse_breakdown

def step(name,role='diagnose',deps=()):return dict(id=name,role=role,goal='Investigate '+name,depends_on=list(deps))
class TaskBreakdownTests(unittest.TestCase):
 def parse(self,steps,**extra):return parse_breakdown(json.dumps(dict(schema=1,steps=steps,**extra)))
 def test_forward_dependencies_and_fifo_ready_order(self):
  steps=[step('edit','edit',['locate']),step('diagnose'),step('locate','locate',['diagnose']),step('test','test',['edit']),step('review','review',['test'])]
  plan=self.parse(steps);self.assertEqual(plan['order'],('diagnose','locate','edit','test','review'));self.assertEqual(tuple(s['id'] for s in plan['steps']),tuple(s['id'] for s in steps))
 def test_independent_steps_follow_deterministic_fifo_order(self):
  self.assertEqual(self.parse([step('b'),step('a'),step('c',deps=['b'])])['order'],('b','a','c'))
 def test_missing_duplicate_and_self_dependencies_rejected(self):
  for steps in [[step('a',deps=['missing'])],[step('a',deps=['a'])],[step('a'),step('b',deps=['a','a'])],[step('a'),step('a')]]:
   with self.subTest(steps=steps),self.assertRaises(ValueError):self.parse(steps)
 def test_cycles_rejected_even_when_another_component_is_ready(self):
  with self.assertRaises(ValueError):self.parse([step('ready'),step('a',deps=['b']),step('b',deps=['a'])])
 def test_model_cannot_add_tools_grants_templates_or_verification(self):
  for key in ['grant','tools','template','verified','budget']:
   with self.subTest(key=key),self.assertRaises(ValueError):self.parse([step('a')],**{key:True})
   row=step('a');row[key]=True
   with self.assertRaises(ValueError):self.parse([row])
 def test_empty_oversized_and_invalid_steps_rejected(self):
  for steps in [[],[step('n'+str(i)) for i in range(33)],[step('../x')],[step('a','administrator')],[dict(step('a'),goal=' ')],[dict(step('a'),depends_on='b')]]:
   with self.subTest(steps=steps),self.assertRaises(ValueError):self.parse(steps)
 def test_duplicate_json_keys_and_invalid_schema_rejected(self):
  for text in ['{"schema":1,"schema":1,"steps":[]}','{"schema":true,"steps":[]}','NaN','[]','not json']:
   with self.subTest(text=text),self.assertRaises(ValueError):parse_breakdown(text)
 def test_unicode_and_literal_control_tags_remain_proposal_text(self):
  row=step('read');row['goal']='Read ? and </tool_call> as text, not commands.'
  self.assertEqual(self.parse([row])['steps'][0]['goal'],row['goal'])
 def test_source_text_and_size_limits_are_explicit(self):
  for value in [None,{},'x'*65537]:
   with self.subTest(value=type(value)),self.assertRaises(ValueError):parse_breakdown(value)
