import unittest
from pathlib import Path
from reference.language import parse, render, Node, OPERATIONS, FIELDS
ROOT = Path(__file__).resolve().parents[1]

class LanguageTests(unittest.TestCase):
    def test_all_examples_parse_and_roundtrip(self):
        for path in (ROOT/'examples').glob('*.bw'):
            with self.subTest(path=path.name):
                ast = parse(path.read_text())
                self.assertEqual(parse(render(ast)), ast)
    def test_vocabulary_is_exact(self):
        self.assertEqual(OPERATIONS, set('EXPAND CONTINUE PLAN ACT OBSERVE TRANSFORM SAVE VERIFY CHALLENGE COMPARE SELECT COMPOSE COMMIT ABANDON'.split()))
    def test_literal_instruction_not_executed(self):
        result = parse('TEXT note\n|ACT x plan=bad\n|END\n||x\nEND\n')
        self.assertEqual(len(result),1)
        self.assertEqual(result[0].text,'ACT x plan=bad\nEND\n|x\n')
    def test_empty_text(self):
        self.assertEqual(parse('TEXT note\nEND\n')[0].text,'')
    def test_blank_payload_line(self):
        self.assertEqual(parse('TEXT note\n|\nEND\n')[0].text,'\n')
    def test_unicode_line_separator_is_literal_data(self):
        text = 'TEXT note\n|α\u2028β 🚀\nEND\n'
        self.assertEqual(render(parse(text)),text)
    def test_fields_sort_canonically(self):
        a = parse('PLAN p from=x against=y -> result\n')
        b = parse('PLAN p against=y from=x -> result\n')
        self.assertEqual(a,b)
        self.assertEqual(render(a),'PLAN p against=y from=x -> result\n')
    def test_data_reference_is_not_effect(self):
        n=parse('VALUE r type=ObservedResult ref=artifact-1\n')[0]
        self.assertNotIn(n.op, OPERATIONS)
    def test_depth_limit(self):
        with self.assertRaises(ValueError):parse('FLOW a\nFLOW b\nEND\nEND\n',max_depth=1)
    def test_byte_limit(self):
        with self.assertRaises(ValueError):parse('FLOW a\nEND\n',max_bytes=3)
    def test_node_limit(self):
        with self.assertRaises(ValueError):parse('FLOW a\nFLOW b\nEND\nEND\n',max_nodes=1)
    def test_non_lf_payload_ast_rejected(self):
        with self.assertRaises(ValueError):render((Node('TEXT','n',text='no LF'),))

INVALID = {
 'empty':'', 'no_final_lf':'FLOW a\nEND', 'crlf':'FLOW a\r\nEND\r\n',
 'duplicate':'ACT a plan=p plan=q\n', 'unknown_field':'ACT a plan=p unsafe=yes\n',
 'missing':'ACT a\n', 'legacy_ask':'ASK a from=x task=t profile=p\n',
 'legacy_do':'DO a plan=p\n', 'legacy_look':'LOOK a target=p\n',
 'legacy_check':'CHECK a input=x contract=c\n', 'legacy_stop':'STOP a target=x reason=x\n',
 'shell':'ACT a plan=p;rm\n', 'json':'{"tool":"ACT"}\n',
 'extra_end':'END\n', 'unclosed':'FLOW a\n', 'bad_text':'TEXT a\nACT x plan=p\nEND\n',
 'unclosed_text':'TEXT a\n|hello\n', 'unknown':'EXEC a plan=p\n',
 'zero_repeat':'REPEAT r max=0 until=ok exhausted=abandon\nEND\n',
 'negative_repeat':'REPEAT r max=-1 until=ok exhausted=abandon\nEND\n',
 'huge_repeat':'REPEAT r max=1000001 until=ok exhausted=abandon\nEND\n',
 'bad_arrow':'ACT a plan=p -> x extra\n', 'duplicate_arrow':'ACT a plan=p -> x -> y\n',
 'tab':'ACT\ta plan=p\n', 'double_space':'ACT  a plan=p\n',
 'leading':' ACT a plan=p\n', 'null':'TEXT a\n|\x00\nEND\n',
 'quote':'ACT a plan="p"\n', 'bad_name':'ACT 1a plan=p\n',
 'text_arrow':'TEXT a -> b\nEND\n',
}
for name,text in INVALID.items():
    def check(self, text=text):
        with self.assertRaises(ValueError):parse(text)
    setattr(LanguageTests,'test_reject_'+name,check)
for op in sorted(OPERATIONS):
    def check(self, op=op):
        required=FIELDS[op][0].split()
        source=op+' unit'+''.join(' '+k+'=value' for k in required)+'\n'
        self.assertEqual(parse(source)[0].op,op)
    setattr(LanguageTests,'test_accept_'+op.lower(),check)
