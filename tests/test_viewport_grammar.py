"""Actual CPU GBNF/JSON-Schema matchers over the host viewport menu."""
import json,sys,tempfile,unittest
from pathlib import Path
from branchwrite.browser_capture import BrowserConfig
from branchwrite.execution import Executor,Grant,ToolRejected
from branchwrite.tool_registry import ToolRegistry
class ViewportGrammarTests(unittest.TestCase):
 def setUp(self):
  from serve.cow_grammar import GrammarRegistry
  from test_grammar_first import TinyByteTokenizer
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  source=self.root/'source';source.mkdir();(source/'index.html').write_text('page')
  browser=BrowserConfig(Path(sys.executable),viewports=(('desktop',640,480),('phone',360,640)))
  self.tools=ToolRegistry(Executor.create(source,self.root/'world',browser=browser),Grant((),False,read_paths=('index.html',),capture_paths=('index.html',),interact_paths=('index.html',)))
  self.tokenizer=TinyByteTokenizer();self.Registry=GrammarRegistry
 def grammar(self,fmt):
  src=self.tools.model_gbnf() if fmt=='gbnf' else self.tools.model_schema()
  q=self.root/(fmt+'.json');q.write_text(json.dumps(dict(schema=1,states=dict(VIEWPORT=dict(format=fmt,source=src)))))
  return self.Registry.load(q,self.tokenizer,[self.tokenizer.EOS])
 def consume(self,g,text):
  state=g.start('VIEWPORT','named-host-viewports',[],len(self.tokenizer.tokens));s=g.restore(state,[])
  for token in self.tokenizer.encode(text,parse_special=False):state=s.consume(state,token,self.tokenizer.token_bytes(token),False)
  return s
 def proposal(self,name,interact=False):
  args=dict(path='index.html')
  if interact:args['actions']=[dict(kind='click',target='inc',value='')]
  args['viewport']=name
  return json.dumps(dict(tool='interact_page' if interact else 'capture_page',arguments=args))
 def test_both_viewports_and_both_tools_complete_real_gbnf(self):
  g=self.grammar('gbnf')
  for name in ['desktop','phone']:
   for interact in [False,True]:
    text=self.proposal(name,interact);self.assertTrue(self.consume(g,text).is_complete());self.assertEqual(self.tools.parse(text)[1]['viewport'],name)
 def test_ungranted_and_missing_viewports_fail_real_gbnf(self):
  from context_time_travel.store import IntegrityError
  g=self.grammar('gbnf')
  for text in [self.proposal('unknown'),json.dumps(dict(tool='capture_page',arguments=dict(path='index.html')))]:
   with self.subTest(text=text),self.assertRaises(IntegrityError):self.consume(g,text)
   with self.assertRaises(ToolRejected):self.tools.parse(text)
 def test_json_schema_enforces_the_same_viewport_names_and_type(self):
  from context_time_travel.store import IntegrityError
  g=self.grammar('json_schema')
  for name in ['desktop','phone']:
   text=json.dumps(json.loads(self.proposal(name,True)),sort_keys=True);self.assertTrue(self.consume(g,text).is_complete())
  for name in ['unknown',360]:
   text=json.dumps(json.loads(self.proposal(name,True)),sort_keys=True)
   with self.subTest(name=name),self.assertRaises(IntegrityError):self.consume(g,text)
if __name__=='__main__':unittest.main()
