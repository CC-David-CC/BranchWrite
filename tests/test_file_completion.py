"""Generic host file/readback completion; actual tools and subprocess CLI.

Synthetic CPU choices here test the driver. The real Q4 H00 run is separate.
"""
import copy,hashlib,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from branchwrite.execution import Executor,Grant
from branchwrite.tool_registry import ToolRegistry
from branchwrite.records import RuntimeLog
from branchwrite.kernel import FrameKernel
from branchwrite.interpreter import Interpreter,Value,AdmissionError

class FileCompletionTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.base=Path(self.temp.name)
  self.source=self.base/'source';self.source.mkdir()
  self.executor=Executor.create(self.source,self.base/'world')
  self.registry=ToolRegistry(self.executor,Grant(('note.txt',),False,read_paths=('note.txt',),create_paths=('note.txt',)))
  self.log=RuntimeLog(self.base/'log');self.addCleanup(self.close);self.kernel=FrameKernel(self.log)
  self.expected=b'Observed bytes.\n'
  self.spec=dict(schema=1,files=[dict(path='note.txt',sha256=hashlib.sha256(self.expected).hexdigest())])
 def close(self):
  if not self.log._closed:self.log.close()
 def runtime(self,spec=None):return Interpreter(self.kernel,self.registry,verification=self.spec if spec is None else spec)
 def program(self,actions=('create','read','finish')):
  parts=['FLOW files']
  for name in actions:parts.extend([f'PLAN p-{name} from={name} against=world -> plan',f'ACT a-{name} plan=plan -> outcome'])
  parts.extend(['VERIFY v input=outcome contract=file-readback-and-finish -> verified','END'])
  return '\n'.join(parts)+'\n'
 def bindings(self):
  return {name:Value('ToolProposal',json.dumps(dict(tool=tool,arguments=args))) for name,tool,args in [
   ('create','create_file',dict(path='note.txt',content=self.expected.decode())),
   ('read','read_file',dict(path='note.txt')),
   ('finish','finish',dict(answer=self.expected.decode()))]}
 def test_create_read_finish_without_test_grant_passes_actual_bytes(self):
  runtime=self.runtime();runtime.start(self.program(),self.bindings());result=runtime.run()
  self.assertTrue(result.value['verified']);self.assertEqual((self.executor.workspace/'note.txt').read_bytes(),self.expected)
  self.assertEqual(result.value['bindings']['verified'][1]['policy'],'file-readback-and-finish')
  self.assertFalse((self.source/'note.txt').exists())
 def test_create_observation_cannot_substitute_for_a_read(self):
  runtime=self.runtime();runtime.start(self.program(('create','finish')),self.bindings())
  self.assertFalse(runtime.run().value['verified'])
 def test_finish_claim_with_correct_file_but_no_tool_read_fails(self):
  (self.executor.workspace/'note.txt').write_bytes(self.expected)
  runtime=self.runtime();runtime.start(self.program(('finish',)),self.bindings())
  self.assertFalse(runtime.run().value['verified'])
 def test_wrong_expected_hash_fails(self):
  spec=copy.deepcopy(self.spec);spec['files'][0]['sha256']='0'*64
  runtime=self.runtime(spec);runtime.start(self.program(),self.bindings());self.assertFalse(runtime.run().value['verified'])
 def test_file_changed_after_read_fails(self):
  runtime=self.runtime();runtime.start(self.program(),self.bindings())
  while self.kernel.frame('program')['pc']<4:runtime.step()
  (self.executor.workspace/'note.txt').write_bytes(b'Changed outside the tool.\n')
  self.assertFalse(runtime.run().value['verified'])
 def test_scope_close_rechecks_bytes_after_verification(self):
  runtime=self.runtime();runtime.start(self.program(),self.bindings())
  while self.kernel.frame('program')['pc']<7:runtime.step()
  while self.kernel.frame('program')['state']=='Waiting':runtime.step()
  (self.executor.workspace/'note.txt').write_bytes(b'Changed after verification.\n')
  self.assertFalse(runtime.run().value['verified'])
 def test_host_policy_is_detached_and_changed_policy_cannot_resume(self):
  runtime=self.runtime();runtime.start(self.program(),self.bindings());saved=copy.deepcopy(self.spec)
  self.spec['files'][0]['sha256']='0'*64
  with self.assertRaisesRegex(AdmissionError,'identity changed|different program or inputs'):self.runtime().step()
  self.assertTrue(runtime.run().value['verified']);self.assertNotEqual(self.spec,saved)
 def test_invalid_or_ungranted_policy_is_rejected(self):
  bad=[dict(schema=True,files=self.spec['files']),dict(schema=1,files=[]),dict(schema=1,files=self.spec['files']*2),
   dict(schema=1,files=[dict(path='../note.txt',sha256='a'*64)]),dict(schema=1,files=[dict(path='other.txt',sha256='a'*64)]),
   dict(schema=1,files=[dict(path='note.txt',sha256='A'*64)]),dict(schema=1,files=self.spec['files'],accepted=True)]
  for spec in bad:
   with self.subTest(spec=spec),self.assertRaises((AdmissionError,ValueError)):self.runtime(spec)
 def test_read_in_another_run_cannot_verify(self):
  # A real read exists in this log, but it belongs to a different root.
  other=Interpreter(self.kernel,self.registry)
  foreign='FLOW other\nPLAN p from=read against=world -> plan\nACT read plan=plan\nEND\n'
  (self.executor.workspace/'note.txt').write_bytes(self.expected)
  other.start(foreign,{'read':self.bindings()['read']});other.run()
  # The new run has its own canonical kernel log; a read from the previous run
  # is deliberately not supplied as a verifier witness.
  self.close();self.log=RuntimeLog(self.base/'separate-log');self.kernel=FrameKernel(self.log)
  runtime=self.runtime();runtime.start(self.program(('finish',)),self.bindings());self.assertFalse(runtime.run().value['verified'])

 def test_successful_read_without_finish_is_not_completion(self):
  runtime=self.runtime();runtime.start(self.program(('create','read')),self.bindings())
  self.assertFalse(runtime.run().value['verified'])
 def test_missing_host_policy_rejected_at_program_preflight(self):
  runtime=Interpreter(self.kernel,self.registry)
  with self.assertRaisesRegex(AdmissionError,'host file verification policy required'):runtime.start(self.program(),self.bindings())
  self.assertEqual(self.kernel.frames(),())
 def test_closed_read_child_is_not_visible_until_parent_resumes(self):
  from branchwrite.tool_dispatch import tool_call,dispatch_tool
  runtime=self.runtime();runtime.start(self.program(('finish',)),self.bindings())
  (self.executor.workspace/'note.txt').write_bytes(self.expected)
  plan=self.registry.freeze(self.bindings()['read'].data)
  call=tool_call(self.kernel,self.registry,child_id='unjoined-read',attempt_id='attempt-read',slot='result',plan=plan)
  self.kernel.spawn('program',expected_epoch=0,calls=(call,),next_pc=1)
  dispatch_tool(self.kernel,self.registry,'unjoined-read')
  parent=self.kernel.frame('program');self.assertEqual(parent['state'],'Waiting')
  verdict=runtime._verification(dict(requested_finish=True),policy='file-readback-and-finish',frame=parent)
  self.assertEqual(verdict['status'],'fail')
  self.kernel.resume('program',parent['epoch'])
  verdict=runtime._verification(dict(requested_finish=True),policy='file-readback-and-finish',frame=self.kernel.frame('program'))
  self.assertEqual(verdict['status'],'pass')

class FileCompletionCliTests(unittest.TestCase):
 def test_real_cli_file_policy_and_separate_process_receipt_replay(self):
  with tempfile.TemporaryDirectory() as temp:
   base=Path(temp);source=base/'source';source.mkdir();program=base/'job.bw';config=base/'host.json';state=base/'run'
   text='A different task.\n'
   bindings={name:dict(type='ToolProposal',value=json.dumps(dict(tool=tool,arguments=args))) for name,tool,args in [
    ('write','create_file',dict(path='result.txt',content=text)),('read','read_file',dict(path='result.txt')),('done','finish',dict(answer=text))]}
   cfg=dict(schema=1,source=str(source),run_id='files-cli',grant=dict(edit_paths=[],read_paths=['result.txt'],create_paths=['result.txt'],allow_tests=False),bindings=bindings,profiles={},verification=dict(schema=1,files=[dict(path='result.txt',sha256=hashlib.sha256(text.encode()).hexdigest())]))
   config.write_text(json.dumps(cfg));program.write_text('FLOW task\nPLAN p from=write against=world -> plan\nACT write plan=plan\nPLAN r from=read against=world -> plan\nACT read plan=plan\nPLAN f from=done against=world -> plan\nACT finish plan=plan -> outcome\nVERIFY check input=outcome contract=file-readback-and-finish -> verified\nEND\n')
   command=[sys.executable,'-B','-m','branchwrite','run',str(program),'--config',str(config),'--state',str(state)]
   first=subprocess.run(command,capture_output=True,text=True,timeout=20);self.assertEqual(first.returncode,0,first.stderr)
   before={str(p.relative_to(state/'ledger')):p.read_bytes() for p in (state/'ledger').rglob('*') if p.is_file()}
   second=subprocess.run(command,capture_output=True,text=True,timeout=20);self.assertEqual(second.returncode,0,second.stderr);self.assertEqual(first.stdout,second.stdout)
   self.assertEqual(before,{str(p.relative_to(state/'ledger')):p.read_bytes() for p in (state/'ledger').rglob('*') if p.is_file()});self.assertFalse((source/'result.txt').exists())
 def test_file_only_prefix_does_not_demand_ungranted_tests(self):
  from branchwrite.coding_defaults import system_prefix
  schema=dict(oneOf=[dict(properties=dict(tool=dict(enum=['read_file']))),dict(properties=dict(tool=dict(enum=['finish'])))] )
  prefix=system_prefix(schema);self.assertIn('no run_tests',prefix);self.assertNotIn('Only request finish after tests pass.',prefix)
