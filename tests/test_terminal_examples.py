"""Terminal prompts teach reports without changing file-only workflows."""
from pathlib import Path
import hashlib,unittest
from branchwrite.coding_defaults import system_prefix

def schema(*tools):
 return dict(oneOf=[dict(properties=dict(tool=dict(enum=[tool]))) for tool in tools])

class TerminalExampleTests(unittest.TestCase):
 def test_terminal_prompt_uses_relevant_complete_worked_examples(self):
  text=system_prefix(schema('read_file','run_shell','finish'))
  self.assertIn('TERMINAL WORKED EXAMPLES',text)
  self.assertIn('A printed success message cannot override the real exit status.',text)
  self.assertIn('EXAMPLE 10',text)
  self.assertNotIn('report their actual contents before requesting finish',text)
 def test_example_final_reports_do_not_teach_copying_drafting_notes(self):
  text=system_prefix(schema('read_file','run_shell','finish'))
  self.assertIn('Keep drafting notes out of the final answer.',text)
  self.assertIn('Refer to the first or second probe when repeating a command is unnecessary.',text)
  self.assertIn('These examples grant no paths, executables or permissions.',text)
 def test_nonterminal_prefix_stays_identical_to_its_frozen_predecessor(self):
  # These fingerprints were checked against the pre-unification main branch.
  expected={'read_file,finish': '57933a4a2b3d5e4f6c46acdb51554defce861b02928f75c78ab3490b1457727e', 'read_file,run_tests,finish': '6a436d88638cec685000d1753f0a67b3ba76cf455fad6ee211a2222eef18f4eb'}
  for names,digest in expected.items():
   self.assertEqual(hashlib.sha256(system_prefix(schema(*names.split(','))).encode()).hexdigest(),digest)
 def test_terminal_support_keeps_required_test_instruction_when_tests_granted(self):
  text=system_prefix(schema('read_file','run_shell','run_tests','finish'))
  self.assertIn('Only request finish after tests pass.',text)
  self.assertIn('TERMINAL WORKED EXAMPLES',text)

if __name__=='__main__':unittest.main()
