"""Reusable examples are independent of current path/command policy."""
import unittest
from branchwrite.coding_defaults import continuation_input
class ControllerPrefixTests(unittest.TestCase):
 def schema(self,path):
  return {'oneOf':[{'type':'object','properties':{'tool':{'enum':['read_file']},'arguments':{'properties':{'path':{'enum':[path]}}}}}]}
 def test_same_family_different_projects_have_identical_prefix_bytes(self):
  from branchwrite.coding_defaults import controller_prefix
  a=controller_prefix(self.schema('project_a/sentinel.py'))
  b=controller_prefix(self.schema('project_b/different.py'))
  self.assertEqual(a,b)
  self.assertNotIn('project_a/sentinel.py',a);self.assertNotIn('project_b/different.py',a)
 def test_root_points_to_current_task_policy_instead_of_an_embedded_schema(self):
  from branchwrite.coding_defaults import controller_prefix
  text=controller_prefix(self.schema('unique-private-path'))
  self.assertIn('HOST TOOL CONTEXT',text);self.assertNotIn('unique-private-path',text)
  self.assertNotIn('HOST COMPLETION REQUIREMENTS:',text)
  self.assertIn('Worked example',text)
 def test_current_card_changes_without_rewriting_shared_examples(self):
  a=continuation_input('Task A',self.schema('a.py'),command_requirements=(('command-A','exited',0),))
  b=continuation_input('Task B',self.schema('b.py'),command_requirements=(('command-B','exited',0),))
  self.assertIn('command-A',a);self.assertNotIn('command-B',a)
  self.assertIn('command-B',b);self.assertNotIn('command-A',b)
 def test_different_tool_families_do_not_claim_identical_prefixes(self):
  from branchwrite.coding_defaults import controller_prefix
  a=controller_prefix(self.schema('a.py'))
  schema={'oneOf':[{'properties':{'tool':{'enum':['run_shell']}}}]}
  self.assertNotEqual(a,controller_prefix(schema))
