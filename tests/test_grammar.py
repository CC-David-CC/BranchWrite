import unittest
from reference.grammar import Matcher, choice_grammar
from reference.sampling import mask, min_p, greedy

class GrammarTests(unittest.TestCase):
    def setUp(self):
        self.a=b'ACT run plan=plan-a -> out\n'
        self.b=b'ABANDON stop target=attempt reason=declined\n'
        self.m=Matcher((self.a,self.b))
    def test_choice_grammar_escaped_lf(self):
        g=choice_grammar((self.a.decode(),self.b.decode()))
        self.assertIn('\\n"',g)
        self.assertTrue(g.startswith('root ::= '))
    def test_sibling_progress_independent(self):
        prefix=self.m.advance(b'A')
        a,b=prefix.fork(),prefix.fork()
        a=a.advance(self.a[1:])
        self.assertTrue(a.complete)
        self.assertEqual(b.prefix,b'A')
        self.assertTrue(b.permits(b'BANDON'))
        self.assertFalse(b.complete)
    def test_rejected_probe_does_not_mutate(self):
        before=self.m
        for _ in range(20):self.assertFalse(self.m.permits(b'COMMIT'))
        self.assertEqual(self.m,before)
    def test_multiline_token_piece(self):
        m=Matcher((b'ABC\nDEF\n',)).advance(b'ABC\nD')
        self.assertTrue(m.permits(b'EF\n'))
    def test_partial_utf8_bytes(self):
        raw='λ🚀\n'.encode()
        m=Matcher((raw,))
        for piece in [raw[:1],raw[1:3],raw[3:]]:m=m.advance(piece)
        self.assertTrue(m.complete)
    def test_incomplete_not_eos(self):
        self.assertFalse(self.m.advance(b'ACT').complete)
    def test_complete_eos(self):
        self.assertTrue(self.m.advance(self.a).complete)
    def test_empty_piece_is_not_eos(self):
        self.assertFalse(self.m.permits(b''))
    def test_invalid_tail_rejected(self):
        with self.assertRaises(ValueError):self.m.advance(self.a+b'evil')
    def test_empty_grammar_rejected(self):
        with self.assertRaises(ValueError):Matcher(())
    def test_duplicate_choices_rejected(self):
        with self.assertRaises(ValueError):Matcher((self.a,self.a))
    def test_unknown_prefix_rejected(self):
        with self.assertRaises(ValueError):Matcher((self.a,),b'COMMIT')
    def test_invalid_utf8_language_rejected(self):
        with self.assertRaises(UnicodeError):Matcher((b'\xff',))
    def test_control_grammar_does_not_take_program(self):
        with self.assertRaises(ValueError):choice_grammar(('FLOW a\nEND\n',))
    def test_control_grammar_does_not_take_two_calls(self):
        with self.assertRaises(ValueError):choice_grammar(('ACT a plan=p\nACT b plan=q\n',))
    def test_control_grammar_requires_choices(self):
        with self.assertRaises(ValueError):choice_grammar(())
    def test_hard_mask_before_minp(self):
        cs=mask({0:100,1:1,2:0},{1,2})
        self.assertEqual(greedy(min_p(cs,.05)),1)
        self.assertNotIn(0,{c.token for c in cs})
    def test_no_legal_token_is_failure(self):
        with self.assertRaises(ValueError):mask({0:100},{1})
    def test_single_legal_token_survives(self):
        cs=min_p(mask({0:100,1:-100},{1}),1)
        self.assertEqual(greedy(cs),1)
    def test_restore_prefix_same_next_set(self):
        a=self.m.advance(b'ACT run ')
        b=Matcher(a.choices,a.prefix)
        for token in [b'plan=',b'target=',b'plan=plan-a -> out\n']:
            self.assertEqual(a.permits(token),b.permits(token))
