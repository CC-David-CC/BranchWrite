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
    def test_search_preserves_original_values(self):
        before=[dict(x) for x in self.entries]
        search_contacts(self.entries,"Ann")
        self.assertEqual(self.entries,before)
    def test_unicode_saved_without_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"contacts.json"
            save_contacts(path,self.entries)
            self.assertEqual(load_contacts(path),self.entries)
