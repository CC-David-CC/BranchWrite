"""Owner-selected new thinking default; failure ladder is host-controlled."""
from pathlib import Path
import copy,tempfile,unittest
from branchwrite.execution import Executor,Grant
from branchwrite.tool_registry import ToolRegistry
from branchwrite.coding_defaults import grammar_registry,generation_profile
class ThinkingDefaultsTests(unittest.TestCase):
 def tools(self,root):
  s=root/'source';s.mkdir();(s/'a.py').write_text('old')
  return ToolRegistry(Executor.create(s,root/'run'),Grant(('a.py',),True,read_paths=('a.py',)))
 def test_new_default_is_4096_without_1024_answer_target(self):
  from branchwrite.cow_actions import DEFAULT_THINKING_TOKENS
  self.assertEqual(DEFAULT_THINKING_TOKENS,4096)
  with tempfile.TemporaryDirectory() as t:
   state=grammar_registry(self.tools(Path(t)))['states']['BW_TOOLS']
   self.assertEqual(state['source']['max_tokens'],4096)
  self.assertGreater(generation_profile()['max_output_tokens'],4096)
 def test_standard_and_lite_ladders_start_at_their_own_budget(self):
  from branchwrite.thinking_ladder import ladder
  standard=ladder();lite=ladder('lite')
  self.assertEqual([x.tokens for x in standard],[4096,8192,16384,32768])
  self.assertEqual([x.tokens for x in lite],[256,512,1024,2048,4096,8192,16384,32768])
  self.assertTrue(all(a.seconds<b.seconds for a,b in zip(lite,lite[1:])))
  with self.assertRaises(ValueError):ladder('unknown')
 def test_only_verified_task_failure_advances_and_exhaustion_stops(self):
  from branchwrite.thinking_ladder import next_attempt,ladder
  self.assertEqual(next_attempt('standard',0,'verified_failure'),1)
  self.assertEqual(next_attempt('standard',0,'verified_pass'),None)
  self.assertEqual(next_attempt('standard',len(ladder())-1,'verified_failure'),None)
  for status in ['incomplete','tool_progress','infrastructure_failure','unresolved_effect']:
   with self.subTest(status=status):self.assertEqual(next_attempt('standard',0,status),0)
  with self.assertRaises(ValueError):next_attempt('standard',0,'model_says_pass')
 def test_failed_natural_thinking_can_escalate_without_model_budget_choice(self):
  from branchwrite.thinking_ladder import next_attempt
  # The owner now chooses host verified failure as the ladder trigger,
  # independently of whether the model ended thinking early.
  self.assertEqual(next_attempt('lite',0,'verified_failure'),1)
 def test_budget_definitions_are_detached_immutable_and_named(self):
  from dataclasses import FrozenInstanceError
  from branchwrite.thinking_ladder import ladder
  q=ladder()[0]
  with self.assertRaises(FrozenInstanceError):q.tokens=256
  with tempfile.TemporaryDirectory() as t:
   tools=self.tools(Path(t));a=grammar_registry(tools);saved=copy.deepcopy(a)
   self.assertEqual(a['states']['BW_TOOLS']['source']['max_tokens'],4096)
   for rung in ladder('lite'):
    self.assertEqual(a['states'][rung.grammar_state]['source']['max_tokens'],rung.tokens)
    self.assertEqual(a['states'][rung.grammar_state]['source']['final'],dict(format='gbnf',source=tools.model_gbnf()))
   a['states']['BW_TOOLS']['source']['max_tokens']=1
   self.assertEqual(grammar_registry(tools),saved)
 def test_recovery_guidance_is_task_level_and_contains_no_reference_answer(self):
  from branchwrite.thinking_ladder import recovery_guidance
  text=recovery_guidance('Repair the report config.','The report command said: missing file.')
  for fragment in ['Think carefully','givens','assumptions','different approach','missing file']:self.assertIn(fragment,text)
  self.assertNotIn('expected-report.tsv',text)
  self.assertNotIn('temperature',text)
if __name__=='__main__':unittest.main()
