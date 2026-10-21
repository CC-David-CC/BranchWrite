"""A long text payload follows its finite control fields in the generation grammar."""
import json,tempfile,unittest
from pathlib import Path
from branchwrite.execution import Executor,Grant
from branchwrite.tool_registry import ToolRegistry
from branchwrite.coding_defaults import grammar_registry
from test_thinking_grammar import ThinkingTokenizer
from context_time_travel.grammar_first import GrammarEngine

class TextFileMetadataOrderTests(unittest.TestCase):
 def test_generated_file_closes_after_payload_without_repeating_control_fields(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'source').mkdir()
   tools=ToolRegistry(Executor.create(root/'source',root/'world'),Grant((),False,create_paths=('new.html',),read_paths=('new.html',)))
   tokenizer=ThinkingTokenizer();engine=GrammarEngine(tokenizer,grammar_registry(tools)['states'],[tokenizer.EOS])
   session=engine.restore(engine.start('BW_TOOLS','metadata-first',[],engine.vocab_size),[])
   proposal=dict(tool='create_text_file',arguments=dict(path='new.html',line_ending='LF',final_newline=True,lines=['<h1>example</h1>','<p>Unicode: ?</p>']))
   for t in [tokenizer.CLOSE,*json.dumps(proposal).encode()]:
    session._consume_selected(t,tokenizer.token_bytes(t),t==tokenizer.EOS)
   self.assertTrue(session.is_complete())
   result=tools.execute(tools.freeze(json.dumps(proposal),observations=()),'new-file')
   self.assertEqual(result.exit_code,0)
   self.assertEqual((root/'world/workspace/new.html').read_text(),'<h1>example</h1>\n<p>Unicode: ?</p>\n')
