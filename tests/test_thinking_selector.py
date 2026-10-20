"""Admission-only unit fixtures; model returns are explicitly scripted ledger values.

No GPU, HTTP inference, numerical exactness or autonomous quality is certified.
Real fork/model transport recovery is covered separately by planning_retry_flow.
"""
from pathlib import Path
import dataclasses,hashlib,json,tempfile,unittest
from unittest.mock import patch
from branchwrite.records import RuntimeLog,Artifact,decode
from branchwrite.kernel import FrameKernel
from branchwrite.execution import Executor,Grant
from branchwrite.tool_registry import ToolRegistry
from branchwrite.interpreter import Interpreter,Value,AdmissionError
from branchwrite.cow_client import CowClient,OperationJournal,BranchHead
from branchwrite.model_dispatch import ModelAdapter,FrozenModelCall
from branchwrite.coding_defaults import generation_profile
from branchwrite.planning_retry import retry_definition

class ThinkingSelectorAdmissionTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.base=Path(self.temp.name)
  source=self.base/'source';source.mkdir();(source/'data.txt').write_bytes(b'keep\n')
  self.executor=Executor.create(source,self.base/'world')
  self.registry=ToolRegistry(self.executor,Grant((),False,read_paths=('data.txt',)))
  self.client=CowClient.http('http://127.0.0.1:9',journal=OperationJournal(self.base/'cow-journal'),endpoint_pin='admission-unit-only')
  self.no_network=patch.object(self.client.transport,'request',side_effect=AssertionError('admission unit must not use network'));self.no_network.start();self.addCleanup(self.no_network.stop)
  self.adapter=ModelAdapter(self.client,run_id='selection-unit',model_contract_id='fixture-only',execution_profile_id='fixture-only',eos_tokens=(299,))
  self.log=RuntimeLog(self.base/'ledger');self.addCleanup(self.close);self.kernel=FrameKernel(self.log)
  self.profile={**generation_profile(),'thinking_ladder':'standard'}
  self.spec=dict(schema=1,files=[dict(path='data.txt',sha256=hashlib.sha256(b'keep\n').hexdigest())])
  self.runtime=Interpreter(self.kernel,self.registry,adapter=self.adapter,profiles=dict(control=self.profile),verification=self.spec)
  self.head=BranchHead('main',0,'b'*64,'a'*64)
 def close(self):
  if not self.log._closed:self.log.close()
 def start(self,duplicate=False):
  program="""FLOW task
REPEAT attempts max=6 until=verified exhausted=stop
EXPAND decide from=current task=task profile=control -> proposed
PLAN freeze from=proposed against=world -> plan
ACT perform plan=plan -> outcome
TRANSFORM advance input=proposed contract=cow-source -> current
TRANSFORM feedback input=outcome contract=tool-feedback -> task
VERIFY check input=outcome contract=file-readback-and-finish -> verified
DUPLICATE
END
END
""".replace('DUPLICATE\n','VERIFY duplicate input=outcome contract=file-readback-and-finish -> checked\n' if duplicate else '')
  self.runtime.start(program,dict(current=Value('COWSource',dict(head=dataclasses.asdict(self.head),mode='ask')),task=Value('Text','Read data.txt, preserve it, and finish.')))
 def next_model(self):
  for _ in range(120):
   report=self.runtime.step()
   if report.status=='admitted':
    frame=self.kernel.frame(report.frame)
    if frame['contract']==('ModelOutput','record'):return frame
   if report.status=='complete' and report.frame=='program':return None
  self.fail('missing model admission')
 def plan(self,frame):
  raw=decode(self.log.read_artifact(Artifact(*frame['inputs'])))
  data=raw['model_plan'] if 'model_plan' in raw else self.log.read_artifact(Artifact(*frame['inputs']))
  return self.adapter.plan(FrozenModelCall(data))
 def scripted_model_return(self,frame,tool='finish',foreign_root=False):
  # The trusted unit fixture supplies a ledger value; it does NOT pretend that
  # native inference or thinking happened. Production never takes this shortcut.
  plan=self.plan(frame);head=BranchHead(plan['source']['name'],plan['source']['revision']+1,hashlib.sha256(frame['id'].encode()).hexdigest(),'c'*64 if foreign_root else plan['source']['root'])
  args=dict(answer='done') if tool=='finish' else dict(path='data.txt')
  value=dict(schema=1,model_frame=frame['id'],plan_sha256=frame['inputs'][0],output_format='thinking',
   text=json.dumps(dict(tool=tool,arguments=args)),native_receipt=dict(branch=dataclasses.asdict(head),model_contract_id='fixture-only',execution_profile_id='fixture-only'),
   source_snapshot=plan['source']['tip'],consumed_output_tokens=1,request_count=1,responses=())
  self.kernel.finish(frame['id'],value);return value
 def test_new_default_selects_standard_ladder_and_invalid_start_is_rejected(self):
  self.assertEqual(generation_profile().get('thinking_ladder'),'standard')
  for patch_values in [dict(thinking_ladder='unknown'),dict(output_format='text'),dict(grammar_state='BW_TOOLS_THINK_8192')]:
   with self.subTest(patch=patch_values),self.assertRaises(AdmissionError):
    Interpreter(self.kernel,self.registry,adapter=self.adapter,profiles=dict(control={**self.profile,**patch_values}),verification=self.spec)
 def test_initial_admission_uses_4k_with_original_frame_pointer(self):
  self.start();frame=self.next_model();plan=self.plan(frame)
  self.assertEqual(plan['planning'],dict(schema=1,profile='control',mode='standard',rung=0,origin_model_frame=frame['id'],handled_failures=()))
  self.assertEqual(plan['config']['grammar_state'],'BW_TOOLS');self.assertEqual(plan['config']['mode'],'ask')
  self.assertNotIn('thinking_ladder',plan['config'])
 def test_failed_finish_forks_prior_ask_and_advances_to_8k(self):
  self.start();first=self.next_model();before=self.plan(first);failed=self.scripted_model_return(first)
  retry=self.next_model();raw=decode(self.log.read_artifact(Artifact(*retry['inputs'])));plan=self.plan(retry)
  self.assertEqual(self.log.read_artifact(Artifact(*retry['definition'])),retry_definition(self.adapter))
  self.assertEqual(raw['source'],failed['native_receipt']['branch']);self.assertEqual(raw['snapshot'],self.head.tip)
  self.assertEqual(plan['config']['mode'],'ask');self.assertEqual(plan['config']['grammar_state'],'BW_TOOLS_THINK_8192')
  self.assertTrue(plan['config']['content'].startswith(before['config']['content']))
  self.assertIn('givens',plan['config']['content']);self.assertIn('File edits',plan['config']['content'])
  self.assertEqual(plan['planning']['origin_model_frame'],first['id']);self.assertEqual(plan['planning']['rung'],1)
  self.assertEqual(len(plan['planning']['handled_failures']),1)
  self.assertEqual(plan['config']['settings'],before['config']['settings'])
  self.assertEqual((self.executor.workspace/'data.txt').read_bytes(),b'keep\n')
 def test_ordinary_tool_progress_stays_on_same_rung_without_fork(self):
  self.start();first=self.next_model();self.scripted_model_return(first,'read_file')
  second=self.next_model();plan=self.plan(second)
  self.assertEqual(self.log.read_artifact(Artifact(*second['definition'])),self.adapter.definition)
  self.assertEqual(plan['planning']['origin_model_frame'],first['id'])
  self.assertEqual(plan['planning']['rung'],0);self.assertEqual(plan['planning']['handled_failures'],())
  self.assertEqual(plan['config']['mode'],'append_user')
 def test_duplicate_verification_of_one_finish_does_not_spend_two_rungs(self):
  self.start(duplicate=True);first=self.next_model();self.scripted_model_return(first)
  second=self.next_model();plan=self.plan(second)
  self.assertEqual(plan['planning']['rung'],1);self.assertEqual(len(plan['planning']['handled_failures']),1)
 def test_foreign_root_model_result_cannot_start_an_unrelated_ladder(self):
  self.start();first=self.next_model();self.scripted_model_return(first,foreign_root=True)
  with self.assertRaisesRegex(AdmissionError,'root|source'):self.next_model()
 def test_successful_task_does_not_create_retry(self):
  self.start();first=self.next_model();self.scripted_model_return(first,'read_file')
  second=self.next_model();self.scripted_model_return(second)
  self.assertIsNone(self.next_model());self.assertEqual(len([f for f in self.kernel.frames() if f['contract']==('ModelOutput','record')]),2)
 def test_admitted_retry_survives_log_reopen_without_new_fork_intent(self):
  self.start();first=self.next_model();self.scripted_model_return(first);retry=self.next_model()
  before=self.log.read_artifact(Artifact(*retry['inputs']));ids=[f['id'] for f in self.kernel.frames()]
  self.close();self.log=RuntimeLog(self.base/'ledger');self.kernel=FrameKernel(self.log)
  self.runtime=Interpreter(self.kernel,self.registry,adapter=self.adapter,profiles=dict(control=self.profile),verification=self.spec)
  self.assertEqual([f['id'] for f in self.kernel.frames()],ids)
  self.assertEqual(self.log.read_artifact(Artifact(*self.kernel.frame(retry['id'])['inputs'])),before)
if __name__=='__main__':unittest.main()
