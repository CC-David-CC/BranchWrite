"""Small contact-directory core. Preserve the input entries and their order."""
import json
from pathlib import Path

def load_contacts(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def save_contacts(path, contacts):
    Path(path).write_text(json.dumps(contacts, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")

def search_contacts(contacts, query):
    return [entry for entry in contacts if query in entry["name"]]
