"""Host completion obligations must be visible at new model admission."""
import unittest
from branchwrite.coding_defaults import system_prefix
class CommandPrefixTests(unittest.TestCase):
 def schema(self):
  return dict(oneOf=[dict(properties=dict(tool=dict(enum=['run_shell']))),dict(properties=dict(tool=dict(enum=['finish'])))])
 def test_host_command_requirement_is_visible_and_not_an_execution_claim(self):
  prefix=system_prefix(self.schema(),command_requirements=(('python3 -m unittest discover -s tests -v','exited',0),))
  self.assertIn('python3 -m unittest discover -s tests -v',prefix)
  self.assertIn('host completion requirements',prefix.lower())
  self.assertIn('not evidence',prefix.lower())
 def test_absent_command_requirement_preserves_existing_prefix(self):
  self.assertEqual(system_prefix(self.schema()),system_prefix(self.schema(),command_requirements=()))
