"""Exact selected PDF/text preview through the existing loopback server."""
import tempfile,unittest
from pathlib import Path
from urllib.request import urlopen
from urllib.error import HTTPError
from branchwrite.workspace_versions import WorkspaceVersions
from branchwrite.interactive_preview import Preview

class DocumentPreviewTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.project=self.root/'project';self.project.mkdir();self.preview=Preview();self.addCleanup(self.preview.close)
  self.pdf=(Path(__file__).parents[1]/'validation/pdf-live-q4-20261020/accepted/report.pdf').read_bytes()
 def capture(self):
  versions=WorkspaceVersions(self.project,self.root/'versions')
  return versions,versions.capture('selected',context=None)['commit']
 def missing(self,url):
  with self.assertRaises(HTTPError) as error:urlopen(url,timeout=3)
  self.assertEqual(error.exception.code,404)
 def test_single_saved_pdf_opens_without_a_website(self):
  (self.project/'report.pdf').write_bytes(self.pdf);v,c=self.capture();url=self.preview.show(v,c)
  with urlopen(url,timeout=3) as response:
   self.assertEqual(response.headers['Content-Type'],'application/pdf');self.assertEqual(response.read(),self.pdf)
 def test_selected_text_is_literal_and_other_text_is_not_exposed(self):
  text='Literal <script>alert(1)</script> and Unicode: caf? ?\n'.encode()
  (self.project/'START_HERE.txt').write_bytes(text);(self.project/'private.txt').write_text('not requested')
  v,c=self.capture();url=self.preview.show(v,c,document='START_HERE.txt')
  with urlopen(url,timeout=3) as response:
   self.assertTrue(response.headers['Content-Type'].startswith('text/plain'));self.assertEqual(response.headers['X-Content-Type-Options'],'nosniff');self.assertEqual(response.read(),text)
  self.missing(url.rsplit('/',1)[0]+'/private.txt')
 def test_website_preview_does_not_implicitly_add_documents(self):
  (self.project/'index.html').write_text('<h1>Dogs</h1>');(self.project/'report.pdf').write_bytes(self.pdf);(self.project/'private.txt').write_text('not requested')
  v,c=self.capture();url=self.preview.show(v,c)
  with urlopen(url,timeout=3) as response:self.assertIn(b'Dogs',response.read())
  for name in ['report.pdf','private.txt']:self.missing(url.rsplit('/',1)[0]+'/'+name)
 def test_multiple_pdfs_require_explicit_choice(self):
  for name in ['first.pdf','second.pdf']:(self.project/name).write_bytes(self.pdf)
  v,c=self.capture()
  with self.assertRaisesRegex(ValueError,'preview.*pdf'):self.preview.show(v,c)
