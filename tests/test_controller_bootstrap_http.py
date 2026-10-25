"""Actual CLI/HTTP bootstrap policy separation; CPU backend, no model claims."""
import unittest,tempfile,json,os,sys,subprocess,threading
from pathlib import Path
class ControllerBootstrapHTTPTests(unittest.TestCase):
 def test_two_projects_share_prefix_text_but_keep_distinct_current_policy(self):
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
  tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);base=Path(tmp.name)
  tokenizer=ThinkingTokenizer()
  profile=dict(model_contract_id='a'*64,execution_profile_id='b'*64,model_weights_sha256='a'*64,
   execution=dict(GPU=[0],resume_contract='identical-native-operators-v1',generated_operator='normal-verifier-decode',
   selected_token_protocol='consumed-selected-receipt-v1',native_request_protocol='consumed-greedy-ack-v1',prefill_chunk=16,capacity=131072,eos_tokens=[256]))
  coordinator=ContextCoordinator(base/'store',PoolConfig(gpus=(0,),ram_bytes=64*1024**2,disk_bytes=256*1024**2,min_available_bytes=0),
   lambda gpu:BranchingModel(base/'store',GrammarCPUBackend(profile,tokenizer),profile))
  self.addCleanup(coordinator.close);coordinator.ready(5)
  adapter=CowAdapter(coordinator)
  text=CowTextAdapter(adapter,tokenizer,_render,lambda messages,rendered,add_generation_prompt:_encode(tokenizer,messages,rendered,add_generation_prompt),
   initial_root_mode=_initial_root_mode,renderer_id='b'*64)
  catalog=DurableGrammarCatalog(base/'grammars',tokenizer,[256]);self.addCleanup(catalog.close)
  workspace=CowWorkspace(coordinator.store,tokenizer,root_mode_resolver=text.root_mode_for_projection)
  server=make_server(adapter,api_key='owned-key',text_adapter=text,grammar_catalog=catalog,workspace=workspace,
   connection_info=dict(model_contract_id=profile['model_contract_id'],execution_profile_id=profile['execution_profile_id'],
    eos_tokens=profile['execution']['eos_tokens']))
  thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  self.addCleanup(lambda:(server.shutdown(),server.server_close(),thread.join(5)))
  endpoint='http://127.0.0.1:'+str(server.server_port)
  client=CowClient.http(endpoint,journal=OperationJournal(base/'inspect'),api_key='owned-key',endpoint_pin='cpu')
  prefixes=[];cards=[]
  program=base/'job.bw';program.write_text('FLOW job\nTEXT note\n|hello\nEND\nEND\n')
  for name in ['A','B']:
   source=base/('source-'+name);source.mkdir();(source/(name+'.py')).write_text('pass')
   config=dict(schema=1,source=str(source),run_id='controller-'+name,source_policy='metadata-free-project-v1',
    grant=dict(edit_paths=[name+'.py'],read_paths=[name+'.py'],create_paths=[],allow_tests=False,allow_shell=True),
    shell=dict(timeout=2),bindings=dict(task=dict(type='Text',value='Task '+name)),
    verification=dict(schema=1,commands=[dict(command='printf current-policy-'+name,disposition='exited',exit_code=0)]),
    cow=dict(endpoint_url=endpoint,endpoint_pin='cpu',model_contract_id=profile['model_contract_id'],execution_profile_id=profile['execution_profile_id'],
     eos_tokens=[256],branch='branch-'+name,mode='ask',bootstrap='coding',grammar_registration='inline'))
   cfg=base/('config-'+name+'.json');cfg.write_text(json.dumps(config));state=base/('state-'+name)
   result=subprocess.run([sys.executable,'-B','-m','branchwrite','run',str(program),'--config',str(cfg),'--state',str(state)],
    env={**os.environ,'BW_COW_API_KEY':'owned-key'},capture_output=True,text=True,timeout=30)
   self.assertEqual(result.returncode,1,result.stderr) # completed non-coding FLOW, not verified
   prefixes.append(client.history('branch-'+name).messages[0]['text'])
   with RuntimeLog(state/'ledger',read_only=True) as log:
    root=FrameKernel(log).frame('program');inputs=decode(log.read_artifact(Artifact(*root['inputs'])))
    cards.append(inputs['bindings']['task'][1])
  self.assertEqual(prefixes[0],prefixes[1])
  self.assertNotIn('current-policy-A',prefixes[0]);self.assertNotIn('current-policy-B',prefixes[1])
  self.assertIn('current-policy-A',cards[0]);self.assertNotIn('current-policy-B',cards[0])
  self.assertIn('current-policy-B',cards[1]);self.assertNotIn('current-policy-A',cards[1])
