"""Real PCC matcher and BW host admission, with generated synthetic inputs."""
import copy
import json
import tempfile
from pathlib import Path
import unittest
from unittest import mock

from branchwrite.coding_defaults import grammar_registry
from branchwrite.execution import Executor, Grant, ToolRejected
from branchwrite.tool_registry import ToolRegistry
from context_time_travel.grammar_first import GrammarEngine
from context_time_travel.store import IntegrityError
from test_thinking_grammar import ThinkingTokenizer

class LarkToolTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);root=Path(tmp.name)
        source=root/'source';source.mkdir();(source/'a.py').write_text('old')
        self.tools=ToolRegistry(Executor.create(source,root/'run'),Grant(('a.py',),True,read_paths=('a.py',)))
        self.tokenizer=ThinkingTokenizer()

    def engine(self, syntax='lark'):
        return GrammarEngine(self.tokenizer,grammar_registry(self.tools,direct=True,syntax=syntax)['states'],[self.tokenizer.EOS])

    def session(self, engine):
        return engine.restore(engine.start('BW_TOOLS_DIRECT','lark-tools',[],engine.vocab_size),[])

    def feed(self,session,text):
        for token in text.encode():session._consume_selected(token,self.tokenizer.token_bytes(token),False)

    def proposal(self, lines):
        return json.dumps(dict(tool='replace_text_file',arguments=dict(path='a.py',line_ending='LF',final_newline=True,lines=lines)),separators=(',',':'),ensure_ascii=True)

    def test_opt_in_and_legacy_payload_are_distinct_and_old_snapshot_refused(self):
        old=grammar_registry(self.tools,direct=True)
        from hashlib import sha256
        # Captured from the original 37410085 implementation with this owned fixture.
        encoded=json.dumps(old,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
        self.assertEqual(sha256(encoded).hexdigest(),'4ff4f9c2c5c09fa9f3e37935c0e25fdc1704adda281cfc6c082b57130084fc4a')
        self.assertEqual(old,grammar_registry(self.tools,direct=True,syntax='gbnf'))
        self.assertEqual(old['states']['BW_TOOLS_DIRECT'],dict(format='gbnf',source=self.tools.model_gbnf()))
        new=grammar_registry(self.tools,direct=True,syntax='lark')
        self.assertEqual(new['states']['BW_TOOLS_DIRECT']['format'],'lark')
        self.assertTrue(all(v['source']['final']['format']=='lark'for k,v in new['states'].items()if k!='BW_TOOLS_DIRECT'))
        legacy=self.engine('gbnf');state=legacy.start('BW_TOOLS_DIRECT','legacy',[],legacy.vocab_size);saved=copy.deepcopy(state)
        with self.assertRaises(IntegrityError):self.engine().restore(state,[])
        self.assertEqual(saved,state)
        for syntax in ('unknown',True,None):
            with self.assertRaises(ValueError):grammar_registry(self.tools,syntax=syntax)

    def test_repetitive_array_accepts_maximum_and_masks_one_over(self):
        engine=self.engine()
        for length in (0,4096):
            text=self.proposal(['']*length);session=self.session(engine);self.feed(session,text)
            self.assertTrue(session.is_complete());self.assertEqual(len(json.loads(text)['arguments']['lines']),length)
        with self.assertRaises(IntegrityError):self.feed(self.session(engine),self.proposal(['']*4097))

    def test_escape_and_metadata_contracts_preserved(self):
        engine=self.engine()
        text=self.proposal(['quote " and slash \\', 'caf\u00e9', '\tindent'])
        session=self.session(engine);self.feed(session,text);self.assertTrue(session.is_complete())
        self.assertEqual(self.tools.parse(text)[0],'replace_text_file')
        for text in [text.replace('"LF"','"CR"'),text.replace('"final_newline":true','"final_newline":1'),self.proposal(['bad\nline'])]:
            with self.subTest(text=text[:90]),self.assertRaises((IntegrityError,ToolRejected)):
                session=self.session(engine);self.feed(session,text)
                self.tools.parse(text)

    def test_host_grant_remains_authoritative(self):
        text=self.proposal(['new']).replace('"a.py"','"secret.py"')
        # Exact granted-path grammar must reject it; host also refuses it independently.
        with self.assertRaises(IntegrityError):self.feed(self.session(self.engine()),text)
        with self.assertRaises(ToolRejected):self.tools.parse(text)

    def test_missing_optional_dependency_never_falls_back(self):
        with mock.patch.dict('sys.modules',{'llguidance':None}):
            with self.assertRaises(ValueError):self.tools.model_lark()

if __name__=='__main__':unittest.main()
