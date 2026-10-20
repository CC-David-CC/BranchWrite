"""Actual PDF tools, granted file publication and current-byte views."""
import json,tempfile,unittest
from pathlib import Path
from branchwrite.execution import Executor,Grant,ToolRejected
from branchwrite.tool_registry import ToolRegistry
from test_pdf_execution import SOURCE

class PdfToolTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  from branchwrite.pdf_tools import PdfCapability
  cls.cap=PdfCapability()
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);root=Path(self.tmp.name)
  source=root/'source';source.mkdir();(source/'report.py').write_bytes(SOURCE)
  self.executor=Executor.create(source,root/'world')
  self.registry=ToolRegistry(self.executor,Grant((),False,project_files=True),pdf=self.cap)
 def call(self,tool,args,op):
  plan=self.registry.freeze(json.dumps(dict(tool=tool,arguments=args)));return self.registry.execute(plan,op)
 def test_actual_pdf_is_published_and_selected_page_is_rendered(self):
  result=self.call('build_pdf',dict(path='report.py',output='reports/result.pdf'),'pdf-build')
  self.assertEqual(result.disposition,'pdf_built',result.stderr)
  document=self.executor._read_private_bytes('reports/result.pdf');self.assertTrue(document.startswith(b'%PDF-'))
  self.assertEqual(result.metadata['pdf_sha256'],__import__('hashlib').sha256(document).hexdigest())
  self.assertEqual(result.observation.path,'reports/result.pdf')
  page=self.call('render_pdf',dict(path='reports/result.pdf',page=2),'pdf-page2')
  self.assertEqual(page.disposition,'pdf_rendered',page.stderr);self.assertEqual(page.metadata['page_count'],2)
  self.assertIn('Measurements',page.stdout.decode());self.assertEqual(page.image.read_bytes()[:8],b'\x89PNG\r\n\x1a\n')
 def test_failed_new_build_preserves_previous_pdf(self):
  self.call('build_pdf',dict(path='report.py',output='result.pdf'),'pdf-first')
  before=self.executor._read_private_bytes('result.pdf')
  (self.executor.workspace/'report.py').write_bytes(b"from pathlib import Path;Path('document.pdf').write_bytes(b'not PDF')")
  result=self.call('build_pdf',dict(path='report.py',output='result.pdf'),'pdf-invalid')
  self.assertEqual(result.disposition,'pdf_failed');self.assertEqual(self.executor._read_private_bytes('result.pdf'),before)
 def test_changed_preimages_reject_frozen_build_before_execution(self):
  plan=self.registry.freeze(json.dumps(dict(tool='build_pdf',arguments=dict(path='report.py',output='result.pdf'))))
  (self.executor.workspace/'report.py').write_bytes(SOURCE+b'\n# changed\n')
  with self.assertRaises(ToolRejected):self.registry.execute(plan,'pdf-stale')
  self.assertFalse((self.executor.workspace/'result.pdf').exists())
 def test_absent_capability_and_ungranted_destinations_are_rejected(self):
  bare=ToolRegistry(self.executor,Grant((),False,project_files=True))
  with self.assertRaises(ToolRejected):bare.freeze(json.dumps(dict(tool='build_pdf',arguments=dict(path='report.py',output='result.pdf'))))
  for target in ['../outside.pdf','/tmp/outside.pdf','image.png']:
   with self.subTest(target=target),self.assertRaises(ToolRejected):self.registry.freeze(json.dumps(dict(tool='build_pdf',arguments=dict(path='report.py',output=target))))
 def test_page_schema_and_host_reject_bool_zero_and_out_of_bounds(self):
  for page in [True,0,-1,257]:
   with self.subTest(page=page),self.assertRaises(ToolRejected):self.registry.freeze(json.dumps(dict(tool='render_pdf',arguments=dict(path='result.pdf',page=page))))
  schema=self.registry.model_schema();variant=next(v for v in schema['oneOf'] if v['properties']['tool']['enum']==['render_pdf'])
  self.assertEqual(variant['properties']['arguments']['properties']['page']['type'],'integer')
  self.assertIn('pdf-page-number',self.registry.model_gbnf())
