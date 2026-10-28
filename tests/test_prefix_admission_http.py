"""Actual CLI and HTTP root admission; CPU arithmetic backend, no GPU claim."""
import pathlib,tempfile,unittest,threading,subprocess,os,sys,json,urllib.request
class PrefixHttpTests(unittest.TestCase):
 def test_public_prefix_source_uses_existing_ask_api(self):
  from test_thinking_grammar import ThinkingTokenizer
  from serve.test_cow_grammar_canonical_flow import GrammarCPUBackend,_render,_encode
  from serve.test_cow_presentation_flow import initial_root_mode,append_initial_user_suffix
  from context_time_travel.real import BranchingModel
  from context_time_travel.coordinator import ContextCoordinator
  from context_time_travel.pools import PoolConfig
  from serve.cow_adapter import CowAdapter
  from serve.cow_text_adapter import CowTextAdapter
  from serve.cow_grammar_disk import DurableGrammarCatalog
  from serve.cow_http import make_server
  from branchwrite.cow_client import CowClient,OperationJournal
  from branchwrite.coding_cli import read_launch
  with tempfile.TemporaryDirectory() as t:
   base=pathlib.Path(t);tokenizer=ThinkingTokenizer()
   profile=dict(model_contract_id='c'*64,execution_profile_id='e'*64,model_weights_sha256='a'*64,execution=dict(GPU=[0],resume_contract='identical-native-operators-v1',generated_operator='normal-verifier-decode',selected_token_protocol='consumed-selected-receipt-v1',native_request_protocol='consumed-greedy-ack-v1',prefill_chunk=16,capacity=131072,eos_tokens=[256]))
   def factory(gpu):return BranchingModel(base/'store',GrammarCPUBackend(profile,tokenizer),profile)
   coordinator=ContextCoordinator(base/'store',PoolConfig(gpus=(0,),ram_bytes=64*1024**2,disk_bytes=256*1024**2,min_available_bytes=0),factory)
   catalog=None;server=None;thread=None
   try:
    coordinator.ready(5);adapter=CowAdapter(coordinator)
    text=CowTextAdapter(adapter,tokenizer,_render,lambda messages,rendered,add_generation_prompt:_encode(tokenizer,messages,rendered,add_generation_prompt),initial_root_mode=initial_root_mode,append_initial_user_suffix=append_initial_user_suffix,renderer_id='b'*64)
    catalog=DurableGrammarCatalog(base/'grammars',tokenizer,[256])
    server=make_server(adapter,api_key='prefix-key',text_adapter=text,grammar_catalog=catalog,
      connection_info=dict(model_contract_id=profile['model_contract_id'],execution_profile_id=profile['execution_profile_id'],eos_tokens=[256]))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    url='http://127.0.0.1:'+str(server.server_port)
    client=CowClient.http(url,journal=OperationJournal(base/'setup-journal'),api_key='prefix-key',endpoint_pin='owned')
    namespace=client.create_namespace('Prepared prefix','prefix-namespace')['namespace_id']
    prepared=client.load_context('source-prefix',namespace,[dict(role='system',content='Shared project context')],'prefix-context')
    parent=client.head('source-prefix')
    self.assertEqual(parent.tip,parent.root)
    source=base/'source';source.mkdir();(source/'app.py').write_text('pass\n');(source/'.git').mkdir()
    (source/'.git/config').write_text('private metadata')
    connection=base/'connection';connection.write_text(json.dumps(dict(endpoint_url=url,endpoint_pin='owned',model_contract_id=profile['model_contract_id'],execution_profile_id=profile['execution_profile_id'],eos_tokens=[256])))
    task=base/'task';task.write_text('Inspect the project')
    state=base/'state'
    command=[sys.executable,'-B','-m','branchwrite','code',str(source),'--task-file',str(task),'--connection',str(connection),'--state',str(state),'--branch','child','--from-prefix','source-prefix','--read','app.py','--test-command','python3 -m unittest','--max-steps','1']
    result=subprocess.run(command,capture_output=True,text=True,env=dict(os.environ,BW_COW_API_KEY='prefix-key',PYTHONDONTWRITEBYTECODE='1'),timeout=30)
    self.assertEqual(result.returncode,3,result.stderr)
    launch=read_launch(state);self.assertEqual(launch['config']['cow']['mode'],'ask')
    self.assertEqual(launch['fork']['snapshot'],parent.root)
    self.assertFalse((state/'world/workspace/.git').exists())
    child=client.head('child');self.assertEqual(child.tip,parent.root)
    route='/cow/text/'+launch['config']['cow']['mode'].replace('_','-')
    from branchwrite.thinking_ladder import ladder
    registrations=[json.loads(p.read_text()) for p in (state/'cow-operations').glob('*.json') if json.loads(p.read_text()).get('path')=='/cow/grammars']
    self.assertEqual(len(registrations),1)
    grammar=registrations[0]['receipt']['states'][ladder('standard')[0].grammar_state]
    # Use the same registered grammar as the CLI. This CPU backend implements
    # grammar consumption, not the native-only unconstrained resident shortcut.
    body=dict(branch='child',content='First question',revision=child.revision,operation_id='prefix-question',max_tokens=1,grammar_state=grammar,stream=False)
    request=urllib.request.Request(url+route,data=json.dumps(body).encode(),headers={'Authorization':'Bearer prefix-key','Content-Type':'application/json'})
    try:
     with urllib.request.urlopen(request,timeout=15) as response:
      self.assertEqual(response.status,200);response.read()
    except urllib.error.HTTPError as error:self.fail(error.read().decode('utf8','replace'))
    self.assertNotEqual(client.head('child').tip,parent.root)
    self.assertEqual(client.head('source-prefix'),parent)
   finally:
    if server is not None:server.shutdown();server.server_close()
    if thread is not None:thread.join(5)
    if catalog is not None:catalog.close()
    coordinator.close()
