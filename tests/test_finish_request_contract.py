"""Actual CPU CLI/HTTP transitions distinguish a finish request from its verdict."""
import copy,json,os,subprocess,sys,tempfile,unittest
from collections import defaultdict
from pathlib import Path
from branchwrite.coding_cli import build_launch,save_launch,read_launch
from branchwrite.coding_defaults import controller_prefix
from branchwrite.run_cli import _config

LEGACY='Request finish only after the current host completion policy is satisfied.'
REQUEST="Once the host's required evidence and checks are ready, request finish so the host can evaluate completion; final verification happens after that request."

class FinishRequestContractTests(unittest.TestCase):
 def test_owner_selection_is_saved_and_cannot_change_a_retained_root(self):
  schema={'oneOf':[{'properties':{'tool':{'enum':['finish']}}}]}
  baseline_prefix=controller_prefix(schema,style='compact')
  request_prefix=controller_prefix(schema,style='compact-finish-request')
  self.assertEqual(request_prefix,baseline_prefix.replace(LEGACY,REQUEST))
  connection=dict(endpoint_url='http://127.0.0.1:1',endpoint_pin='owned',model_contract_id='m',execution_profile_id='p',eos_tokens=[1])
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);project=root/'project';project.mkdir()
   args=dict(branch='new',project_files=True,thinking_mode='off')
   baseline=build_launch(project,'Owned task',connection,instruction_style='compact',**args)
   chosen=build_launch(project,'Owned task',connection,instruction_style='compact-finish-request',**args)
   self.assertEqual(_config(json.dumps(chosen['config']))['cow']['controller_prefix'],'compact-finish-request')
   compare=copy.deepcopy(chosen);compare['config']['cow']['controller_prefix']='compact'
   self.assertEqual(compare,baseline)
   save_launch(root/'state',chosen)
   self.assertEqual(read_launch(root/'state'),chosen)
   with self.assertRaises(ValueError):save_launch(root/'state',baseline)
   with self.assertRaisesRegex(ValueError,'retained prefixes'):
    build_launch(project,'Owned task',connection,instruction_style='compact-finish-request',from_branch='retained',**args)


 def test_actual_bootstrap_preserves_host_finish_and_check_transitions(self):
  from test_thinking_grammar import ThinkingTokenizer
  from serve.test_cow_grammar_canonical_flow import GrammarCPUBackend,_render,_encode,_initial_root_mode
  from context_time_travel.real import BranchingModel
  from context_time_travel.coordinator import ContextCoordinator
  from context_time_travel.pools import PoolConfig
  from serve.cow_adapter import CowAdapter
  from serve.cow_text_adapter import CowTextAdapter
  from serve.cow_grammar_disk import DurableGrammarCatalog
  from serve.cow_http import make_server
  from serve.cow_workspace import CowWorkspace
  from branchwrite.cow_client import CowClient,OperationJournal
  from branchwrite.records import RuntimeLog,Artifact,decode
  from branchwrite.kernel import FrameKernel
  import threading
  temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);root=Path(temporary.name)
  tokenizer=ThinkingTokenizer()
  profile=dict(model_contract_id='a'*64,execution_profile_id='b'*64,model_weights_sha256='c'*64,
   execution=dict(GPU=[0],resume_contract='identical-native-operators-v1',generated_operator='normal-verifier-decode',
    selected_token_protocol='consumed-selected-receipt-v1',native_request_protocol='consumed-greedy-ack-v1',prefill_chunk=16,capacity=131072,eos_tokens=[256]))
  coordinator=ContextCoordinator(root/'store',PoolConfig(gpus=(0,),ram_bytes=64*1024**2,disk_bytes=256*1024**2,min_available_bytes=0),
   lambda gpu:BranchingModel(root/'store',GrammarCPUBackend(profile,tokenizer),profile))
  self.addCleanup(coordinator.close);coordinator.ready(5)
  adapter=CowAdapter(coordinator)
  text=CowTextAdapter(adapter,tokenizer,_render,lambda messages,rendered,add_generation_prompt:_encode(tokenizer,messages,rendered,add_generation_prompt),initial_root_mode=_initial_root_mode,renderer_id='d'*64)
  catalog=DurableGrammarCatalog(root/'grammars',tokenizer,[256]);self.addCleanup(catalog.close)
  workspace=CowWorkspace(coordinator.store,tokenizer,root_mode_resolver=text.root_mode_for_projection)
  server=make_server(adapter,api_key='owned-key',text_adapter=text,workspace=workspace,grammar_catalog=catalog,connection_info=dict(model_contract_id=profile['model_contract_id'],execution_profile_id=profile['execution_profile_id'],eos_tokens=[256]))
  thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  self.addCleanup(lambda:(server.shutdown(),server.server_close(),thread.join(5)))
  endpoint='http://127.0.0.1:'+str(server.server_port)
  connection=dict(endpoint_url=endpoint,endpoint_pin='owned-cpu',model_contract_id=profile['model_contract_id'],execution_profile_id=profile['execution_profile_id'],eos_tokens=[256])
  project=root/'project';project.mkdir();(project/'marker').write_text('owned')
  launch=build_launch(project,'Check the saved marker and report completion.',connection,branch='finish-request-contract',project_files=True,thinking_mode='off',instruction_style='compact-finish-request',shell_timeout=2)
  actions=[dict(tool='finish',arguments=dict(answer='not yet checked')),
   dict(tool='run_check',arguments=dict(name='owned_marker',command='test "$(cat marker)" = owned')),
   dict(tool='finish',arguments=dict(answer='checked saved marker'))]
  lines=['FLOW phases']
  for index,action in enumerate(actions):
   name='step'+str(index);launch['config']['bindings'][name]=dict(type='ToolProposal',value=json.dumps(action))
   lines.extend(['PLAN p-'+name+' from='+name+' against=world -> plan','ACT a-'+name+' plan=plan -> outcome',
    'VERIFY v-'+name+' input=outcome contract=project-checks-and-finish -> verdict-'+name,
    'TRANSFORM f-'+name+' contract=tool-feedback input=outcome evidence=verdict-'+name+' -> view-'+name])
  lines.append('END');launch['program']='\n'.join(lines)+'\n'
  program=root/'phases.bw';program.write_text(launch['program']);config=root/'config.json';config.write_text(json.dumps(launch['config']))
  result=subprocess.run([sys.executable,'-B','-m','branchwrite','run',str(program),'--config',str(config),'--state',str(root/'state')],capture_output=True,text=True,env={**os.environ,'BW_COW_API_KEY':'owned-key'},timeout=30)
  self.assertEqual(result.returncode,0,result.stderr);self.assertTrue(json.loads(result.stdout)['verified'])
  client=CowClient.http(endpoint,journal=OperationJournal(root/'inspect'),api_key='owned-key',endpoint_pin='owned-cpu')
  prefix=client.history('finish-request-contract').messages[0]['text']
  self.assertIn(REQUEST,prefix);self.assertNotIn(LEGACY,prefix)
  with RuntimeLog(root/'state/ledger',read_only=True) as ledger:
   frame=FrameKernel(ledger).frame('program');value=decode(ledger.read_artifact(Artifact(*frame['result'])))[2]
  views=[json.loads(value['bindings']['view-step'+str(i)][1]) for i in range(3)]
  # This CPU fixture scripts actions; it establishes actual host semantics and
  # bootstrap delivery, not autonomous model behavior or better tool choices.
  self.assertEqual([(v['tool'],v['verification']['status']) for v in views],[('finish','fail'),('run_check','fail'),('finish','pass')])
  self.assertEqual((project/'marker').read_text(),'owned')
