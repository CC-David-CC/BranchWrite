"""Small offline structural smoke check, not a browser/design acceptance test."""
from html.parser import HTMLParser
from pathlib import Path

class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.stylesheets = []
        self.language = None
        self.title_depth = 0
        self.title = []
    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        attributes = dict(attrs)
        if tag == "html":
            self.language = attributes.get("lang")
        if tag == "title":
            self.title_depth += 1
        if tag == "link" and "stylesheet" in attributes.get("rel", "").split():
            self.stylesheets.append(attributes.get("href"))
    def handle_endtag(self, tag):
        if tag == "title":
            self.title_depth = max(0, self.title_depth - 1)
    def handle_data(self, data):
        if self.title_depth:
            self.title.append(data)

root = Path(__file__).resolve().parent
html = (root / "index.html").read_text(encoding="utf-8")
css = (root / "style.css").read_text(encoding="utf-8")
assert "\x00" not in html + css, "NUL bytes are not valid source text here"
page = Page()
page.feed(html)
page.close()
for tag in ("html", "head", "title", "body", "h1"):
    assert tag in page.tags, f"Missing <{tag}>"
assert page.language, "Set the page language on <html>"
assert "".join(page.title).strip(), "Use a nonempty page title"
assert "style.css" in page.stylesheets, "Link the local style.css stylesheet"
assert css.strip() and "{" in css and "}" in css, "Write CSS rules"
print("PASS: basic HTML structure and local stylesheet")
