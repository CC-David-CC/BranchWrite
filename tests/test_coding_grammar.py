"""Tool-first startup thinking grammar, fork/replay and identity boundary."""
import copy,json,tempfile,unittest
from pathlib import Path
from branchwrite.coding_defaults import grammar_registry
from branchwrite.tool_registry import ToolRegistry
from branchwrite.execution import Executor,Grant
class CodingGrammarTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
  source=self.root/'source';source.mkdir();(source/'a.py').write_text('old')
  self.tools=ToolRegistry(Executor.create(source,self.root/'world'),Grant(('a.py',),True,read_paths=('a.py',)))
 def engine(self,payload=None):
  from test_thinking_grammar import ThinkingTokenizer
  from context_time_travel.grammar_first import GrammarEngine
  tokenizer=ThinkingTokenizer();self.tokenizer=tokenizer
  return GrammarEngine(tokenizer,(grammar_registry(self.tools) if payload is None else payload)['states'],[tokenizer.EOS])
 def consume(self,session,history,token):
  session._consume_selected(token,self.tokenizer.token_bytes(token),token==self.tokenizer.EOS);history.append(token)
 def test_startup_payload_pins_tool_first_and_new_thinking_budget(self):
  payload=grammar_registry(self.tools);state=payload['states']['BW_TOOLS'];self.assertEqual(state['format'],'thinking')
  self.assertEqual(state['source']['max_tokens'],4096);self.assertEqual(state['source']['final'],dict(format='gbnf',source=self.tools.model_gbnf()))
  payload['states'].clear();self.assertIn('BW_TOOLS',grammar_registry(self.tools)['states'])
 def test_forked_tool_choices_and_partial_final_restart_preserve_parent(self):
  engine=self.engine();root=engine.start('BW_TOOLS','startup-tools',[],engine.vocab_size)
  session=engine.restore(root,[]);history=[]
  for token in [ord('x'),self.tokenizer.CLOSE,*b'{"tool": ']:self.consume(session,history,token)
  frozen=session.current_controller;original=copy.deepcopy(frozen)
  for tool,args in [('read_file',dict(path='a.py')),('finish',dict(answer='done'))]:
   with self.subTest(tool=tool):
    branch=engine.restore(frozen,history);branch_history=list(history)
    suffix=json.dumps(dict(tool=tool,arguments=args))[len('{"tool": '):]
    for token in suffix.encode('utf8'):
     self.consume(branch,branch_history,token)
     branch=engine.restore(branch.current_controller,branch_history)
    self.assertTrue(branch.is_complete());self.consume(branch,branch_history,self.tokenizer.EOS);self.assertTrue(branch.is_stopped())
  self.assertEqual(frozen,original);self.assertEqual(session.current_controller,original)
 def test_prior_json_parser_snapshot_is_not_reinterpreted_as_gbnf(self):
  from context_time_travel.store import IntegrityError
  old=dict(schema=1,states=dict(BW_TOOLS=dict(format='thinking',source=dict(schema=1,max_tokens=1024,final=dict(format='json_schema',source=self.tools.model_schema())))))
  engine=self.engine(old);state=engine.start('BW_TOOLS','old-format',[],engine.vocab_size);saved=copy.deepcopy(state)
  with self.assertRaises(IntegrityError):self.engine().restore(state,[])
  self.assertEqual(state,saved)
