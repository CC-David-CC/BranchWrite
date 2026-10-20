"""Strict, shared parser and syntax grammar for the first coding contract."""
import hashlib
import unittest

from branchwrite.coding_contract import LiteralContract, LiteralValue


class LiteralContractTests(unittest.TestCase):
    def setUp(self):
        self.contract = LiteralContract(
            name="replacement", max_bytes=32768, max_lines=256, max_line_bytes=4096)

    def test_round_trips_exact_utf8_lines_and_control_looking_data(self):
        wire = (
            "TEXT replacement\n"
            "|# source file\n"
            "|END\n"
            "|ACT run-tests\n"
            "|<tool_call>{not a tool call}\n"
            "|café λ\n"
            "END\n"
        )
        value = self.contract.parse(wire)
        expected = "# source file\nEND\nACT run-tests\n<tool_call>{not a tool call}\ncafé λ\n".encode()
        self.assertIsInstance(value, LiteralValue)
        self.assertEqual(value.payload, expected)
        self.assertEqual(value.source_sha256, hashlib.sha256(expected).hexdigest())

    def test_empty_and_literal_blank_final_line_are_distinct(self):
        self.assertEqual(self.contract.parse("TEXT replacement\nEND\n").payload, b"")
        self.assertEqual(self.contract.parse("TEXT replacement\n|tail\nEND\n").payload,
                         b"tail\n")
        self.assertEqual(self.contract.parse("TEXT replacement\n|tail\n|\nEND\n").payload,
                         b"tail\n\n")

    def test_requires_exact_framing_name_and_no_extra_records(self):
        invalid = (
            "TEXT replacement\n|x\nEND",                 # truncated terminator
            "TEXT other\n|x\nEND\n",                  # wrong host-owned contract
            "prose\nTEXT replacement\n|x\nEND\n",   # unframed preamble
            "TEXT replacement\n|x\nEND\nmore\n",   # trailing record
            "TEXT replacement\n|x\n|END\n",         # missing terminator
            "TEXT replacement\n|x\nEND\nEND\n",   # duplicate terminator
            "TEXT replacement\n|x\n\nEND\n",        # unprefixed body line
        )
        for text in invalid:
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.contract.parse(text)

    def test_rejects_cr_nul_invalid_utf8_and_bad_contract_metadata(self):
        for text in (
            "TEXT replacement\n|a\rb\nEND\n",
            "TEXT replacement\n|a\x00b\nEND\n",
            "TEXT replacement\n|\ud800\nEND\n",
        ):
            with self.subTest(text=repr(text)), self.assertRaises(ValueError):
                self.contract.parse(text)
        for kwargs in (
            {"name": "bad name", "max_bytes": 10, "max_lines": 2, "max_line_bytes": 5},
            {"name": "x\nEND", "max_bytes": 10, "max_lines": 2, "max_line_bytes": 5},
            {"name": "x", "max_bytes": True, "max_lines": 2, "max_line_bytes": 5},
            {"name": "x", "max_bytes": 10, "max_lines": 0, "max_line_bytes": 5},
            {"name": "x", "max_bytes": 10, "max_lines": 2, "max_line_bytes": False},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                LiteralContract(**kwargs)

    def test_enforces_utf8_byte_line_and_line_count_bounds(self):
        narrow = LiteralContract("replacement", max_bytes=5, max_lines=2, max_line_bytes=3)
        self.assertEqual(narrow.parse("TEXT replacement\n|λ\nEND\n").payload,
                         "λ\n".encode())
        invalid = (
            "TEXT replacement\n|λa\nEND\n",          # four UTF-8 bytes on one line
            "TEXT replacement\n|a\n|b\n|\nEND\n", # too many lines
            "TEXT replacement\n|ab\n|de\nEND\n",   # six UTF-8 bytes total
        )
        for text in invalid:
            with self.subTest(text=text), self.assertRaises(ValueError):
                narrow.parse(text)

    def test_grammar_is_syntax_only_and_compiles_with_pinned_llguidance(self):
        grammar = self.contract.gbnf()
        self.assertIn('"TEXT replacement\\n"', grammar)
        self.assertIn('"END\\n"', grammar)
        self.assertNotIn("a - b", grammar)
        from llguidance import grammar_from
        compiled = grammar_from("gbnf", grammar)
        self.assertTrue(compiled)


if __name__ == "__main__":
    unittest.main()
