"""Current PDF completion uses canonical actual page receipts, not model claims."""
import copy,json,tempfile,unittest
from pathlib import Path
from branchwrite.execution import Executor,Grant
from branchwrite.terminal import ShellConfig
from branchwrite.tool_registry import ToolRegistry
from branchwrite.kernel import FrameKernel
from branchwrite.records import RuntimeLog
from branchwrite.interpreter import Interpreter,Value
from branchwrite.verification import ProjectChecksPolicy,ReadOnlyPolicy
from test_pdf_execution import SOURCE

class PdfCompletionTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  from branchwrite.pdf_tools import PdfCapability
  cls.cap=PdfCapability()
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  source=self.root/'source';source.mkdir();(source/'report.py').write_bytes(SOURCE)
  self.executor=Executor.create(source,self.root/'world',shell=ShellConfig(timeout=3),project_input=True)
  self.registry=ToolRegistry(self.executor,Grant((),False,allow_shell=True,project_files=True),pdf=self.cap)
 def execute(self,actions,mutate_after=None):
  bindings={};program='FLOW document\n'
  for i,(tool,args) in enumerate(actions):
   bindings['p'+str(i)]=Value('ToolProposal',json.dumps(dict(tool=tool,arguments=args)))
   program+='PLAN p'+str(i)+' from=p'+str(i)+' against=world -> plan\nACT a'+str(i)+' plan=plan -> outcome\n'
  bindings['done']=Value('ToolProposal',json.dumps(dict(tool='finish',arguments=dict(answer='done'))))
  program+='PLAN end from=done against=world -> plan\nACT finish plan=plan -> outcome\nVERIFY check input=outcome contract=project-checks-and-finish -> verified\nEND\n'
  with RuntimeLog(self.root/'ledger') as log:
   kernel=FrameKernel(log);runtime=Interpreter(kernel,self.registry,verification=dict(schema=1,selected_checks=True))
   runtime.start(program,bindings)
   if mutate_after is not None:
    number,source=mutate_after
    while kernel.frame('program')['pc']<number*2 or kernel.frame('program')['state']=='Waiting':runtime.step()
    (self.executor.workspace/'report.py').write_bytes(source)
   result=runtime.run();self.outcomes=tuple(runtime._visible_tool_outcomes(kernel.frame('program')))
   return result.value['verified']
 def build(self):return ('build_pdf',dict(path='report.py',output='report.pdf'))
 def page(self,n):return ('render_pdf',dict(path='report.pdf',page=n))
 def check(self):return ('run_check',dict(name='pdf-file',command='test -s report.pdf'))
 def verdict(self,outcomes=None):
  with RuntimeLog(self.root/'ledger') as log:
   return ProjectChecksPolicy().verify(self.registry,log,self.outcomes if outcomes is None else outcomes)
 def test_passing_file_check_cannot_hide_an_unrendered_page(self):
  self.assertFalse(self.execute([self.build(),self.check()]))
  self.assertEqual(self.verdict()['pdf_documents'][0]['missing_pages'],[2])
 def test_every_current_page_and_a_current_named_check_can_pass(self):
  self.assertTrue(self.execute([self.build(),self.page(2),self.check()]))
  self.assertEqual(self.verdict()['pdf_documents'][0]['rendered_pages'],[1,2])
 def test_edit_after_build_invalidates_document_even_with_new_file_check(self):
  self.assertFalse(self.execute([self.build(),self.page(2),self.check()],mutate_after=(1,SOURCE+b'\n# changed construction\n')))
 def test_rebuild_cannot_reuse_page_receipts_from_old_pdf(self):
  new=SOURCE.replace(b'Measurements',b'New Measurements')
  self.assertFalse(self.execute([self.build(),self.page(2),self.build(),self.check()],mutate_after=(2,new)))
  self.assertEqual(self.verdict()['pdf_documents'][0]['missing_pages'],[2])
 def test_canonical_receipt_and_page_artifact_cannot_be_forged(self):
  self.assertTrue(self.execute([self.build(),self.page(2),self.check()]))
  forged=copy.deepcopy(self.outcomes)
  for frame,value in forged:
   if value['tool']=='render_pdf':value['details']['page']=1
  self.assertEqual(self.verdict(forged)['status'],'fail')
 def test_reopened_ledger_revalidates_same_actual_page_evidence(self):
  self.assertTrue(self.execute([self.build(),self.page(2),self.check()]))
  with RuntimeLog(self.root/'ledger') as log:
   kernel=FrameKernel(log);runtime=Interpreter(kernel,self.registry,verification=dict(schema=1,selected_checks=True))
   rows=tuple(runtime._visible_tool_outcomes(kernel.frame('program')))
   self.assertEqual(ProjectChecksPolicy().verify(self.registry,log,rows)['status'],'pass')
 def test_latest_failed_build_cannot_accept_previous_preserved_pdf(self):
  self.assertFalse(self.execute([self.build(),self.page(2),self.build(),self.check()],mutate_after=(2,b'raise RuntimeError("broken revision")')))
  self.assertTrue(self.executor._read_private_bytes('report.pdf').startswith(b'%PDF-'))
 def test_readonly_policy_rejects_pdf_execution_capability(self):
  registry=ToolRegistry(self.executor,Grant(('report.py',),False),pdf=self.cap)
  with self.assertRaises(ValueError):ReadOnlyPolicy.admit(dict(schema=1,read_only=True),registry)
 def test_invalid_selected_page_is_an_explicit_tool_failure(self):
  plan=self.registry.freeze(json.dumps(dict(tool='build_pdf',arguments=dict(path='report.py',output='report.pdf'))))
  self.registry.execute(plan,'pdf-valid')
  plan=self.registry.freeze(json.dumps(dict(tool='render_pdf',arguments=dict(path='report.pdf',page=3))))
  outcome=self.registry.execute(plan,'pdf-outside')
  self.assertEqual(outcome.disposition,'pdf_failed');self.assertIn(b'outside',outcome.stderr)
 def test_cli_export_contains_pdf_and_actual_page_images(self):
  self.assertTrue(self.execute([self.build(),self.page(2),self.check()]))
  from branchwrite.run_cli import _artifact_exports
  with RuntimeLog(self.root/'ledger') as log:exports=_artifact_exports(log,self.outcomes)
  documents=[row for row in exports if row['media_type']=='application/pdf']
  self.assertTrue(documents);self.assertEqual(documents[0]['name'],'report.pdf')
  self.assertTrue(any(row['name']=='page-2.png' for row in exports))
  for row in exports:
   self.assertTrue(Path(row['path']).is_file());self.assertEqual(len(row['source_id']),64)
