"""Measure actual PDF text boxes; do not infer layout from source variables."""
import tempfile,unittest,io
from pathlib import Path
from reportlab.pdfgen import canvas
from branchwrite.pdf_execution import PdfRuntime,inspect_document

class PdfLayoutObservationTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.runtime=PdfRuntime()
 def pdf(self,entries):
  stream=io.BytesIO();c=canvas.Canvas(stream,pagesize=(300,400))
  for x,y,text in entries:c.drawString(x,y,text)
  c.save();return stream.getvalue()
 def test_regular_page_has_measured_zero_without_claiming_visual_correctness(self):
  result=inspect_document(self.pdf([(30,350,'Visible text')]),1,self.runtime)
  self.assertEqual(result['status'],'PASS')
  self.assertEqual(result['layout']['outside_page_characters'],0)
  self.assertEqual(result['layout']['scope'],'text boxes only; images, overlap and design quality require visual inspection')
  self.assertEqual(result['layout']['page_box_points'],[0,0,300,400])
 def test_clipped_characters_report_real_coordinates_and_warning(self):
  result=inspect_document(self.pdf([(-20,350,'LEFT CLIPPED'),(290,300,'RIGHT CLIPPED')]),1,self.runtime)
  self.assertEqual(result['status'],'PASS') # Render remains available for repair.
  layout=result['layout'];self.assertGreater(layout['outside_page_characters'],0)
  self.assertTrue(layout['warnings'])
  self.assertLess(layout['outside_examples'][0]['box_points'][0],0)
  self.assertLessEqual(len(layout['outside_examples']),8)
 def test_empty_page_is_observed_not_claimed_to_satisfy_content_requirements(self):
  stream=io.BytesIO();c=canvas.Canvas(stream,pagesize=(300,400));c.showPage();c.save()
  result=inspect_document(stream.getvalue(),1,self.runtime)
  self.assertEqual(result['layout']['text_characters'],0)
  self.assertEqual(result['layout']['outside_page_characters'],0)

 def test_long_page_has_explicit_scan_bound(self):
  result=inspect_document(self.pdf([(10,300,'A'*9000)]),1,self.runtime)
  self.assertGreater(result['layout']['text_characters'],8192)
  self.assertEqual(result['layout']['checked_characters'],8192)
  self.assertTrue(result['layout']['truncated'])
  self.assertLessEqual(len(result['layout']['outside_examples']),8)
 def test_rotated_page_uses_same_canvas_coordinates(self):
  import pypdf
  raw=self.pdf([(-20,350,'LEFT CLIPPED'),(290,300,'RIGHT CLIPPED')])
  first=inspect_document(raw,1,self.runtime)['layout']
  reader=pypdf.PdfReader(io.BytesIO(raw));reader.pages[0].rotate(90)
  writer=pypdf.PdfWriter();writer.add_page(reader.pages[0]);out=io.BytesIO();writer.write(out)
  rotated=inspect_document(out.getvalue(),1,self.runtime)['layout']
  self.assertEqual(first['outside_page_characters'],rotated['outside_page_characters'])
  self.assertEqual(first['page_box_points'],rotated['page_box_points'])
 def test_cropbox_is_actual_visible_boundary(self):
  import pypdf
  raw=self.pdf([(20,300,'Outside crop'),(100,200,'Inside crop')])
  reader=pypdf.PdfReader(io.BytesIO(raw));reader.pages[0].cropbox.lower_left=(80,80);reader.pages[0].cropbox.upper_right=(260,350)
  writer=pypdf.PdfWriter();writer.add_page(reader.pages[0]);out=io.BytesIO();writer.write(out)
  layout=inspect_document(out.getvalue(),1,self.runtime)['layout']
  self.assertEqual(layout['page_box_points'],[80,80,260,350])
  self.assertGreater(layout['outside_page_characters'],0)

 def test_worked_example_has_no_measured_outside_text_on_either_page(self):
  import re
  from branchwrite.coding_defaults import system_prefix
  from branchwrite.pdf_execution import build_document
  prefix=system_prefix({'oneOf':[{'properties':{'tool':{'enum':['build_pdf']}}}]})
  source=re.search(r'```python\n(.*?)```',prefix,re.S).group(1).encode()
  built=build_document((('example.py',source),),'example.py',self.runtime)
  self.assertEqual(built['disposition'],'built',built['stderr'])
  for page in (1,2):
   result=inspect_document(built['pdf'],page,self.runtime)
   self.assertEqual(result['layout']['outside_page_characters'],0)
   self.assertFalse(result['layout']['truncated'])
 def test_real_build_feedback_exposes_measurements_to_model(self):
  import json
  from branchwrite.execution import Executor,Grant
  from branchwrite.tool_registry import ToolRegistry
  from branchwrite.pdf_tools import PdfCapability
  from branchwrite.records import RuntimeLog
  from branchwrite.kernel import FrameKernel
  from branchwrite.interpreter import Interpreter,Value
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);source=root/'source';source.mkdir()
   (source/'report.py').write_text("from reportlab.pdfgen import canvas;c=canvas.Canvas('document.pdf',pagesize=(300,400));c.drawString(-20,300,'LEFT CLIPPED');c.save()")
   executor=Executor.create(source,root/'world')
   registry=ToolRegistry(executor,Grant((),False,project_files=True),pdf=PdfCapability())
   with RuntimeLog(root/'ledger') as log:
    runtime=Interpreter(FrameKernel(log),registry)
    runtime.start('FLOW pdf\nPLAN p from=proposal against=world -> plan\nACT a plan=plan -> outcome\nTRANSFORM f contract=tool-feedback input=outcome -> feedback\nEND\n',
     {'proposal':Value('ToolProposal',json.dumps(dict(tool='build_pdf',arguments=dict(path='report.py',output='result.pdf'))))})
    result=runtime.run();self.assertEqual(result.status,'complete')
    view=json.loads(result.value['bindings']['feedback'][1]);observed=json.loads(view['stdout'])
    self.assertEqual(view['disposition'],'pdf_built')
    self.assertGreater(observed['layout']['outside_page_characters'],0)
    self.assertTrue(observed['layout']['warnings'])
    self.assertIsNotNone(view['image']) # Current rendered evidence remains available.
