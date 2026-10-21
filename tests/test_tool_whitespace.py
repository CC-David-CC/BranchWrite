"""Real CPU grammar matcher; structural whitespace is not source-file text."""
import json,unittest
from test_tool_gbnf import ToolGbnfTests
from context_time_travel.store import IntegrityError

class ToolWhitespaceTests(ToolGbnfTests):
    def test_separator_whitespace_cannot_loop_without_an_action(self):
        for prefix in ['{'+(' \n'*32), '{"tool":'+(' \r'*32),
                       '{"tool":"finish",'+(' \t'*32)]:
            with self.subTest(prefix=prefix),self.assertRaises(IntegrityError):self.consume(prefix)
    def test_separator_limit_preserves_literal_spaces_tabs_and_newlines(self):
        value='  keep    these spaces\n\n  keep\tthis tab\n'
        text=self.emitted('finish',answer=value)
        self.assertTrue(self.consume(text).is_complete())
        self.assertEqual(self.registry.parse(text)[1]['answer'],value)
    def test_single_structural_whitespace_remains_valid_json(self):
        text='{"tool": "finish", "arguments": {"answer": "done"}}'
        self.assertTrue(self.consume(text).is_complete())
        self.assertEqual(json.loads(text)['arguments']['answer'],'done')
