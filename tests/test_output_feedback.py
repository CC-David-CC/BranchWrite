"""Exact raw output artifacts versus bounded, explicitly decoded model views."""
from pathlib import Path
import hashlib,json,os,shlex,subprocess,sys,tempfile,unittest
from unittest.mock import patch
from branchwrite.execution import Executor,Grant
from branchwrite.terminal import ShellConfig
from branchwrite.tool_registry import ToolRegistry
from branchwrite.records import RuntimeLog,Artifact
from branchwrite.kernel import FrameKernel
from branchwrite.interpreter import Interpreter,Value

class OutputFeedbackTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
  source=self.root/'source';source.mkdir()
  self.executor=Executor.create(source,self.root/'world',shell=ShellConfig(timeout=3,expected_hostname=os.uname().nodename))
  self.registry=ToolRegistry(self.executor,Grant((),False,allow_shell=True))
  self.log=RuntimeLog(self.root/'ledger');self.addCleanup(self.close)
 def close(self):
  if not self.log._closed:self.log.close()
 def run_output(self,out,err=b'',code=7):
  command=shlex.join(['/usr/bin/python3','-I','-B','-c','import os;os.write(1,'+repr(out)+');os.write(2,'+repr(err)+');raise SystemExit('+str(code)+')'])
  # Large literal test data is generated within a bounded shell request.
  if len(command)>16000:
   command=shlex.join(['/usr/bin/python3','-I','-B','-c',"import os;os.write(1,b'x'*32767+'Δ'.encode()+b'end');raise SystemExit(7)"])
  self.command=command
  self.program='FLOW view\nPLAN freeze from=probe against=world -> plan\nACT execute plan=plan -> outcome\nTRANSFORM display contract=tool-feedback input=outcome -> view\nEND\n'
  self.bindings=dict(probe=Value('ToolProposal',json.dumps(dict(tool='run_shell',arguments=dict(command=command)))))
  runtime=Interpreter(FrameKernel(self.log),self.registry);runtime.start(self.program,self.bindings);result=runtime.run()
  self.assertEqual(result.status,'complete')
  self.outcome=result.value['bindings']['outcome'][1]
  return json.loads(result.value['bindings']['view'][1])
 def assert_raw(self,field,body,feedback):
  ref=Artifact(*self.outcome[field]);self.assertEqual(self.log.read_artifact(ref),body)
  self.assertEqual(feedback[field+'_artifact'],dict(sha256=hashlib.sha256(body).hexdigest(),bytes=len(body)))
 def test_binary_stdout_stderr_have_exact_artifacts_and_explicit_lossy_views(self):
  out=b'A\xff\0B';err=b'err\xfe';view=self.run_output(out,err)
  self.assert_raw('stdout',out,view);self.assert_raw('stderr',err,view)
  self.assertEqual(view['exit_code'],7);self.assertEqual(view['stdout'],'A\ufffd\0B')
  self.assertEqual(view['stderr'],'err\ufffd')
  for field,body in [('stdout',out),('stderr',err)]:
   self.assertEqual(view[field+'_display'],dict(encoding='utf-8',errors='replace',lossy=True,source_bytes=len(body)))
   self.assertFalse(view[field+'_truncated'])
 def test_literal_replacement_character_is_not_misclassified_as_invalid_utf8(self):
  body='\ufffd Δ\n'.encode();view=self.run_output(body,code=0)
  self.assert_raw('stdout',body,view);self.assertEqual(view['stdout'],body.decode())
  self.assertEqual(view['stdout_display'],dict(encoding='utf-8',errors='replace',lossy=False,source_bytes=len(body)))
  self.assertEqual(view['stderr_display'],dict(encoding='utf-8',errors='replace',lossy=False,source_bytes=0))
 def test_truncation_inside_multibyte_character_is_explicit_and_raw_stays_complete(self):
  body=b'x'*32767+'Δ'.encode()+b'end';view=self.run_output(body)
  self.assert_raw('stdout',body,view);self.assertEqual(view['stdout'],'x'*32767+'\ufffd')
  self.assertTrue(view['stdout_truncated'])
  self.assertEqual(view['stdout_display'],dict(encoding='utf-8',errors='replace',lossy=True,source_bytes=32768))
  self.assertFalse(view['stderr_truncated'])
 def test_small_valid_streams_keep_existing_text_and_status_fields(self):
  view=self.run_output(b'ordinary output\n',b'diagnostic output\n',7)
  self.assertEqual((view['stdout'],view['stderr'],view['exit_code']),('ordinary output\n','diagnostic output\n',7))
  self.assertFalse(view['stdout_display']['lossy']);self.assertFalse(view['stderr_display']['lossy'])
 def test_completed_reopen_uses_original_raw_artifacts_without_reexecution(self):
  view=self.run_output(b'raw\xff',b'error\xfe')
  before={str(f.relative_to(self.root/'ledger')):f.read_bytes() for f in (self.root/'ledger').rglob('*') if f.is_file()}
  self.close();self.log=RuntimeLog(self.root/'ledger')
  runtime=Interpreter(FrameKernel(self.log),self.registry);runtime.start(self.program,self.bindings)
  with patch.object(self.executor,'run_shell',side_effect=AssertionError('completed tool must not run again')):
   result=runtime.run()
  self.assertEqual(json.loads(result.value['bindings']['view'][1]),view)
  self.assertEqual(before,{str(f.relative_to(self.root/'ledger')):f.read_bytes() for f in (self.root/'ledger').rglob('*') if f.is_file()})

 def test_shell_feedback_binds_exact_executed_command_to_its_real_status(self):
  view=self.run_output(b'printed success does not mean status zero\n',code=19)
  self.assertEqual(view['command'],self.command)
  self.assertEqual(view['exit_code'],19)
  self.assertEqual(view['plan_sha256'],self.outcome['plan_sha256'])
  self.assertEqual(view['operation_id'],self.outcome['operation_id'])
 def test_command_provenance_does_not_decode_or_requote_shell_program(self):
  body=b'raw\xff\0';view=self.run_output(body,b'err\xfe',code=23)
  self.assertEqual(view['command'],self.command)
  self.assertIn("'import os;",view['command'])
  self.assertIn("\\xff",view['command'])
  self.assertEqual(view['exit_code'],23);self.assert_raw('stdout',body,view)

class OutputFeedbackHttpTests(unittest.TestCase):
 def test_actual_remote_model_history_receives_safe_view_and_exact_raw_identities(self):
  # Actual CLI/HTTP/tools with explicitly scripted CPU model choices, not GPU.
  import test_cow_client_flow as fixture
  from collections import defaultdict
  from branchwrite.coding_defaults import workflow_source
  case=fixture.CowClientFlowTests();self.addCleanup(case.doCleanups);case.setUp()
  root=Path(case.temp.name);source=root/'source';source.mkdir();(source/'keep.txt').write_bytes(b'unchanged\n')
  command=shlex.join(['/usr/bin/python3','-I','-B','-c',"import os;os.write(1,b'out\\xff');os.write(2,b'err\\xfe');raise SystemExit(7)"])
  actions=[dict(tool='run_shell',arguments=dict(command=command)),dict(tool='read_file',arguments=dict(path='keep.txt')),dict(tool='finish',arguments=dict(answer='actual nonzero probe observed'))]
  stream=iter(tuple(json.dumps(v).encode())+(299,) for v in actions)
  case.models[0].plans=defaultdict(lambda:next(stream))
  cfg=dict(schema=1,source=str(source),run_id='binary-feedback',grant=dict(edit_paths=[],read_paths=['keep.txt'],create_paths=[],allow_tests=False,allow_shell=True),shell=dict(timeout=3,expected_hostname=os.uname().nodename),
   profiles=dict(control=dict(output_format='text',settings=dict(temperature=0),request_tokens=1024)),bindings=dict(task=dict(type='Text',value='Run the binary stream probe, read keep.txt and finish.')),
   verification=dict(schema=1,files=[dict(path='keep.txt',sha256=hashlib.sha256(b'unchanged\n').hexdigest())]),
   cow=dict(endpoint_url=case.base_url,endpoint_pin='flow-model-free',model_contract_id='flow-model',execution_profile_id='flow-profile',eos_tokens=[299],branch='binary-feedback',mode='ask',bootstrap='coding'))
  config=root/'host.json';config.write_text(json.dumps(cfg));program=root/'job.bw';program.write_text(workflow_source().replace('contract=unit-tests-and-finish','contract=file-readback-and-finish'))
  cmd=[sys.executable,'-B','-m','branchwrite','run',str(program),'--config',str(config),'--state',str(root/'run')]
  done=subprocess.run(cmd,capture_output=True,env={**os.environ,'BW_COW_API_KEY':'cpu-flow-secret'},timeout=20)
  self.assertEqual(done.returncode,0,done.stderr);self.assertTrue(json.loads(done.stdout)['verified'])
  history=case._client('http','inspect-binary-feedback').history('binary-feedback');views=[]
  for message in history.messages:
   try:value=json.loads(message['text'])
   except (ValueError,TypeError):continue
   if type(value) is dict and value.get('tool')=='run_shell' and 'stdout_display' in value:views.append(value)
  self.assertEqual(len(views),1);view=views[0]
  for field,body,text in [('stdout',b'out\xff','out\ufffd'),('stderr',b'err\xfe','err\ufffd')]:
   self.assertEqual(view[field],text)
   self.assertEqual(view[field+'_artifact'],dict(bytes=len(body),sha256=hashlib.sha256(body).hexdigest()))
   self.assertEqual(view[field+'_display'],dict(encoding='utf-8',errors='replace',lossy=True,source_bytes=len(body)))
  self.assertEqual(view['command'],command)
  self.assertRegex(view['plan_sha256'],'^[0-9a-f]{64}$')
  self.assertEqual(view['exit_code'],7);self.assertEqual(len(case.trace),3)
  case._stop_server()
  again=subprocess.run(cmd,capture_output=True,env={**os.environ,'BW_COW_API_KEY':'cpu-flow-secret'},timeout=20)
  self.assertEqual((again.returncode,again.stdout),(done.returncode,done.stdout),again.stderr)

if __name__=='__main__':unittest.main()
