"""Progress is cosmetic, emitted by the owner, and never workflow authority."""
import contextlib,hashlib,io,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from branchwrite.execution import Executor,Grant
from branchwrite.tool_registry import ToolRegistry
from branchwrite.records import RuntimeLog
from branchwrite.kernel import FrameKernel
from branchwrite.interpreter import Interpreter,Value,AdmissionError
class ProgressTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name);source=self.root/'source';source.mkdir()
  self.executor=Executor.create(source,self.root/'world')
  self.registry=ToolRegistry(self.executor,Grant((),False,read_paths=('new.txt',),create_paths=('new.txt',)))
  self.log=RuntimeLog(self.root/'ledger');self.addCleanup(self.log.close)
  self.kernel=FrameKernel(self.log)
 def start(self,progress):
  r=Interpreter(self.kernel,self.registry,progress=progress)
  r.start('FLOW work\nPLAN p from=request against=world -> plan\nACT a plan=plan -> outcome\nEND\n',
   {'request':Value('ToolProposal',json.dumps(dict(tool='create_file',arguments=dict(path='new.txt',content='PRIVATE-CONTENT'))))})
  return r
 def test_tool_progress_brackets_real_effect_without_payload(self):
  events=[]
  def observe(event):
   events.append((event,(self.executor.workspace/'new.txt').exists()))
  runtime=self.start(observe)
  self.assertEqual(runtime.run(max_steps=32).status,'complete')
  self.assertIn(('tool_started',False),events)
  self.assertIn(('tool_returned',True),events)
  self.assertTrue(all(type(e) is str and 'PRIVATE' not in e for e,_ in events))
 def test_broken_observer_does_not_abort_or_repeat_effect(self):
  events=[]
  def broken(event):
   events.append(event);raise BrokenPipeError('closed progress display')
  runtime=self.start(broken)
  self.assertEqual(runtime.run(max_steps=32).status,'complete')
  self.assertEqual((self.executor.workspace/'new.txt').read_text(),'PRIVATE-CONTENT')
  self.assertEqual(events,['tool_started'])
 def test_invalid_observer_rejected_before_admission(self):
  with self.assertRaises(AdmissionError):
   Interpreter(self.kernel,self.registry,progress=42)
  self.assertEqual(self.log.event_count,0)
 def test_observer_not_in_identity_and_completed_reopen_is_quiet(self):
  plain=Interpreter(self.kernel,self.registry)
  runtime=self.start(lambda _:None)
  self.assertEqual(plain.identity,runtime.identity)
  runtime.run(max_steps=32)
  events=[];reopened=Interpreter(self.kernel,self.registry,progress=events.append)
  self.assertEqual(reopened.run(max_steps=32).status,'complete')
  self.assertEqual(events,[])
 def test_cli_stderr_progress_preserves_json_stdout_and_offline_reopen(self):
  source=self.root/'cli-source';source.mkdir()
  config=dict(schema=1,source=str(source),run_id='progress-cli',
   grant=dict(edit_paths=[],read_paths=['new.txt'],create_paths=['new.txt'],allow_tests=False),
   bindings=dict(request=dict(type='ToolProposal',value=json.dumps(dict(tool='create_file',arguments=dict(path='new.txt',content='PRIVATE-CONTENT'))))))
  conf=self.root/'host.json';conf.write_text(json.dumps(config))
  program=self.root/'work.bw';program.write_text('FLOW work\nPLAN p from=request against=world -> plan\nACT a plan=plan -> outcome\nEND\n')
  command=[sys.executable,'-B','-m','branchwrite','run',str(program),'--config',str(conf),'--state',str(self.root/'cli-state')]
  p=subprocess.run(command,capture_output=True,text=True)
  self.assertEqual(p.returncode,1,p.stderr)
  self.assertEqual(json.loads(p.stdout)['status'],'complete')
  self.assertIn('[BranchWrite] Running a tool.',p.stderr)
  self.assertIn('[BranchWrite] Tool result recorded.',p.stderr)
  self.assertNotIn('PRIVATE-CONTENT',p.stderr)
  again=subprocess.run(command,capture_output=True,text=True)
  self.assertEqual(again.stdout,p.stdout)
  self.assertEqual(again.stderr,'')
