"""Small contact-directory core. Preserve saved entries; search results are sorted by name."""
import json
import unicodedata
from pathlib import Path

def load_contacts(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def save_contacts(path, contacts):
    Path(path).write_text(json.dumps(contacts, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")

def _search_key(value):
    return unicodedata.normalize("NFC", value).casefold()

def search_contacts(contacts, query):
    needle = _search_key(query.strip())
    matches = [entry for entry in contacts if needle in _search_key(entry["name"])]
    return sorted(matches, key=lambda entry: _search_key(entry["name"]))
