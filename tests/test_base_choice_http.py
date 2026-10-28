"""Proposed-base CLI admission, actual HTTP fork and ask; CPU fixture only."""
import pathlib,tempfile,unittest,threading,subprocess,os,sys,json,urllib.request
class BaseChoiceHttpTests(unittest.TestCase):
 def test_proposed_base_source_uses_existing_fork_and_ask_api(self):
  self.exercise(False)
 def test_automatic_host_selection_uses_existing_fork_and_ask_api(self):
  self.exercise(True)
 def test_prepare_base_cli_publishes_catalog_and_retries_without_prefill(self):
  self.exercise("cli")
 def test_prepare_base_recovers_namespace_ack_loss_in_new_process(self):
  self.exercise('cli-namespace-loss')
 def test_prepare_base_recovers_context_ack_loss_without_prefix_recompute(self):
  self.exercise('cli-context-loss')
 def test_prepare_base_unknown_context_is_not_replayed(self):
  self.exercise('cli-before-context')
 def test_code_cli_builds_project_receipt_then_uses_real_cpu_cow_root(self):
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
   models=[]
   def factory(gpu):
    model=BranchingModel(base/'store',GrammarCPUBackend(profile,tokenizer),profile);models.append(model);return model
   coordinator=ContextCoordinator(base/'store',PoolConfig(gpus=(0,),ram_bytes=64*1024**2,disk_bytes=256*1024**2,min_available_bytes=0),factory)
   catalog=None;server=None;thread=None
   try:
    coordinator.ready(5);adapter=CowAdapter(coordinator)
    text=CowTextAdapter(adapter,tokenizer,_render,lambda messages,rendered,add_generation_prompt:_encode(tokenizer,messages,rendered,add_generation_prompt),initial_root_mode=initial_root_mode,append_initial_user_suffix=append_initial_user_suffix,renderer_id='b'*64)
    catalog=DurableGrammarCatalog(base/'grammars',tokenizer,[256])
    from serve.cow_workspace import CowWorkspace
    workspace=CowWorkspace(coordinator.store,tokenizer,root_mode_resolver=text.root_mode_for_projection)
    server=make_server(adapter,api_key='prefix-key',text_adapter=text,grammar_catalog=catalog,workspace=workspace,
      connection_info=dict(model_contract_id=profile['model_contract_id'],execution_profile_id=profile['execution_profile_id'],eos_tokens=[256]))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    url='http://127.0.0.1:'+str(server.server_port)
    client=CowClient.http(url,journal=OperationJournal(base/'setup-journal'),api_key='prefix-key',endpoint_pin='owned')
    namespace=client.create_namespace('Saved examples','example-namespace')['namespace_id']
    client.load_context('reference-source',namespace,
        [dict(role='system',content='Saved source example: preserve the existing public API.')],
        'source-context')
    source_head=client.head('reference-source')
    project=base/'project';project.mkdir()
    (project/'README.md').write_text('Current project source truth.')
    (project/'src').mkdir();(project/'src'/'app.py').write_text('def answer(): return 42\n')
    (project/'.env').write_text('DO_NOT_INCLUDE')
    connection=base/'connection.json'
    connection.write_text(json.dumps(dict(endpoint_url=url,endpoint_pin='owned',
        model_contract_id=profile['model_contract_id'],execution_profile_id=profile['execution_profile_id'],
        eos_tokens=[256])))
    state=base/'run-state'
    command=[sys.executable,'-B','-m','branchwrite','code',str(project),
        '--task','Inspect the current project and preserve its interface.',
        '--connection',str(connection),'--state',str(state),'--branch','worker',
        '--read','README.md','--read-dir','src','--build-project-context',
        '--context-source-branch','reference-source','--test-command','true','--max-steps','1']
    env=dict(os.environ,BW_COW_API_KEY='prefix-key',PYTHONDONTWRITEBYTECODE='1')
    result=subprocess.run(command,capture_output=True,text=True,env=env,timeout=45)
    self.assertIn(result.returncode,(0,3),result.stderr)
    launch=read_launch(state)
    receipt= json.loads((state/'context-source-receipt.json').read_text())
    pack=launch['config']['context_pack']
    self.assertEqual(launch['config']['bindings']['project_context_receipt_sha256']['value'],
        __import__('hashlib').sha256(json.dumps(receipt,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest())
    prefix=(pathlib.Path(pack['path'])/'prefix.txt').read_text()
    self.assertIn('Current project source truth.',prefix)
    self.assertIn('Saved source example',prefix)
    self.assertIn('def answer(): return 42',prefix)
    self.assertNotIn('DO_NOT_INCLUDE',prefix)
    self.assertEqual(client.head('reference-source'),source_head)
    self.assertGreater(models[0].backend.stats['forward_tokens'],0)
    status=subprocess.run([sys.executable,'-B','-m','branchwrite','context-status',str(state),'--json'],
        capture_output=True,text=True,env=env,timeout=15)
    self.assertEqual(status.returncode,0,status.stderr)
    self.assertEqual(json.loads(status.stdout)['phase'],'PACK_DURABLE')
   finally:
    if server is not None:server.shutdown();server.server_close()
    if thread is not None:thread.join(5)
    if catalog is not None:catalog.close()
    coordinator.close()
 def exercise(self,automatic):
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
   models=[]
   def factory(gpu):
    model=BranchingModel(base/'store',GrammarCPUBackend(profile,tokenizer),profile);models.append(model);return model
   coordinator=ContextCoordinator(base/'store',PoolConfig(gpus=(0,),ram_bytes=64*1024**2,disk_bytes=256*1024**2,min_available_bytes=0),factory)
   catalog=None;server=None;thread=None
   try:
    coordinator.ready(5);adapter=CowAdapter(coordinator)
    text=CowTextAdapter(adapter,tokenizer,_render,lambda messages,rendered,add_generation_prompt:_encode(tokenizer,messages,rendered,add_generation_prompt),initial_root_mode=initial_root_mode,append_initial_user_suffix=append_initial_user_suffix,renderer_id='b'*64)
    catalog=DurableGrammarCatalog(base/'grammars',tokenizer,[256])
    from serve.cow_workspace import CowWorkspace
    workspace=CowWorkspace(coordinator.store,tokenizer,root_mode_resolver=text.root_mode_for_projection)
    server=make_server(adapter,api_key='prefix-key',text_adapter=text,grammar_catalog=catalog,workspace=workspace,
      connection_info=dict(model_contract_id=profile['model_contract_id'],execution_profile_id=profile['execution_profile_id'],eos_tokens=[256]))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    url='http://127.0.0.1:'+str(server.server_port)
    client=CowClient.http(url,journal=OperationJournal(base/'setup-journal'),api_key='prefix-key',endpoint_pin='owned')
    namespace=client.create_namespace('Prepared prefix','prefix-namespace')['namespace_id']
    if automatic:
     from branchwrite.context_pack import build_pack
     from branchwrite.golden_path import ProjectBase
     facts=base/'facts';facts.mkdir();(facts/'context.txt').write_text('Shared project context')
     pack=build_pack(root=facts,facts=['context.txt'],output=base/'packs',as_of='2026-10-19T00:00:00Z')
     project_base=ProjectBase(client,namespace,eos_tokens=(256,))
     if isinstance(automatic,str) and automatic.startswith('cli'):
      connection_path=base/'base-connection.json';connection_path.write_text(json.dumps(dict(endpoint_url=url,endpoint_pin='owned',model_contract_id=profile['model_contract_id'],execution_profile_id=profile['execution_profile_id'],eos_tokens=[256])))
      base_state=base/'base-state'
      prepare_command=[sys.executable,'-B','-m','branchwrite','prepare-base','--connection',str(connection_path),'--state',str(base_state),'--branch','source-prefix','--purpose','Review source','--context-pack',pack['pack_path'],'--context-pack-id',pack['pack_id'],'--source-revision','a'*40,'--capacity','131072','--operation-id','prepare-base-cli']
      env=dict(os.environ,BW_COW_API_KEY='prefix-key',PYTHONDONTWRITEBYTECODE='1')
      if automatic!='cli':
       if automatic=='cli-before-context':
        hook="import os,runpy;from branchwrite.cow_client import HTTPTransport;original=HTTPTransport.request\ndef request(self,method,path,*a,**kw):\n if method=='POST' and path=='/cow/text/context':os._exit(98)\n return original(self,method,path,*a,**kw)\nHTTPTransport.request=request\nrunpy.run_module('branchwrite',run_name='__main__')"
        expected=98
       else:
        target='/cow/namespace' if automatic=='cli-namespace-loss' else '/cow/text/context'
        hook="import os,runpy;from branchwrite.cow_client import OperationJournal;original=OperationJournal.complete\ndef complete(self,record,*a,**kw):\n if record['path']=="+repr(target)+":os._exit(97)\n return original(self,record,*a,**kw)\nOperationJournal.complete=complete\nrunpy.run_module('branchwrite',run_name='__main__')"
        expected=97
       interrupted=subprocess.run([sys.executable,'-B','-c',hook,*prepare_command[4:]],capture_output=True,text=True,env=env,timeout=30)
       self.assertEqual(interrupted.returncode,expected,interrupted.stderr)
       self.assertFalse((base_state/'base-catalog.json').exists())
       after_fault=dict(models[0].backend.stats);namespace_count=len(coordinator.store.namespaces())
       unresolved=subprocess.run(prepare_command,capture_output=True,text=True,env=env,timeout=30)
       self.assertEqual(unresolved.returncode,4,unresolved.stderr);self.assertEqual(models[0].backend.stats,after_fault)
       reconciled=subprocess.run([*prepare_command,'--reconcile'],capture_output=True,text=True,env=env,timeout=30)
       if automatic=='cli-before-context':
        self.assertEqual(reconciled.returncode,4,reconciled.stderr)
        self.assertFalse((base_state/'base-catalog.json').exists());self.assertEqual(models[0].backend.stats,after_fault)
        self.assertEqual(len(coordinator.store.namespaces()),namespace_count)
        self.assertNotIn('source-prefix',[head.name for head in coordinator.store.branches()])
        return
       self.assertEqual(reconciled.returncode,0,reconciled.stderr)
       if automatic=='cli-namespace-loss':
        # Namespace committed, but the prefix had not been dispatched.
        # Recovery must evaluate it once, not zero times or twice.
        count=json.loads((base_state/'base-catalog.json').read_text())[0]['prefix_tokens']
        self.assertEqual(after_fault['forward_tokens'],0)
        self.assertEqual(models[0].backend.stats['forward_tokens']-after_fault['forward_tokens'],count)
       else:self.assertEqual(models[0].backend.stats,after_fault)
       self.assertEqual(len(coordinator.store.namespaces()),namespace_count)
      prepared_cli=subprocess.run(prepare_command,capture_output=True,text=True,env=env,timeout=30)
      self.assertEqual(prepared_cli.returncode,0,prepared_cli.stderr)
      catalog_path=base_state/'base-catalog.json';derived_offer=json.loads(catalog_path.read_text())[0]
      initial_head=client.head('source-prefix')
      initial_work=dict(models[0].backend.stats)
      other=list(prepare_command);other[other.index('--state')+1]=str(base/'same-operation-other-state')
      other_result=subprocess.run(other,capture_output=True,text=True,env=env,timeout=30)
      self.assertEqual(other_result.returncode,0,other_result.stderr);self.assertEqual(models[0].backend.stats,initial_work)

      repeated=subprocess.run(prepare_command,capture_output=True,text=True,env=env,timeout=30)
      self.assertEqual(repeated.returncode,0,repeated.stderr);self.assertEqual(client.head('source-prefix'),initial_head);self.assertEqual(models[0].backend.stats,initial_work)
      catalog_path.unlink() # Lost derived publication: canonical operation journal stays.
      recovered=subprocess.run(prepare_command,capture_output=True,text=True,env=env,timeout=30)
      self.assertEqual(recovered.returncode,0,recovered.stderr);self.assertEqual(json.loads(catalog_path.read_text()),[derived_offer]);self.assertEqual(models[0].backend.stats,initial_work)
      changed=list(prepare_command);changed[changed.index('--purpose')+1]='Changed goal'
      rejected=subprocess.run(changed,capture_output=True,text=True,env=env,timeout=30)
      self.assertEqual(rejected.returncode,2);self.assertEqual(client.head('source-prefix'),initial_head)
      saved=catalog_path.read_bytes();catalog_path.write_bytes(b'[]\n')
      rejected_publication=subprocess.run(prepare_command,capture_output=True,text=True,env=env,timeout=30)
      self.assertEqual(rejected_publication.returncode,2);self.assertEqual(catalog_path.read_bytes(),b'[]\n');self.assertEqual(models[0].backend.stats,initial_work)
      catalog_path.write_bytes(saved)
      self.assertEqual(catalog_path.stat().st_mode & 0o777,0o600)

     else:
      version=project_base.prepare_pack('source-prefix','Review source',pack['pack_path'],pack['pack_id'],'prefix-context')
    else:
     prepared=client.load_context('source-prefix',namespace,[dict(role='system',content='Shared project context')],'prefix-context')
    parent=client.head('source-prefix')
    self.assertEqual(parent.tip,parent.root)
    source=base/'source';source.mkdir();(source/'app.py').write_text('pass\n');(source/'.git').mkdir()
    (source/'.git/config').write_text('private metadata')
    connection=base/'connection';connection.write_text(json.dumps(dict(endpoint_url=url,endpoint_pin='owned',model_contract_id=profile['model_contract_id'],execution_profile_id=profile['execution_profile_id'],eos_tokens=[256])))
    task=base/'task';task.write_text('Inspect the project')
    state=base/'state'
    offer=dict(base_id='1'*64,branch='source-prefix',snapshot=parent.root,source_revision='a'*40,execution_profile_id=profile['execution_profile_id'],prefix_tokens=32,capacity=131072)
    if isinstance(automatic,str) and automatic.startswith('cli'):
     offer=derived_offer
    elif automatic:
     offer=project_base.catalog_entry(version,pack_path=pack['pack_path'],source_revision='a'*40,execution_profile_id=profile['execution_profile_id'],capacity=131072)
     self.assertGreater(offer['prefix_tokens'],0)
     self.assertEqual(offer['reference_pack_id'],pack['pack_id'])
     from dataclasses import replace
     from unittest.mock import patch
     options=dict(pack_path=pack['pack_path'],source_revision='a'*40,execution_profile_id=profile['execution_profile_id'],capacity=131072)
     with self.assertRaises(ValueError):project_base.catalog_entry(version,**dict(options,execution_profile_id='f'*64))
     with self.assertRaises(ValueError):project_base.catalog_entry(replace(version,snapshot='f'*64),**options)
     with self.assertRaises(ValueError):project_base.catalog_entry(replace(version,summary='unreviewed summary'),**options)
     # Do not transfer the request receipt to another namespace or operation.
     import base64,hashlib,copy
     for field in ('branch','namespace_id','operation_id'):
      transferred=copy.deepcopy(client.journal.read(version.operation_id))
      body=json.loads(base64.b64decode(transferred['body_b64']));body[field]='different-owner'
      raw=json.dumps(body).encode();transferred['body_b64']=base64.b64encode(raw).decode();transferred['body_sha256']=hashlib.sha256(raw).hexdigest()
      with patch.object(client.journal,'read',return_value=transferred):
       with self.assertRaises(ValueError):project_base.catalog_entry(version,**options)
     history=client.history(version.branch)
     missing=dict(history.raw);missing.pop('root_input_cells')
     with patch.object(client,'history',return_value=replace(history,raw=missing)):
      with self.assertRaises(ValueError):project_base.catalog_entry(version,**options)
     # A different pack in an otherwise completed local operation is rejected.
     import base64,hashlib,copy
     record=copy.deepcopy(client.journal.read(version.operation_id))
     body=json.loads(base64.b64decode(record['body_b64']));body['messages'][0]['content']='Different reference bytes'
     raw=json.dumps(body).encode();record['body_b64']=base64.b64encode(raw).decode();record['body_sha256']=hashlib.sha256(raw).hexdigest()
     with patch.object(client.journal,'read',return_value=record):
      with self.assertRaises(ValueError):project_base.catalog_entry(version,**options)

    offers=base/'offers.json';offers.write_text(json.dumps([offer]))
    choice=base/'choice.json';choice.write_text(json.dumps(dict(schema=1,base_id='1'*64,reason='Use the offered prepared reference.')))
    command=[sys.executable,'-B','-m','branchwrite','code',str(source),'--task-file',str(task),'--connection',str(connection),'--state',str(state),'--branch','child','--project-bases',str(offers),'--base-choice',str(choice),'--base-revision','a'*40,'--base-reserve-tokens','8192','--read','app.py','--test-command','python3 -m unittest','--max-steps','1']
    if automatic:
     position=command.index('--base-choice');command[position:position+2]=['--auto-base']
     offers.write_text(json.dumps([dict(offer,base_id='2'*64,source_revision='f'*40,prefix_tokens=100000),offer]))
    bad_command=list(command);bad_command[bad_command.index('--base-revision')+1]='9'*40
    bad=subprocess.run(bad_command,capture_output=True,text=True,env=dict(os.environ,BW_COW_API_KEY='prefix-key',PYTHONDONTWRITEBYTECODE='1'),timeout=30)
    self.assertEqual(bad.returncode,2,bad.stderr);self.assertFalse(state.exists());self.assertEqual(client.head('source-prefix'),parent)
    result=subprocess.run(command,capture_output=True,text=True,env=dict(os.environ,BW_COW_API_KEY='prefix-key',PYTHONDONTWRITEBYTECODE='1'),timeout=30)
    self.assertEqual(result.returncode,3,result.stderr)
    launch=read_launch(state);self.assertEqual(launch['config']['cow']['mode'],'ask')
    self.assertEqual(launch['fork']['snapshot'],parent.root)
    decision=json.loads(launch['config']['bindings']['project_base_choice']['value']);self.assertEqual(decision['base'],offer)
    if automatic:self.assertIn('host-longest-fitting-v1',decision['reason'])
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
