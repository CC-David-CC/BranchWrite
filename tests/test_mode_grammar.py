"""COW CPU grammar integration for mode proposals;not GPU qualification."""
import json,tempfile,unittest
from pathlib import Path
from branchwrite.execution import Executor,Grant
from branchwrite.tool_registry import ToolRegistry
class ModeGrammarTests(unittest.TestCase):
 def setUp(self):
  from serve.cow_grammar import GrammarRegistry
  from test_grammar_first import TinyByteTokenizer
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name);source=self.root/'source';source.mkdir();(source/'task.sh').write_text('script')
  self.registry=ToolRegistry(Executor.create(source,self.root/'world'),Grant((),False,read_paths=('task.sh',),mode_paths=('task.sh',),mode_mask=0o100))
  self.tokenizer=TinyByteTokenizer();self.registries={}
  for fmt,source in [('gbnf',self.registry.model_gbnf()),('json_schema',self.registry.model_schema())]:
   cfg=self.root/(fmt+'.json');cfg.write_text(json.dumps(dict(schema=1,states=dict(TOOLS=dict(format=fmt,source=source)))))
   self.registries[fmt]=GrammarRegistry.load(cfg,self.tokenizer,[self.tokenizer.EOS])
 def consume(self,fmt,text):
  g=self.registries[fmt];state=g.start('TOOLS','mode-test',[],len(self.tokenizer.tokens));session=g.restore(state,[])
  for token in self.tokenizer.encode(text,parse_special=False):state=session.consume(state,token,self.tokenizer.token_bytes(token),False)
  return session
 def test_exact_octal_mode_completes_in_gbnf_and_json_schema(self):
  for fmt in self.registries:
   proposal=json.dumps(dict(tool='set_mode',arguments=dict(path='task.sh',mode='0740')),sort_keys=fmt=='json_schema')
   with self.subTest(fmt=fmt):self.assertTrue(self.consume(fmt,proposal).is_complete())
 def test_malformed_and_special_modes_rejected_by_both_grammars(self):
  from context_time_travel.store import IntegrityError
  for fmt in self.registries:
   for mode in ['740','4740','0780',True]:
    with self.subTest(fmt=fmt,mode=mode),self.assertRaises(IntegrityError):
     self.consume(fmt,json.dumps(dict(tool='set_mode',arguments=dict(path='task.sh',mode=mode)),sort_keys=fmt=='json_schema'))
if __name__=='__main__':unittest.main()
