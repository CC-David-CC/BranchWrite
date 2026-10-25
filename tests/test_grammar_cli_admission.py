"""Actual CLI/HTTP grammar admission; CPU backend and host-scripted actions.

This checks plumbing and completed replay, not autonomous model reasoning.
The continuation case checks admission/registration only: scripted tool actions
do not issue a model continuation. Real retained-context execution is separate.
"""
from pathlib import Path
import json,os,subprocess,sys,tempfile,threading,unittest

class GrammarCliAdmissionTests(unittest.TestCase):
 def test_real_cli_registers_thinking_grammars_and_reopens_offline(self):
  self._exercise(False)

 def test_explicit_continuation_registers_and_reopens_offline(self):
  self._exercise(True)

 def _exercise(self,continuation):
  from test_thinking_grammar import ThinkingTokenizer
  from serve.test_cow_grammar_canonical_flow import GrammarCPUBackend,_render,_encode,_initial_root_mode
  from context_time_travel.real import BranchingModel
  from context_time_travel.coordinator import ContextCoordinator
  from context_time_travel.pools import PoolConfig
  from serve.cow_adapter import CowAdapter
  from serve.cow_text_adapter import CowTextAdapter
  from serve.cow_grammar_disk import DurableGrammarCatalog
  from serve.cow_http import make_server
  from branchwrite.cow_client import CowClient,OperationJournal
  temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);base=Path(temp.name)
  tokenizer=ThinkingTokenizer()
  profile=dict(model_contract_id='a'*64,execution_profile_id='b'*64,
   model_weights_sha256='a'*64,execution=dict(GPU=[0],resume_contract='identical-native-operators-v1',
   generated_operator='normal-verifier-decode',selected_token_protocol='consumed-selected-receipt-v1',
   native_request_protocol='consumed-greedy-ack-v1',prefill_chunk=16,capacity=131072,eos_tokens=[256]))
  def factory(gpu):return BranchingModel(base/'store',GrammarCPUBackend(profile,tokenizer),profile)
  coordinator=ContextCoordinator(base/'store',PoolConfig(gpus=(0,),ram_bytes=64*1024**2,disk_bytes=256*1024**2,min_available_bytes=0),factory)
  self.addCleanup(coordinator.close);coordinator.ready(5)
  adapter=CowAdapter(coordinator)
  text=CowTextAdapter(adapter,tokenizer,_render,
   lambda messages,rendered,add_generation_prompt:_encode(tokenizer,messages,rendered,add_generation_prompt),
   initial_root_mode=_initial_root_mode,renderer_id='b'*64)
  catalog=DurableGrammarCatalog(base/'grammars',tokenizer,[256]);self.addCleanup(catalog.close)
  server=make_server(adapter,api_key='cli-key',text_adapter=text,grammar_catalog=catalog,
   connection_info=dict(model_contract_id=profile['model_contract_id'],execution_profile_id=profile['execution_profile_id'],
    eos_tokens=profile['execution']['eos_tokens']))
  thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  closed=False
  def stop():
   nonlocal closed
   if not closed:
    server.shutdown();server.server_close();thread.join(5);closed=True
  self.addCleanup(stop)
  source=base/'source';source.mkdir();(source/'note.txt').write_text('unchanged')
  body=lambda tool,args:dict(type='ToolProposal',value=json.dumps(dict(tool=tool,arguments=args)))
  config=dict(schema=1,source=str(source),run_id='registered-cli',grant=dict(edit_paths=[],create_paths=[],read_paths=['note.txt'],allow_tests=False,allow_shell=True),
   shell=dict(timeout=2),bindings=dict(command=body('run_shell',dict(command='printf verified')),finish=body('finish',dict(answer='observed'))),
   cow=dict(endpoint_url='http://127.0.0.1:'+str(server.server_port),endpoint_pin='owned-cpu-server',
    model_contract_id=profile['model_contract_id'],execution_profile_id=profile['execution_profile_id'],
    eos_tokens=[256],branch='cli',mode='ask',bootstrap='coding',grammar_registration='inline'),
   verification=dict(schema=1,commands=[dict(command='printf verified',disposition='exited',exit_code=0)]))
  if continuation:
   client=CowClient.http(config['cow']['endpoint_url'],journal=OperationJournal(base/'prepare-journal'),api_key='cli-key',endpoint_pin='owned-cpu-server')
   namespace=client.create_namespace('retained coding context','prepare-namespace')
   prepared=client.prepare('parent',namespace['namespace_id'],'Earlier coding task.','prepare-root')
   client.fork('parent',prepared.receipt.snapshot,'cli','prepare-fork')
   parent_before=client.head('parent')
   config['cow'].pop('bootstrap')
   config['cow']['mode']='append_user'
   config['bindings']['task']=dict(type='Text',value='Continue the retained coding task.')
  cfg=base/'host.json';cfg.write_text(json.dumps(config))
  program=base/'task.bw';program.write_text('FLOW task\nPLAN p from=command against=world -> plan\nACT c plan=plan -> outcome\nPLAN f from=finish against=world -> plan\nACT done plan=plan -> outcome\nVERIFY v input=outcome contract=command-evidence-and-finish -> verified\nEND\n')
  state=base/'run';argv=[sys.executable,'-B','-m','branchwrite','run',str(program),'--config',str(cfg),'--state',str(state)]
  env={**os.environ,'BW_COW_API_KEY':'cli-key'}
  first=subprocess.run(argv,capture_output=True,text=True,env=env,timeout=30)
  self.assertEqual(first.returncode,0,first.stderr);self.assertTrue(json.loads(first.stdout)['verified'])
  records=[json.loads(p.read_text()) for p in (state/'cow-operations').glob('*.json')]
  registrations=[r for r in records if r['path']=='/cow/grammars']
  self.assertEqual(len(registrations),1);self.assertEqual(registrations[0]['state'],'complete')
  self.assertIn('BW_TOOLS',registrations[0]['receipt']['states'])
  self.assertEqual((source/'note.txt').read_text(),'unchanged')
  if continuation:self.assertEqual(client.head('parent'),parent_before)
  stop()
  ledger=state/'ledger';before={str(p.relative_to(ledger)):p.read_bytes() for p in ledger.rglob('*') if p.is_file()}
  second=subprocess.run(argv,capture_output=True,text=True,env=env,timeout=15)
  self.assertEqual(second.returncode,0,second.stderr);self.assertEqual(first.stdout,second.stdout)
  self.assertEqual(before,{str(p.relative_to(ledger)):p.read_bytes() for p in ledger.rglob('*') if p.is_file()})
