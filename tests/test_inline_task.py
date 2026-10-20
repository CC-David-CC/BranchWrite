"""Public inline-task input must preserve literal text and file compatibility."""
import contextlib,io,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from branchwrite.__main__ import main
from branchwrite.coding_cli import read_launch
class InlineTaskTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name);self.project=self.root/'project';self.project.mkdir()
  (self.project/'app.py').write_text('pass\n')
  self.task=self.root/'task.txt';self.task.write_text('Original file task\n')
  self.connection=self.root/'connection.json'
  self.connection.write_text(json.dumps(dict(endpoint_url='http://127.0.0.1:1',endpoint_pin='owned',model_contract_id='m',execution_profile_id='p',eos_tokens=[256])))
  self.state=self.root/'state'
 def invoke(self,task_args):
  args=['code',str(self.project),'--connection',str(self.connection),'--state',str(self.state),'--branch','new','--edit','app.py','--test-command','python3 -m unittest',*task_args]
  stdout=io.StringIO();stderr=io.StringIO()
  with patch('branchwrite.coding_cli.run_saved',return_value=(0,{'verified':True})) as run,contextlib.redirect_stdout(stdout),contextlib.redirect_stderr(stderr):
   try:code=main(args)
   except SystemExit as e:code=e.code
  return code,stdout.getvalue(),stderr.getvalue(),run
 def test_inline_task_is_preserved_exactly(self):
  text="Inspect café's $HOME; do not expand $(echo hi).\nSecond line.\n"
  code,out,err,run=self.invoke(['--task',text])
  self.assertEqual(code,0,err);run.assert_called_once()
  self.assertEqual(read_launch(self.state)['config']['bindings']['task']['value'],text)
 def test_file_task_still_works_and_is_unchanged(self):
  code,out,err,run=self.invoke(['--task-file',str(self.task)])
  self.assertEqual(code,0,err);run.assert_called_once()
  self.assertEqual(read_launch(self.state)['config']['bindings']['task']['value'],self.task.read_text())
 def test_both_input_forms_are_rejected_before_state(self):
  code,out,err,run=self.invoke(['--task-file',str(self.task),'--task','Inline'])
  self.assertEqual(code,2);self.assertIn('not allowed',err)
  self.assertFalse(self.state.exists());run.assert_not_called()
 def test_missing_input_is_rejected_before_state(self):
  code,out,err,run=self.invoke([])
  self.assertEqual(code,2);self.assertFalse(self.state.exists());run.assert_not_called()
 def test_blank_inline_task_uses_existing_task_validation(self):
  code,out,err,run=self.invoke(['--task','   '])
  self.assertEqual(code,2);self.assertIn('bounded nonempty task',err)
  self.assertFalse(self.state.exists());run.assert_not_called()
 def test_inline_text_is_never_executed(self):
  marker=self.root/'executed'
  text='$(touch '+str(marker)+'); __import__("os").system("false")'
  code,out,err,run=self.invoke(['--task',text])
  self.assertEqual(code,0,err);self.assertFalse(marker.exists())
  self.assertEqual(read_launch(self.state)['config']['bindings']['task']['value'],text)
