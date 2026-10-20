"""Actual COW parser boundaries for the new 4K thinking definition."""
import copy,tempfile,unittest
from pathlib import Path
from branchwrite.execution import Executor,Grant
from branchwrite.tool_registry import ToolRegistry
from branchwrite.coding_defaults import grammar_registry
class ThinkingBudgetGrammarTests(unittest.TestCase):
 def setUp(self):
  from test_thinking_grammar import ThinkingTokenizer
  from context_time_travel.grammar_first import GrammarEngine
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);root=Path(self.tmp.name)
  source=root/'source';source.mkdir();(source/'a.py').write_text('old')
  self.tools=ToolRegistry(Executor.create(source,root/'run'),Grant(('a.py',),True,read_paths=('a.py',)))
  self.tokenizer=ThinkingTokenizer();self.engine=GrammarEngine(self.tokenizer,grammar_registry(self.tools)['states'],[self.tokenizer.EOS])
 def session(self):
  state=self.engine.start('BW_TOOLS','new-budget',[],self.engine.vocab_size)
  return self.engine.restore(state,[])
 def consume(self,s,token):s._consume_selected(token,self.tokenizer.token_bytes(token),token==self.tokenizer.EOS)
 def allowed(self,s,token):
  logits=[0.]*self.engine.vocab_size;logits[token]=100.
  return s.choose(logits)==token
 def test_4096_budget_forces_legal_closure_not_an_incomplete_action(self):
  s=self.session()
  for _ in range(4096):self.consume(s,ord('x'))
  self.assertTrue(self.allowed(s,self.tokenizer.CLOSE));self.assertFalse(self.allowed(s,ord('x')))
  self.consume(s,self.tokenizer.CLOSE);self.assertEqual(s.thinking_progress()['close_reason'],'budget')
  for token in b'{"tool":"finish","arguments":{"answer":"done"}}':self.consume(s,token)
  self.assertTrue(s.is_complete());self.consume(s,self.tokenizer.EOS);self.assertTrue(s.is_stopped())
 def test_natural_closure_can_finish_before_allowance(self):
  s=self.session()
  for token in b'short':self.consume(s,token)
  self.consume(s,self.tokenizer.CLOSE)
  self.assertEqual(s.thinking_progress()['reasoning_tokens'],5)
  self.assertEqual(s.thinking_progress()['close_reason'],'natural')
 def test_saved_1024_definition_is_not_silently_rebudgeted(self):
  from context_time_travel.grammar_first import GrammarEngine
  from context_time_travel.store import IntegrityError
  payload=grammar_registry(self.tools);payload['states']['BW_TOOLS']['source']['max_tokens']=1024
  old=GrammarEngine(self.tokenizer,payload['states'],[self.tokenizer.EOS]);state=old.start('BW_TOOLS','saved',[],old.vocab_size);frozen=copy.deepcopy(state)
  with self.assertRaises(IntegrityError):self.engine.restore(state,[])
  self.assertEqual(state,frozen)
if __name__=='__main__':unittest.main()
