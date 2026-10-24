"""Actual launcher subprocess admission over real COW HTTP; CPU arithmetic only."""
from pathlib import Path
import json,os,subprocess,sys,tempfile,threading,unittest
class CodingLauncherHttpTests(unittest.TestCase):
 def test_code_prepares_real_context_and_resume_keeps_pinned_setup(self):
  self.launch_case(False)
 def test_explore_cli_prepares_two_owned_worlds_and_resume_keeps_the_same_plan(self):
  self.launch_case(True)
 def test_direct_mode_pins_registered_grammar_and_resume(self):
  self.launch_case(False,thinking="off")
 def test_compact_direct_cli_pins_a_distinct_root_and_resume(self):
  self.launch_case(False,thinking='off',instructions='compact')
 def launch_case(self,explore,thinking="standard",instructions='worked-examples'):
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
   connection_info=dict(model_contract_id=profile['model_contract_id'],
    execution_profile_id=profile['execution_profile_id'],eos_tokens=[256]))
  thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  closed=False
  def stop():
   nonlocal closed
   if not closed:
    server.shutdown();server.server_close();thread.join(5);closed=True
  self.addCleanup(stop)
  source=base/'source';source.mkdir();(source/'app.py').write_text('print("unchanged")\n')
  connection=base/'connection.json'
  connection.write_text(json.dumps(dict(endpoint_url='http://127.0.0.1:'+str(server.server_port),endpoint_pin='owned-cpu',model_contract_id=profile['model_contract_id'],execution_profile_id=profile['execution_profile_id'],eos_tokens=[256])))
  task=base/'task.txt';task.write_text('Inspect this project and run its test.')
  state=base/'run'
  argv=[sys.executable,'-B','-m','branchwrite','code',str(source),'--task-file',str(task),'--connection',str(connection),'--state',str(state),'--branch','public-code','--read','app.py','--test-command','python3 -m unittest','--max-steps','1']
  if explore:argv.append('--explore')
  env=dict(os.environ,BW_COW_API_KEY='cli-key')
  first=subprocess.run(argv,capture_output=True,text=True,env=env,timeout=30)
  self.assertEqual(first.returncode,3,first.stderr)
  self.assertFalse(json.loads(first.stdout)['verified'])
  self.assertTrue((state/'ledger').is_dir())
  if explore:
   for name in ('first','second'):
    self.assertEqual((state/'candidates'/name/'workspace/app.py').read_bytes(),(source/'app.py').read_bytes())
  before=(state/'coding-launch.json').read_bytes()
  self.assertEqual(coordinator.store.head('public-code').revision,1)
  records=[json.loads(p.read_text()) for p in (state/'cow-operations').glob('*.json')]
  self.assertEqual(len([r for r in records if r['path']=='/cow/grammars' and r['state']=='complete']),1)
  self.assertTrue(any(r['path']=='/cow/text/context' and r['state']=='complete' for r in records))
  resumed=subprocess.run([sys.executable,'-B','-m','branchwrite','resume',str(state),'--max-steps','1'],capture_output=True,text=True,env=env,timeout=15)
  self.assertEqual(resumed.returncode,3,resumed.stderr)
  self.assertEqual((state/'coding-launch.json').read_bytes(),before)
  self.assertEqual(json.loads(resumed.stdout)['state'],json.loads(first.stdout)['state'])
  self.assertFalse(json.loads(resumed.stdout)['verified'])
  self.assertEqual((source/'app.py').read_text(),'print("unchanged")\n')
