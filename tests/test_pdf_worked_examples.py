"""Executable PDF teaching fixture; not live-model qualification."""
import re,subprocess,sys,tempfile,unittest
from pathlib import Path
from pypdf import PdfReader
from branchwrite.coding_defaults import system_prefix

class PdfWorkedExamplesTests(unittest.TestCase):
    def schema(self,name):
        return {'oneOf':[{'properties':{'tool':{'enum':[name]},'arguments':{'type':'object'}}}]}
    def test_pdf_teaching_is_present_only_with_actual_pdf_tool(self):
        taught=system_prefix(self.schema('build_pdf'))
        self.assertIn('PDF WORKED EXAMPLE',taught)
        self.assertNotIn('PDF WORKED EXAMPLE',system_prefix(self.schema('read_file')))
        self.assertIn('PageBreak()',taught)
        self.assertIn('paragraphs for long table cells',taught)
    def test_worked_source_builds_two_reopened_pages_and_footers(self):
        text=system_prefix(self.schema('build_pdf'))
        code=re.search(r'```python\n(.*?)```',text,re.S)
        self.assertIsNotNone(code,'teaching needs an executable complete source example')
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'write_example.py';p.write_text(code.group(1))
            result=subprocess.run([sys.executable,str(p)],cwd=tmp,text=True,capture_output=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr)
            pdf=PdfReader(Path(tmp)/'document.pdf')
            self.assertEqual(len(pdf.pages),2)
            for i,title in enumerate(['Before the visit','After the visit']):
                text=pdf.pages[i].extract_text()
                self.assertIn(title,text);self.assertIn('Page '+str(i+1),text)
