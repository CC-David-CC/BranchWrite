"""New normal project launches attach actual page image feedback by default."""
import tempfile,unittest
from pathlib import Path
from branchwrite.coding_cli import build_launch,_validate
from branchwrite.coding_defaults import continuation_input
class PdfDefaultCliTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.connection=dict(endpoint_url='http://127.0.0.1:8099',endpoint_pin='a'*64,model_contract_id='b'*64,execution_profile_id='c'*64,eos_tokens=[2])
 def test_normal_work_launch_includes_page_image_feedback_without_pdf_config(self):
  value=build_launch(Path(self.tmp.name),'Write a report PDF.',self.connection,branch='document',project_files=True)
  _validate(value)
  self.assertIn('profile=project-views',value['program'])
  self.assertEqual(value['config']['profiles']['project-views'],dict(kind='image-feedback',source='current'))
  self.assertNotIn('pdf',value['config'])
 def test_readonly_launch_does_not_gain_python_execution(self):
  value=build_launch(Path(self.tmp.name),'Discuss the report.',self.connection,branch='discussion',mode='plan')
  _validate(value);self.assertFalse(value['config']['grant']['allow_shell']);self.assertFalse(value['config']['grant'].get('project_files',False))
 def test_document_tool_card_explains_builtin_packages_and_real_page_review(self):
  schema={'oneOf':[{'properties':{'tool':{'enum':['build_pdf']}}},{'properties':{'tool':{'enum':['render_pdf']}}}]}
  text=continuation_input('Write a report.',schema)
  self.assertIn('ReportLab',text);self.assertIn('document.pdf',text);self.assertIn('render_pdf',text)
