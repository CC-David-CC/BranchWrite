"""Real ReportLab build and independent PDF inspection; no model claim."""
import hashlib,importlib.metadata,io,json,tempfile,tomllib,unittest
from pathlib import Path
from PIL import Image

SOURCE=b"""from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
c=canvas.Canvas('document.pdf',pagesize=letter,invariant=1)
c.setFont('Helvetica-Bold',22);c.drawString(54,730,'BranchWrite Report')
c.setFont('Helvetica',12);c.drawString(54,690,'A measured result, not a claimed result.')
c.showPage();c.setFont('Helvetica-Bold',18);c.drawString(54,730,'Measurements')
c.setFont('Helvetica',12);c.drawString(54,690,'Prefix reused. Files checked. Pages reviewed.')
c.save()
"""
class PdfInitialInstallTests(unittest.TestCase):
 def test_dependencies_are_default_not_optional_task_configuration(self):
  root=Path(__file__).resolve().parents[1]
  config=tomllib.loads((root/'pyproject.toml').read_text())['project']
  for requirement in ['reportlab==5.0.1','pypdfium2==5.14.0','pypdf==6.21.1']:
   self.assertIn(requirement,config['dependencies'])
   name,version=requirement.split('==');self.assertEqual(importlib.metadata.version(name),version)

class PdfExecutionTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  from branchwrite.pdf_execution import PdfRuntime
  cls.runtime=PdfRuntime() # the installed BW interpreter; no operator PDF config
 def build(self,source=SOURCE,extra=()):
  from branchwrite.pdf_execution import build_document
  return build_document((("report.py",source),)+extra,"report.py",self.runtime)
 def test_real_pdf_two_pages_and_actual_png_use_same_bytes(self):
  from branchwrite.pdf_execution import inspect_document
  built=self.build();self.assertEqual(built['disposition'],'built',built['stderr'])
  self.assertTrue(built['isolation']['worker_exited']);self.assertEqual(built['isolation']['namespace_members_after'],[])
  pdf=built['pdf'];self.assertTrue(pdf.startswith(b'%PDF-'))
  result=inspect_document(pdf,1,self.runtime)
  self.assertEqual(result['status'],'PASS',result.get('error'));self.assertEqual(result['page_count'],2)
  self.assertIn('BranchWrite Report',result['text']);self.assertEqual(result['pdf_sha256'],hashlib.sha256(pdf).hexdigest())
  self.assertNotEqual(built['isolation']['launcher_pid'],result['isolation']['launcher_pid'])
  self.assertTrue(result['isolation']['worker_exited']);self.assertEqual(result['isolation']['namespace_members_after'],[])
  image=Image.open(io.BytesIO(result['image']));self.assertEqual(image.format,'PNG');self.assertGreater(image.width,600)
  again=inspect_document(pdf,2,self.runtime);self.assertIn('Measurements',again['text']);self.assertNotEqual(result['image'],again['image'])
 def test_old_export_cannot_masquerade_as_fresh_build(self):
  result=self.build(b'pass',(("document.pdf",b'%PDF-old'),))
  self.assertEqual(result['disposition'],'missing_artifact');self.assertIsNone(result['pdf'])
 def test_link_export_is_rejected_before_parsing(self):
  result=self.build(b"import os;os.symlink('/etc/passwd','document.pdf')")
  self.assertEqual(result['disposition'],'output_rejected');self.assertIsNone(result['pdf'])
 def test_invalid_pdf_and_page_numbers_fail_explicitly(self):
  from branchwrite.pdf_execution import inspect_document
  invalid=inspect_document(b'%PDF-not-a-document',1,self.runtime);self.assertEqual(invalid['status'],'FAIL')
  pdf=self.build()['pdf']
  for page in [0,True,-1,3]:
   with self.subTest(page=page),self.assertRaises(ValueError):inspect_document(pdf,page,self.runtime)
 def test_build_cannot_read_home_credentials_or_use_network(self):
  code=b"""import os,pathlib,socket
assert 'BW_COW_API_KEY' not in os.environ
assert not pathlib.Path('/home/dflanag3/.ssh').exists()
try:socket.create_connection(('10.0.7.68',8099),timeout=.2)
except OSError:pass
else:raise AssertionError('network escaped')
"""+SOURCE
  result=self.build(code);self.assertEqual(result['disposition'],'built',result['stderr'])
 def test_hung_script_is_retired_without_partial_pdf(self):
  from branchwrite.pdf_execution import PdfRuntime,build_document
  runtime=PdfRuntime(timeout=1)
  result=build_document((("report.py",b'import time;time.sleep(30)'),),"report.py",runtime)
  self.assertEqual(result['disposition'],'timeout');self.assertIsNone(result['pdf']);self.assertTrue(result['isolation']['worker_exited'])

class PdfLongDocumentTests(unittest.TestCase):
 def test_twenty_page_document_renders_selected_last_page(self):
  from branchwrite.pdf_execution import PdfRuntime,build_document,inspect_document
  source=b"from reportlab.pdfgen import canvas\nc=canvas.Canvas('document.pdf',invariant=1)\nfor i in range(1,21):\n c.drawString(54,730,'Experiment '+str(i));c.showPage()\nc.save()\n"
  runtime=PdfRuntime();built=build_document((("report.py",source),),"report.py",runtime)
  self.assertEqual(built['disposition'],'built',built['stderr'])
  viewed=inspect_document(built['pdf'],20,runtime)
  self.assertEqual(viewed['status'],'PASS',viewed.get('error'));self.assertEqual(viewed['page_count'],20)
  self.assertIn('Experiment 20',viewed['text']);self.assertGreater(len(viewed['image']),1000)
