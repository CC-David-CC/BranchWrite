"""Actual isolated build failures must explain their host export contract."""
import tempfile,unittest
from pathlib import Path
from branchwrite.pdf_execution import PdfRuntime,build_document

class PdfBuildDiagnosticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.runtime=PdfRuntime()
    def test_successful_child_with_wrong_filename_names_required_pdf(self):
        result=build_document((('report.py',b"from pathlib import Path;Path('other.pdf').write_bytes(b'%PDF-placeholder')"),),'report.py',self.runtime)
        self.assertEqual(result['disposition'],'missing_artifact')
        self.assertEqual(result['exit_code'],0)
        self.assertIsNone(result['pdf'])
        self.assertIn(b'document.pdf',result['stderr'])
        self.assertIn(b'BranchWrite',result['stderr'])
    def test_rejected_empty_output_has_export_diagnostic(self):
        result=build_document((('report.py',b"from pathlib import Path;Path('document.pdf').write_bytes(b'')"),),'report.py',self.runtime)
        self.assertEqual(result['disposition'],'output_rejected')
        self.assertIsNone(result['pdf'])
        self.assertIn(b'document.pdf',result['stderr'])
        self.assertIn(b'nonempty',result['stderr'])

class PdfModelFeedbackIntegrationTests(unittest.TestCase):
 def test_real_wrong_filename_failure_reaches_next_model_input(self):
  import json
  from branchwrite.execution import Executor,Grant
  from branchwrite.tool_registry import ToolRegistry
  from branchwrite.pdf_tools import PdfCapability
  from branchwrite.records import RuntimeLog
  from branchwrite.kernel import FrameKernel
  from branchwrite.interpreter import Interpreter,Value
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);source=root/'source';source.mkdir()
   (source/'report.py').write_text("from pathlib import Path;Path('wrong.pdf').write_bytes(b'%PDF-placeholder')")
   executor=Executor.create(source,root/'world')
   registry=ToolRegistry(executor,Grant((),False,project_files=True),pdf=PdfCapability())
   with RuntimeLog(root/'ledger') as log:
    runtime=Interpreter(FrameKernel(log),registry)
    runtime.start('FLOW pdf\nPLAN p from=proposal against=world -> plan\nACT a plan=plan -> outcome\nTRANSFORM f contract=tool-feedback input=outcome -> feedback\nEND\n',
     {'proposal':Value('ToolProposal',json.dumps(dict(tool='build_pdf',arguments=dict(path='report.py',output='reports/dogs.pdf'))))})
    result=runtime.run();self.assertEqual(result.status,'complete')
    view=json.loads(result.value['bindings']['feedback'][1])
    self.assertEqual(view['disposition'],'pdf_failed')
    self.assertEqual(view['problem']['stage'],'missing_artifact')
    self.assertIn('document.pdf',view['stderr'])
    self.assertIn('document.pdf',view['problem']['next_action'])
    self.assertFalse((executor.workspace/'reports/dogs.pdf').exists())
