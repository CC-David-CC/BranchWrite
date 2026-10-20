"""Host action validation; real filesystem edits, no model or GPU substitutes."""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from branchwrite.cow_actions import completed_thinking_text, replacement_schema, parse_replacement
from branchwrite.execution import Executor, Grant, ToolRejected


class CowActionTests(unittest.TestCase):
    def result(self, **changes):
        thinking = dict(schema=1, snapshot='a'*64, complete=True,
                        reasoning_text='A literal </think> is not a boundary.', final_text='{"ok":true}')
        thinking.update(changes)
        return SimpleNamespace(receipt=SimpleNamespace(snapshot='a'*64),
                               answer=dict(tokens=[7, 9], thinking=thinking, text='unsafe raw thought'))

    def test_complete_result_returns_only_receipt_bound_final(self):
        self.assertEqual(completed_thinking_text(self.result(), (9,)), '{"ok":true}')

    def test_partial_mismatched_missing_and_non_eos_are_rejected(self):
        for changes in (dict(complete=False, final_text=None), dict(snapshot='b'*64),
                        dict(schema=True), dict(final_text=7)):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                completed_thinking_text(self.result(**changes), (9,))
        for answer in (dict(tokens=[7, 9], text='do not execute'),
                       dict(self.result().answer, tokens=[7])):
            result = self.result()
            result.answer = answer
            with self.assertRaises(ValueError):
                completed_thinking_text(result, (9,))

    def action(self, **changes):
        args = dict(path='index.html', before='blue', after='green')
        args.update(changes)
        return json.dumps(dict(tool='replace', arguments=args))

    def test_schema_grants_path_and_structure_not_answer(self):
        schema = replacement_schema('index.html')
        args = schema['properties']['arguments']
        self.assertEqual(args['properties']['path']['enum'], ['index.html'])
        self.assertEqual(set(args['required']), {'path', 'before', 'after'})
        self.assertNotIn('enum', args['properties']['after'])
        self.assertEqual(parse_replacement(self.action(), 'index.html'), (b'blue', b'green'))

    def test_duplicate_extra_wrong_path_and_empty_preimage_rejected(self):
        bad = [self.action(path='../other'), self.action(before=''), self.action(after=3),
               self.action(authorization=True), self.action().replace('"tool": "replace"',
                   '"tool":"replace","tool":"replace"')]
        for text in bad:
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_replacement(text, 'index.html')

    def test_unicode_byte_bound_is_independent_of_schema_character_bound(self):
        with self.assertRaises(ValueError):
            parse_replacement(self.action(after='é' * 20000), 'index.html')

    def test_actual_edit_rejects_stale_hash_and_preserves_input(self):
        import hashlib
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root/'source'
            source.mkdir()
            (source/'index.html').write_bytes(b'blue')
            executor = Executor.create(source, root/'tool')
            grant = Grant(('index.html',), False, read_paths=('index.html',))
            before, after = parse_replacement(self.action(), 'index.html')
            with self.assertRaises(ToolRejected):
                executor.replace('stale', grant, 'index.html', '0'*64, before, after)
            self.assertEqual((executor.workspace/'index.html').read_bytes(), b'blue')
            result = executor.replace('edit', grant, 'index.html', hashlib.sha256(b'blue').hexdigest(), before, after)
            self.assertEqual(result.disposition, 'applied')
            self.assertEqual(executor.read_file('read', grant, 'index.html').stdout.read_bytes(), b'green')
            self.assertEqual((source/'index.html').read_bytes(), b'blue')

if __name__ == '__main__':
    unittest.main()
