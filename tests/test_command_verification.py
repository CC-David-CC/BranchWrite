"""Required command work must be proved by canonical tool outcomes."""
from pathlib import Path
import tempfile,unittest
from branchwrite.execution import Executor,Grant
from branchwrite.terminal import ShellConfig
from branchwrite.tool_registry import ToolRegistry
from branchwrite.records import RuntimeLog

class CommandVerificationTests(unittest.TestCase):
 def test_finish_claim_without_actual_command_cannot_verify(self):
  from branchwrite.verification import CommandEvidencePolicy
  with tempfile.TemporaryDirectory() as td:
   base=Path(td);source=base/'source';source.mkdir()
   executor=Executor.create(source,base/'world',shell=ShellConfig(timeout=1))
   registry=ToolRegistry(executor,Grant((),False,allow_shell=True))
   spec=dict(schema=1,commands=[dict(command='printf verified',disposition='exited',exit_code=0)])
   policy=CommandEvidencePolicy.admit(spec,registry)
   with RuntimeLog(base/'ledger') as log:
    result=policy.verify(registry,log,())
   self.assertEqual(result['status'],'fail')
 def test_dispositions_and_exit_status_are_not_interchangeable_at_admission(self):
  from branchwrite.verification import CommandEvidencePolicy
  with tempfile.TemporaryDirectory() as td:
   base=Path(td);source=base/'source';source.mkdir()
   registry=ToolRegistry(Executor.create(source,base/'world',shell=ShellConfig(timeout=1)),Grant((),False,allow_shell=True))
   for disposition,code in [('timeout',0),('spawn_error',0),('exited',None),('success',0)]:
    with self.subTest(disposition=disposition,code=code),self.assertRaises(ValueError):
     CommandEvidencePolicy.admit(dict(schema=1,commands=[dict(command='printf verified',disposition=disposition,exit_code=code)]),registry)

class CommandWorkflowTests(unittest.TestCase):
 def run_case(self,command,expected_command=None,*,run_command=True,mutate=False,expected_disposition="exited",expected_exit=0):
  import json
  from branchwrite.kernel import FrameKernel
  from branchwrite.interpreter import Interpreter,Value
  with tempfile.TemporaryDirectory() as td:
   base=Path(td);source=base/'source';source.mkdir();(source/'marker').write_text('original')
   executor=Executor.create(source,base/'world',shell=ShellConfig(timeout=.2))
   registry=ToolRegistry(executor,Grant((),False,read_paths=('marker',),allow_shell=True))
   verification=dict(schema=1,commands=[dict(command=expected_command or command,disposition=expected_disposition,exit_code=expected_exit)])
   with RuntimeLog(base/'ledger') as log:
    kernel=FrameKernel(log);runtime=Interpreter(kernel,registry,verification=verification)
    text='FLOW task\n'
    if run_command:text+='PLAN p from=command against=world -> plan\nACT c plan=plan -> outcome\n'
    text+='PLAN f from=finish against=world -> plan\nACT done plan=plan -> outcome\nVERIFY check input=outcome contract=command-evidence-and-finish -> verified\nEND\n'
    bindings=dict(command=Value('ToolProposal',json.dumps(dict(tool='run_shell',arguments=dict(command=command)))),finish=Value('ToolProposal',json.dumps(dict(tool='finish',arguments=dict(answer='claimed complete')))))
    runtime.start(text,bindings)
    if mutate:
     while kernel.frame('program')['pc']<2 or kernel.frame('program')['state']=='Waiting':runtime.step()
     (executor.workspace/'marker').write_text('changed after command')
    return runtime.run().value['verified']
 def test_actual_command_and_finish_pass_without_expected_artifact_hash(self):
  self.assertTrue(self.run_case('printf verified'))
 def test_no_command_cannot_finish(self):
  self.assertFalse(self.run_case('printf verified',run_command=False))
 def test_different_command_does_not_satisfy_requirement(self):
  self.assertFalse(self.run_case('printf different','printf verified'))
 def test_current_workspace_change_invalidates_prior_command(self):
  self.assertFalse(self.run_case('printf verified',mutate=True))

 def test_nonzero_exit_does_not_satisfy_success(self):
  self.assertFalse(self.run_case('exit 7'))
 def test_actual_timeout_is_only_accepted_when_required(self):
  command="trap 'exit 143' TERM; sleep 30 & wait"
  self.assertTrue(self.run_case(command,expected_disposition='timeout',expected_exit=143))
  self.assertFalse(self.run_case(command))

class CommandCliTests(unittest.TestCase):
 def test_real_cli_requires_command_and_replays_without_new_effects(self):
  import json,os,subprocess,sys
  with tempfile.TemporaryDirectory() as td:
   base=Path(td);source=base/'source';source.mkdir();(source/'input.txt').write_text('fixture')
   config=dict(schema=1,source=str(source),run_id='command-cli',grant=dict(edit_paths=[],create_paths=[],read_paths=['input.txt'],allow_tests=False,allow_shell=True),shell=dict(timeout=1),profiles={},bindings=dict(command=dict(type='ToolProposal',value=json.dumps(dict(tool='run_shell',arguments=dict(command='printf observed')))),finish=dict(type='ToolProposal',value=json.dumps(dict(tool='finish',arguments=dict(answer='done'))))),verification=dict(schema=1,commands=[dict(command='printf observed',disposition='exited',exit_code=0)]))
   cfg=base/'host.json';cfg.write_text(json.dumps(config));program=base/'task.bw'
   program.write_text('FLOW task\nPLAN p from=command against=world -> plan\nACT c plan=plan -> outcome\nPLAN f from=finish against=world -> plan\nACT done plan=plan -> outcome\nVERIFY v input=outcome contract=command-evidence-and-finish -> verified\nEND\n')
   argv=[sys.executable,'-B','-m','branchwrite','run',str(program),'--config',str(cfg),'--state',str(base/'run')]
   first=subprocess.run(argv,capture_output=True,text=True,timeout=20)
   self.assertEqual(first.returncode,0,first.stderr)
   self.assertTrue(json.loads(first.stdout)['verified'])
   ledger=base/'run/ledger';before={str(p.relative_to(ledger)):p.read_bytes() for p in ledger.rglob('*') if p.is_file()}
   second=subprocess.run(argv,capture_output=True,text=True,timeout=20)
   self.assertEqual(second.returncode,0,second.stderr);self.assertEqual(first.stdout,second.stdout)
   self.assertEqual(before,{str(p.relative_to(ledger)):p.read_bytes() for p in ledger.rglob('*') if p.is_file()})
 def test_cli_policy_checks_actual_published_command_output(self):
  import json
  from branchwrite.kernel import FrameKernel
  from branchwrite.interpreter import Interpreter,Value
  with tempfile.TemporaryDirectory() as td:
   base=Path(td);source=base/'source';source.mkdir();(source/'out.txt').write_text('old')
   executor=Executor.create(source,base/'world',shell=ShellConfig(timeout=1))
   registry=ToolRegistry(executor,Grant((),False,read_paths=('out.txt',),allow_shell=True,output_paths=('out.txt',)))
   command="printf new > out.txt"
   with RuntimeLog(base/'ledger') as log:
    kernel=FrameKernel(log);runtime=Interpreter(kernel,registry,verification=dict(schema=1,commands=[dict(command=command,disposition='exited',exit_code=0)]))
    program='FLOW task\nPLAN p from=command against=world -> plan\nACT c plan=plan -> outcome\nPLAN f from=finish against=world -> plan\nACT done plan=plan -> outcome\nVERIFY v input=outcome contract=command-evidence-and-finish -> verified\nEND\n'
    runtime.start(program,dict(command=Value('ToolProposal',json.dumps(dict(tool='run_shell',arguments=dict(command=command)))),finish=Value('ToolProposal',json.dumps(dict(tool='finish',arguments=dict(answer='done'))))))
    self.assertTrue(runtime.run().value['verified'])
    self.assertEqual((executor.workspace/'out.txt').read_bytes(),b'new')
