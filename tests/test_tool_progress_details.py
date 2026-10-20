"""Progress labels come from frozen tool names, never arbitrary arguments."""
import contextlib,io,json,unittest
from branchwrite.records import encode
from branchwrite.tool_progress import tool_start_event,detail_message

class ToolProgressDetailTests(unittest.TestCase):
 def test_only_closed_tool_names_are_displayed(self):
  from branchwrite.tool_registry import _TOOLS
  for tool in _TOOLS:
   event=tool_start_event(encode(('bw.tool-plan.v2','registry','world',tool,{'command':'PRIVATE\x1b[2J','path':'secret-key'},None,None,None)),'registry','world')
   self.assertEqual(event,'tool_started/'+tool)
   self.assertIsInstance(detail_message(event),str)
   self.assertNotIn('PRIVATE',detail_message(event))
   self.assertNotIn('secret',detail_message(event))
  self.assertIsNone(detail_message('tool_started/PRIVATE\x1b[2J'))
 def test_wrong_world_definition_or_malformed_plan_has_no_label(self):
  for value in [(),('bw.tool-plan.v1','registry','world','read_file',None,None,None,None),('bw.tool-plan.v2','other','world','read_file',None,None,None,None),('bw.tool-plan.v2','registry','other','read_file',None,None,None,None),('bw.tool-plan.v2','registry','world','PRIVATE',None,None,None,None)]:
   self.assertIsNone(tool_start_event(encode(value),'registry','world'))
  self.assertIsNone(tool_start_event(b'not canonical','registry','world'))
 def test_detail_brackets_real_effect_and_excludes_file_payload(self):
  from test_progress import ProgressTests
  case=ProgressTests();case.setUp();self.addCleanup(case.doCleanups)
  events=[]
  runtime=case.start(lambda event:events.append((event,(case.executor.workspace/'new.txt').exists())))
  self.assertEqual(runtime.run(max_steps=32).status,'complete')
  self.assertIn(('tool_started/create_file',False),events)
  self.assertLess(events.index(('tool_started/create_file',False)),events.index(('tool_returned',True)))
  self.assertFalse(any('PRIVATE' in event for event,_ in events))
 def test_interactive_output_is_specific_without_generic_duplicate(self):
  from branchwrite.interactive_session import SessionService
  service=object.__new__(SessionService);output=[];service._emit=output.append
  service._progress('tool_started');service._progress('tool_started/run_check');service._progress('tool_returned')
  self.assertEqual(output,['Running a project check...','Tool result saved.'])
  service._progress('tool_started/PRIVATE\x1b[2J');self.assertEqual(len(output),2)
 def test_noninteractive_detail_stays_on_stderr(self):
  from branchwrite.run_cli import _progress_notice
  out=io.StringIO();err=io.StringIO()
  with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):_progress_notice('tool_started/upload_file')
  self.assertEqual(out.getvalue(),'');self.assertIn('Uploading a project file...',err.getvalue())
