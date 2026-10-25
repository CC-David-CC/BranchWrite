"""Compact presentation over real shell/ledger receipts; no model or GPU fixture."""
from contextlib import contextmanager
from functools import partial
import copy,hashlib,json,os,shlex,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import test_output_feedback as output_fixture
import test_project_check_progress as check_fixture
from branchwrite.records import Artifact
from branchwrite.interpreter import Interpreter,AdmissionError,_compact_tool_feedback
from branchwrite.coding_cli import build_launch,save_launch,read_launch
from branchwrite.run_cli import _config

SPEC=dict(schema=1,format='compact-v1')


class CompactFeedbackTests(unittest.TestCase):
    @contextmanager
    def fixture(self):
        case=output_fixture.OutputFeedbackTests();case.setUp()
        try:
            with patch.object(output_fixture,'Interpreter',partial(Interpreter,tool_feedback=SPEC)):
                yield case
        finally:case.doCleanups()

    def test_binary_outputs_status_and_decoding_boundaries_are_exact(self):
        with self.fixture() as case:
            stdout=b'A\xff\0B';stderr=b'err\xfe';view=case.run_output(stdout,stderr,23)
            self.assertEqual(view['feedback_format'],'compact-v1')
            self.assertEqual((view['stdout'],view['stderr'],view['exit_code']),('A\ufffd\0B','err\ufffd',23))
            self.assertEqual(view['command'],case.command)
            self.assertEqual(view['operation_id'],case.outcome['operation_id'])
            for name,raw in (('stdout',stdout),('stderr',stderr)):
                self.assertEqual(case.log.read_artifact(Artifact(*case.outcome[name])),raw)
                self.assertEqual(view['streams'][name],dict(bytes=len(raw),shown_bytes=len(raw),lossy=True))
                self.assertFalse(view[name+'_truncated'])
                self.assertNotIn(name+'_artifact',view)
            self.assertEqual(view['decoding'],'utf-8/replace')
            self.assertIn('plan_sha256',case.outcome)
            self.assertNotIn('plan_sha256',view)
            self.assertIn('problem',view)
            self.assertIn('source_writes',view['shell_context'])

    def test_multibyte_truncation_never_becomes_a_full_or_lossless_stream(self):
        with self.fixture() as case:
            raw=b'x'*32767+'Δ'.encode()+b'end';view=case.run_output(raw)
            self.assertEqual(view['stdout'],'x'*32767+'\ufffd')
            self.assertEqual(view['streams']['stdout'],dict(bytes=len(raw),shown_bytes=32768,lossy=True))
            self.assertTrue(view['stdout_truncated'])
            self.assertEqual(case.log.read_artifact(Artifact(*case.outcome['stdout'])),raw)

    def test_projection_cannot_rewrite_its_input_or_preexisting_ledger_bytes(self):
        with self.fixture() as case:
            captures=[]
            def projection(full):
                original=copy.deepcopy(full)
                before={str(p):p.read_bytes() for p in (case.root/'ledger').rglob('*') if p.is_file()}
                view=_compact_tool_feedback(full)
                self.assertEqual(full,original)
                self.assertEqual(before,{str(p):p.read_bytes() for p in (case.root/'ledger').rglob('*') if p.is_file()})
                for key in ('operation_id','tool','disposition','exit_code','command','shell_context','diagnostic_guidance','problem','verification','observation','image','capture'):
                    if key in full:self.assertEqual(view[key],full[key])
                captures.append((full,view));return view
            with patch('branchwrite.interpreter._compact_tool_feedback',projection):
                view=case.run_output(b'output',b'Read-only file system; Permission denied',0)
            self.assertEqual(len(captures),1)
            self.assertEqual(view['exit_code'],0)
            self.assertIn('diagnostic_guidance',view)
            self.assertNotIn('problem',view)
            self.assertLess(len(json.dumps(view,separators=(',',':'))),len(json.dumps(captures[0][0],sort_keys=True)))

    def test_completed_compact_view_reopens_without_reexecution_or_changed_receipts(self):
        with self.fixture() as case:
            first=case.run_output(b'raw\xff',b'error\xfe')
            before={str(f.relative_to(case.root/'ledger')):f.read_bytes() for f in (case.root/'ledger').rglob('*') if f.is_file()}
            case.close()
            from branchwrite.records import RuntimeLog
            from branchwrite.kernel import FrameKernel
            case.log=RuntimeLog(case.root/'ledger')
            runtime=Interpreter(FrameKernel(case.log),case.registry,tool_feedback=SPEC)
            runtime.start(case.program,case.bindings)
            with patch.object(case.executor,'run_shell',side_effect=AssertionError('completed effect replayed')):
                result=runtime.run()
            self.assertEqual(json.loads(result.value['bindings']['view'][1]),first)
            self.assertEqual(before,{str(f.relative_to(case.root/'ledger')):f.read_bytes() for f in (case.root/'ledger').rglob('*') if f.is_file()})

    def checks(self,actions):
        case=check_fixture.ProjectCheckProgressTests()
        with patch.object(check_fixture,'Interpreter',partial(Interpreter,tool_feedback=SPEC)):
            return case.execute(actions)

    def test_a_passing_check_still_requires_finish_and_keeps_original_verification(self):
        case=check_fixture.ProjectCheckProgressTests()
        result,views=self.checks([case.check()])
        self.assertFalse(result['verified'])
        self.assertEqual(views[0]['verification']['status'],'fail')
        self.assertEqual(views[0]['verification']['check_status'],'pass')
        self.assertTrue(views[0]['verification']['finish_required'])
        finished,views=self.checks([case.check(),dict(tool='finish',arguments=dict(answer='checked marker'))])
        self.assertTrue(finished['verified'])
        self.assertEqual(views[-1]['verification']['status'],'pass')

    def test_stale_or_failed_checks_are_not_reclassified_as_success(self):
        case=check_fixture.ProjectCheckProgressTests()
        for actions in ([case.check('exit 7'),dict(tool='finish',arguments=dict(answer='not proven'))],
                [case.check(),dict(tool='read_file',arguments=dict(path='marker')),
                 dict(tool='replace',arguments=dict(path='marker',before='good',after='changed')),
                 dict(tool='finish',arguments=dict(answer='stale check'))]):
            result,views=self.checks(actions)
            self.assertFalse(result['verified'])
            self.assertEqual(views[-1]['verification']['status'],'fail')
            self.assertTrue(any(v['status']=='fail' for v in views[-1]['verification']['checks']))

    def test_profile_is_frozen_and_has_a_distinct_interpreter_identity(self):
        with self.fixture() as case:
            from branchwrite.kernel import FrameKernel
            supplied=copy.deepcopy(SPEC)
            default=Interpreter(FrameKernel(case.log),case.registry)
            compact=Interpreter(FrameKernel(case.log),case.registry,tool_feedback=supplied)
            identity=compact.identity;supplied['format']='changed'
            shown=compact.tool_feedback;shown['schema']=2
            self.assertEqual(compact.tool_feedback,SPEC)
            self.assertEqual(compact.identity,identity)
            self.assertNotEqual(default.identity,compact.identity)
            self.assertIsNone(default.tool_feedback)


    def test_candidate_worlds_inherit_only_the_owner_selected_profile(self):
        with self.fixture() as case:
            from branchwrite.kernel import FrameKernel
            worlds=dict(candidate=dict(registry=case.registry))
            compact=Interpreter(FrameKernel(case.log),case.registry,worlds=worlds,tool_feedback=SPEC)
            default=Interpreter(FrameKernel(case.log),case.registry,worlds=worlds)
            self.assertEqual(compact.worlds['candidate'].tool_feedback,SPEC)
            self.assertIsNone(default.worlds['candidate'].tool_feedback)
            self.assertNotEqual(compact.worlds['candidate'].identity,default.worlds['candidate'].identity)
            shown=compact.worlds['candidate'].tool_feedback;shown['format']='changed'
            self.assertEqual(compact.worlds['candidate'].tool_feedback,SPEC)

    def test_default_presentation_never_calls_compact_projection(self):
        case=output_fixture.OutputFeedbackTests();case.setUp()
        try:
            with patch('branchwrite.interpreter._compact_tool_feedback',side_effect=AssertionError('default must keep existing rendering')):
                view=case.run_output(b'ordinary output\n',b'diagnostic\n',7)
            self.assertNotIn('feedback_format',view)
            self.assertIn('plan_sha256',view)
            self.assertIn('stdout_artifact',view)
            self.assertIn('stdout_display',view)
            case.assert_raw('stdout',b'ordinary output\n',view)
            self.assertEqual(view['exit_code'],7)
        finally:case.doCleanups()


class CompactConfigurationTests(unittest.TestCase):
    def launch(self,root):
        project=root/'project';project.mkdir(exist_ok=True)
        return build_launch(project,'Owned ordinary task',dict(endpoint_url='http://127.0.0.1:1',endpoint_pin='owned',model_contract_id='m',execution_profile_id='p',eos_tokens=[256]),branch='new',project_files=True,shell_timeout=2)

    def test_omitted_option_remains_omitted_and_explicit_profile_roundtrips(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);launch=self.launch(root)
            self.assertNotIn('tool_feedback',launch['config'])
            launch['config']['tool_feedback']=copy.deepcopy(SPEC)
            self.assertEqual(_config(json.dumps(launch['config']))['tool_feedback'],SPEC)
            save_launch(root/'run',launch)
            self.assertEqual(read_launch(root/'run')['config']['tool_feedback'],SPEC)
            changed=copy.deepcopy(launch);changed['config'].pop('tool_feedback')
            with self.assertRaises(ValueError):save_launch(root/'run',changed)

    def test_unknown_or_untyped_profiles_are_refused_before_dispatch(self):
        with tempfile.TemporaryDirectory() as td:
            config=self.launch(Path(td))['config']
            for spec in (None,True,'compact-v1',{},dict(schema=True,format='compact-v1'),
                    dict(schema=1,format='compact-v2'),dict(SPEC,untrusted=True)):
                config['tool_feedback']=spec
                with self.subTest(spec=spec),self.assertRaises(AdmissionError):_config(json.dumps(config))


class CompactFeedbackHttpTests(unittest.TestCase):
 def test_compact_cli_http_reuses_raw_receipts_and_finished_reopen(self):
  # Actual CLI/HTTP/tools with explicitly scripted CPU model choices, not GPU.
  import test_cow_client_flow as fixture
  from collections import defaultdict
  from branchwrite.coding_defaults import workflow_source
  from serve.test_cow_presentation_flow import FlowModel
  class DiscoveredFlowModel(FlowModel):
   def __init__(self,*args):
    super().__init__(*args)
    self.profile.update(model_contract_id='a'*64,execution_profile_id='b'*64)
  case=fixture.CowClientFlowTests();self.addCleanup(case.doCleanups)
  case.model_factory=DiscoveredFlowModel
  case.connection_info=dict(model_contract_id='a'*64,execution_profile_id='b'*64,eos_tokens=[299])
  case.setUp()
  root=Path(case.temp.name);source=root/'source';source.mkdir();(source/'keep.txt').write_bytes(b'unchanged\n')
  command=shlex.join(['/usr/bin/python3','-I','-B','-c',"import os;os.write(1,b'out\\xff');os.write(2,b'err\\xfe');raise SystemExit(7)"])
  actions=[dict(tool='run_shell',arguments=dict(command=command)),dict(tool='read_file',arguments=dict(path='keep.txt')),dict(tool='finish',arguments=dict(answer='actual nonzero probe observed'))]
  stream=iter(tuple(json.dumps(v).encode())+(299,) for v in actions)
  case.models[0].plans=defaultdict(lambda:next(stream))
  cfg=dict(schema=1,tool_feedback=copy.deepcopy(SPEC),source=str(source),run_id='binary-feedback',grant=dict(edit_paths=[],read_paths=['keep.txt'],create_paths=[],allow_tests=False,allow_shell=True),shell=dict(timeout=3,expected_hostname=os.uname().nodename),
   profiles=dict(control=dict(output_format='text',settings=dict(temperature=0),request_tokens=1024)),bindings=dict(task=dict(type='Text',value='Run the binary stream probe, read keep.txt and finish.')),
   verification=dict(schema=1,files=[dict(path='keep.txt',sha256=hashlib.sha256(b'unchanged\n').hexdigest())]),
   cow=dict(endpoint_url=case.base_url,endpoint_pin='flow-model-free',model_contract_id='a'*64,execution_profile_id='b'*64,eos_tokens=[299],branch='binary-feedback',mode='ask',bootstrap='coding'))
  config=root/'host.json';config.write_text(json.dumps(cfg));program=root/'job.bw';program.write_text(workflow_source().replace('contract=unit-tests-and-finish','contract=file-readback-and-finish'))
  cmd=[sys.executable,'-B','-m','branchwrite','run',str(program),'--config',str(config),'--state',str(root/'run')]
  done=subprocess.run(cmd,capture_output=True,env={**os.environ,'BW_COW_API_KEY':'cpu-flow-secret'},timeout=20)
  self.assertEqual(done.returncode,0,done.stderr);self.assertTrue(json.loads(done.stdout)['verified'])
  history=case._client('http','inspect-binary-feedback').history('binary-feedback');views=[]
  for message in history.messages:
   try:value=json.loads(message['text'])
   except (ValueError,TypeError):continue
   if type(value) is dict and value.get('tool')=='run_shell' and value.get('feedback_format')=='compact-v1':views.append(value)
  self.assertEqual(len(views),1);view=views[0]
  for field,body,text in [('stdout',b'out\xff','out\ufffd'),('stderr',b'err\xfe','err\ufffd')]:
   self.assertEqual(view[field],text)
   self.assertEqual(view['streams'][field],dict(bytes=len(body),shown_bytes=len(body),lossy=True))
   self.assertFalse(view[field+'_truncated'])
   self.assertNotIn(field+'_artifact',view)
  self.assertEqual(view['command'],command)
  self.assertNotIn('plan_sha256',view)
  self.assertIn('source_writes',view['shell_context'])
  self.assertEqual(view['problem']['stage'],'exited')
  self.assertIn('effects',view['problem']['next_action'])
  self.assertEqual(view['exit_code'],7);self.assertEqual(len(case.trace),3)
  # The settled source outcome still owns the exact original artifact identities.
  from branchwrite.records import RuntimeLog,decode
  from branchwrite.kernel import FrameKernel
  with RuntimeLog(root/'run/ledger') as ledger:
   kernel=FrameKernel(ledger)
   outcomes=[]
   for frame in kernel.frames():
    if frame.get('state')=='Closed' and frame.get('contract')==('ToolOutcome','record'):
     value=decode(ledger.read_artifact(Artifact(*frame['result'])))[2]
     if value.get('tool')=='run_shell':outcomes.append(value)
   self.assertEqual(len(outcomes),1)
   original=outcomes[0]
   self.assertIn('plan_sha256',original)
   self.assertEqual(ledger.read_artifact(Artifact(*original['stdout'])),b'out\xff')
   self.assertEqual(ledger.read_artifact(Artifact(*original['stderr'])),b'err\xfe')
  case._stop_server()
  again=subprocess.run(cmd,capture_output=True,env={**os.environ,'BW_COW_API_KEY':'cpu-flow-secret'},timeout=20)
  self.assertEqual((again.returncode,again.stdout),(done.returncode,done.stdout),again.stderr)



if __name__=='__main__':unittest.main()
