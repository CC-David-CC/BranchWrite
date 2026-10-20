import tempfile
import unittest
from pathlib import Path
from directory import load_contacts, save_contacts, search_contacts

class DirectoryTests(unittest.TestCase):
    def setUp(self):
        self.entries=[{"id":2,"name":"Zoë"},{"id":1,"name":"Ann"}]
    def test_exact_substring(self):
        self.assertEqual(search_contacts(self.entries,"nn"),[self.entries[1]])
    def test_empty_query_preserves_order(self):
        self.assertEqual(search_contacts(self.entries,""),self.entries)
    def test_no_match(self):
        self.assertEqual(search_contacts(self.entries,"nobody"),[])
    def test_case_insensitive_substring(self):
        self.assertEqual(search_contacts(self.entries,"ANN"),[self.entries[1]])
        self.assertEqual(search_contacts(self.entries,"ann"),[self.entries[1]])
    def test_leading_and_trailing_spaces_are_ignored(self):
        self.assertEqual(search_contacts(self.entries,"  Ann  "),[self.entries[1]])
        self.assertEqual(search_contacts(self.entries,"  ANN  "),[self.entries[1]])
    def test_spaces_only_query_preserves_order(self):
        self.assertEqual(search_contacts(self.entries,"   "),self.entries)
    def test_spaces_only_preserves_original_values(self):
        before=[dict(x) for x in self.entries]
        search_contacts(self.entries,"   ")
        self.assertEqual(self.entries,before)
    def test_uppercase_accent_finds_saved_name(self):
        entries=[{"id":3,"name":"Café"}]
        self.assertEqual(search_contacts(entries,"CAFÉ"),entries)
    def test_uppercase_strasse_finds_saved_sharp_s_name(self):
        entries=[{"id":4,"name":"Straße"}]
        self.assertEqual(search_contacts(entries,"STRASSE"),entries)
    def test_search_preserves_original_values(self):
        before=[dict(x) for x in self.entries]
        search_contacts(self.entries,"Ann")
        self.assertEqual(self.entries,before)
    def test_special_search_preserves_original_values(self):
        entries=[{"id":3,"name":"Café"},{"id":4,"name":"Straße"}]
        before=[dict(x) for x in entries]
        search_contacts(entries,"CAFÉ")
        search_contacts(entries,"STRASSE")
        self.assertEqual(entries,before)
    def test_unicode_saved_without_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"contacts.json"
            save_contacts(path,self.entries)
            self.assertEqual(load_contacts(path),self.entries)
