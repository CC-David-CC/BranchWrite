"""Client and COW coordinator restart over durable branch history; CPU fixture."""
import json, os, subprocess, sys, tempfile, threading, unittest
from pathlib import Path

class RealCowClientReceiptTests(unittest.TestCase):
 def test_client_recovers_source_and_committed_answer_receipts(self):
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
   base=Path(t); tok=ThinkingTokenizer()
   profile=dict(model_contract_id="c"*64,execution_profile_id="e"*64,model_weights_sha256="a"*64,
    execution=dict(GPU=[0],resume_contract="identical-native-operators-v1",
    generated_operator="normal-verifier-decode",selected_token_protocol="consumed-selected-receipt-v1",
    native_request_protocol="consumed-greedy-ack-v1",sampling_protocol="full-vocab-adaptive-p-u53-v7",prefill_chunk=16,capacity=131072,eos_tokens=[256]))
   models=[]
   def factory(gpu):
    model=BranchingModel(base/"store",GrammarCPUBackend(profile,tok),profile)
    models.append(model)
    return model
   cow=ContextCoordinator(base/"store",PoolConfig(gpus=(0,),ram_bytes=64*1024**2,disk_bytes=256*1024**2,min_available_bytes=0),factory)
   server=catalog=thread=None
   try:
    cow.ready(5); adapter=CowAdapter(cow)
    text=CowTextAdapter(adapter,tok,_render,lambda m,r,a:_encode(tok,m,r,a),
     initial_root_mode=initial_root_mode,append_initial_user_suffix=append_initial_user_suffix,renderer_id="b"*64)
    catalog=DurableGrammarCatalog(base/"grammars",tok,[256])
    from serve.cow_workspace import CowWorkspace
    server=make_server(adapter,api_key="receipt-test",text_adapter=text,grammar_catalog=catalog,
     workspace=CowWorkspace(cow.store,tok,root_mode_resolver=text.root_mode_for_projection))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    url="http://127.0.0.1:"+str(server.server_port)
    client=CowClient.http(url,journal=OperationJournal(base/"setup-journal"),api_key="receipt-test",endpoint_pin="test")
    ns=client.create_namespace("Reference","ns")["namespace_id"]
    client.load_context("user-conversation",ns,[
     {"role":"system","content":"Project fact: preserve API compatibility."},
     {"role":"user","content":"Latest user update: the server restarted; continue from the durable receipt."},
     {"role":"assistant","content":"Understood. I will keep this conversation tip current."}],"root-op")
    head=client.head("user-conversation")

    # Restart the COW coordinator itself, not only its HTTP listener. Reopen
    # the same durable Store and verify the source branch still names the exact
    # immutable tip before BranchWrite reads it into its own frozen context.
    port=int(url.rsplit(":",1)[1])
    server.shutdown();server.server_close();thread.join(5)
    catalog.close();catalog=None
    cow.close()
    models.clear()
    def restarted_factory(gpu):
     model=BranchingModel(base/"store",GrammarCPUBackend(profile,tok),profile)
     models.append(model)
     return model
    cow=ContextCoordinator(base/"store",PoolConfig(gpus=(0,),ram_bytes=64*1024**2,disk_bytes=256*1024**2,min_available_bytes=0),restarted_factory)
    cow.ready(5)
    adapter=CowAdapter(cow)
    text=CowTextAdapter(adapter,tok,_render,lambda m,r,a:_encode(tok,m,r,a),
     initial_root_mode=initial_root_mode,append_initial_user_suffix=append_initial_user_suffix,renderer_id="b"*64)
    catalog=DurableGrammarCatalog(base/"grammars",tok,[256])
    server=make_server(adapter,host="127.0.0.1",port=port,api_key="receipt-test",
     text_adapter=text,grammar_catalog=catalog,
     workspace=CowWorkspace(cow.store,tok,root_mode_resolver=text.root_mode_for_projection))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    self.assertEqual(client.head("user-conversation"),head)
    project=base/"project";project.mkdir();(project/"README.md").write_text("Original project contract.\\n")
    connection=base/"connection.json";connection.write_text(json.dumps(dict(endpoint_url=url,endpoint_pin="test",model_contract_id=profile["model_contract_id"],execution_profile_id=profile["execution_profile_id"],eos_tokens=[256])))
    state=base/"client-state"
    argv=[sys.executable,"-B","-m","branchwrite","code",str(project),"--task","Preserve the project contract.","--connection",str(connection),"--state",str(state),"--branch","worker","--read","README.md","--build-project-context","--context-source-branch","user-conversation","--test-command","true","--max-steps","1"]
    env=dict(os.environ,BW_COW_API_KEY="receipt-test",PYTHONDONTWRITEBYTECODE="1",PYTHONPATH=str(Path(__file__).resolve().parents[1])+os.pathsep+os.environ.get("PYTHONPATH",""))
    crash='''import os,runpy
import branchwrite.project_context as p
old=p._publish
def stop(state,name,value):
 if name=="context-source-receipt.json": os._exit(78)
 return old(state,name,value)
p._publish=stop
runpy.run_module("branchwrite",run_name="__main__")'''
    crashed=subprocess.run([sys.executable,"-B","-c",crash,*argv[4:]],cwd=Path(__file__).resolve().parents[1],env=env,capture_output=True,text=True,timeout=45)
    self.assertEqual(crashed.returncode,78,crashed.stderr)
    self.assertFalse((state/"context-source-receipt.json").exists())
    snap=list((state/"context-sources").iterdir());self.assertEqual(len(snap),1);self.assertTrue((snap[0]/"receipt.json").is_file())
    self.assertEqual(client.head("user-conversation"),head)
    before=json.loads(subprocess.run([sys.executable,"-B","-m","branchwrite","context-status",str(state),"--json"],cwd=Path(__file__).resolve().parents[1],env=env,capture_output=True,text=True,timeout=15).stdout)
    self.assertEqual(before["phase"],"SOURCE_SNAPSHOT_RECOVERY_CANDIDATE")
    self.assertEqual(before["orphaned_source_snapshots"],[snap[0].name])
    self.assertEqual(before["last_events"][-1]["phase"],"SOURCE_CAPTURE_STARTED")
    server.shutdown();server.server_close();thread.join(5)
    (project/"README.md").write_text("Changed after crash.\\n")
    recover='''import runpy
import branchwrite.coding_cli as c
c.run_saved=lambda state,max_steps=1024:(0,{"status":"PREPARED"})
runpy.run_module("branchwrite",run_name="__main__")'''
    done=subprocess.run([sys.executable,"-B","-c",recover,*argv[4:]],cwd=Path(__file__).resolve().parents[1],env=env,capture_output=True,text=True,timeout=45)
    self.assertEqual(done.returncode,0,done.stderr)
    launch=read_launch(state);receipt=json.loads((state/"context-source-receipt.json").read_text())
    prefix=(Path(launch["config"]["context_pack"]["path"])/"prefix.txt").read_text()
    self.assertIn("Original project contract.",prefix);self.assertIn("Project fact: preserve API compatibility.",prefix);self.assertIn("Latest user update: the server restarted; continue from the durable receipt.",prefix);self.assertNotIn("Changed after crash.",prefix)
    import hashlib
    digest=hashlib.sha256(json.dumps(receipt,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()).hexdigest()
    self.assertEqual(launch["config"]["bindings"]["project_context_receipt_sha256"]["value"],digest)
    status=json.loads(subprocess.run([sys.executable,"-B","-m","branchwrite","context-status",str(state),"--json"],cwd=Path(__file__).resolve().parents[1],env=env,capture_output=True,text=True,timeout=15).stdout)
    self.assertEqual(status["phase"],"PACK_DURABLE");self.assertEqual(status["source_branches"][0]["tip"],head.tip)
    self.assertTrue(any(e.get("recovered_orphan") is True for e in status["last_events"]))
    port=int(url.rsplit(":",1)[1])
    adapter=CowAdapter(cow)
    text=CowTextAdapter(adapter,tok,_render,lambda m,r,a:_encode(tok,m,r,a),
     initial_root_mode=initial_root_mode,append_initial_user_suffix=append_initial_user_suffix,renderer_id="b"*64)
    server=make_server(adapter,host="127.0.0.1",port=port,api_key="receipt-test",
     text_adapter=text,grammar_catalog=catalog,
     workspace=CowWorkspace(cow.store,tok,root_mode_resolver=text.root_mode_for_projection))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    # Kill the client after COW commits the answer, but before the client
    # journal durably publishes its receipt or the workflow ledger records return.
    kill_before_receipt='''import os,runpy
from branchwrite.cow_client import OperationJournal
original=OperationJournal.complete
def complete(self,record,receipt,*,answer=None):
 if record.get("operation_id","").startswith("bwnative-"):
  os._exit(79)
 return original(self,record,receipt,answer=answer)
OperationJournal.complete=complete
runpy.run_module("branchwrite",run_name="__main__")
'''
    killed=subprocess.run([sys.executable,"-B","-c",kill_before_receipt,"resume",str(state),"--max-steps","16"],cwd=Path(__file__).resolve().parents[1],env=env,capture_output=True,text=True,timeout=45)
    self.assertEqual(killed.returncode,79,killed.stdout+"\n"+killed.stderr)
    pending=subprocess.run([sys.executable,"-B","-m","branchwrite","status",str(state),"--json"],cwd=Path(__file__).resolve().parents[1],env=env,capture_output=True,text=True,timeout=15)
    self.assertEqual(pending.returncode,0,pending.stderr)
    rows=json.loads(pending.stdout)["pending_model_recovery"]
    self.assertEqual(len(rows),1)
    operation_id=rows[0]["operation_id"]
    from branchwrite.cow_client import OperationJournal
    journal=OperationJournal(state/"cow-operations")
    record=journal.read(operation_id)
    self.assertEqual(record["state"],"pending")
    self.assertNotIn("answer",record)
    committed_head=client.head("worker")
    self.assertEqual(client.head("user-conversation"),head)

    # Destroy and reopen the full COW coordinator/Store after server commit,
    # before BranchWrite asks for the lost local answer receipt.
    server.shutdown();server.server_close();thread.join(5)
    catalog.close();catalog=None
    cow.close()
    models.clear()
    def answer_restart_factory(gpu):
     model=BranchingModel(base/"store",GrammarCPUBackend(profile,tok),profile)
     models.append(model)
     return model
    cow=ContextCoordinator(base/"store",PoolConfig(gpus=(0,),ram_bytes=64*1024**2,disk_bytes=256*1024**2,min_available_bytes=0),answer_restart_factory)
    cow.ready(5)
    adapter=CowAdapter(cow)
    text=CowTextAdapter(adapter,tok,_render,lambda m,r,a:_encode(tok,m,r,a),
     initial_root_mode=initial_root_mode,append_initial_user_suffix=append_initial_user_suffix,renderer_id="b"*64)
    catalog=DurableGrammarCatalog(base/"grammars",tok,[256])
    server=make_server(adapter,host="127.0.0.1",port=int(url.rsplit(":",1)[1]),api_key="receipt-test",
     text_adapter=text,grammar_catalog=catalog,
     workspace=CowWorkspace(cow.store,tok,root_mode_resolver=text.root_mode_for_projection))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    self.assertEqual(client.head("worker"),committed_head)
    self.assertEqual(client.head("user-conversation"),head)
    work_before_reconcile=models[0].backend.stats["forward_tokens"]
    reconciled=subprocess.run([sys.executable,"-B","-m","branchwrite","reconcile",str(state),"--operation-id",operation_id],cwd=Path(__file__).resolve().parents[1],env=env,capture_output=True,text=True,timeout=30)
    self.assertEqual(reconciled.returncode,0,reconciled.stderr)
    result=json.loads(reconciled.stdout)
    self.assertEqual(result["status"],"reconciled")
    record=journal.read(operation_id)
    self.assertEqual(record["state"],"complete")
    self.assertIn("answer",record)
    receipt_client=CowClient.http(url,journal=journal,api_key="receipt-test",endpoint_pin="test")
    durable=receipt_client.read_completed_generation(operation_id)
    self.assertEqual(durable.answer,record["answer"])
    self.assertEqual(durable.receipt.snapshot,committed_head.tip)
    self.assertEqual(models[0].backend.stats["forward_tokens"],work_before_reconcile)
    self.assertEqual(client.head("worker"),committed_head)
    self.assertEqual(client.head("user-conversation"),head)
    native_work=models[0].backend.stats["forward_tokens"]

    # Explicit recovery reads the client-side receipt without requiring COW.
    server.shutdown();server.server_close();thread.join(5);server=thread=None
    offline_env=dict(env);offline_env.pop("BW_COW_API_KEY",None)
    inspected=subprocess.run([sys.executable,"-B","-m","branchwrite","receipt",str(state),"--operation-id",operation_id,"--json"],cwd=Path(__file__).resolve().parents[1],env=offline_env,capture_output=True,text=True,timeout=15)
    self.assertEqual(inspected.returncode,0,inspected.stderr)
    view=json.loads(inspected.stdout)
    self.assertEqual(view["status"],"DURABLE")
    self.assertEqual(view["scope"],{"exact_saved_output":True,"current_gpu_residency_proven":False,"inference_repeated_during_inspection":False})
    self.assertEqual(view["operation_id"],operation_id)
    self.assertEqual(view["cow_receipt"]["snapshot"],durable.receipt.snapshot)
    self.assertTrue(view["answer"]["available"])
    self.assertEqual(view["answer"]["text_sha256"],hashlib.sha256(durable.answer["text"].encode()).hexdigest())
    self.assertNotIn("text",view["answer"])
    revealed=subprocess.run([sys.executable,"-B","-m","branchwrite","receipt",str(state),"--operation-id",operation_id,"--show-answer","--json"],cwd=Path(__file__).resolve().parents[1],env=offline_env,capture_output=True,text=True,timeout=15)
    self.assertEqual(revealed.returncode,0,revealed.stderr)
    self.assertEqual(json.loads(revealed.stdout)["answer"]["text"],durable.answer["text"])
    recovered=subprocess.run([sys.executable,"-B","-m","branchwrite","reconcile",str(state),"--operation-id",operation_id],cwd=Path(__file__).resolve().parents[1],env=offline_env,capture_output=True,text=True,timeout=30)
    self.assertEqual(recovered.returncode,0,recovered.stderr)
    result=json.loads(recovered.stdout)
    self.assertEqual(result["status"],"reconciled")
    self.assertEqual(result["snapshot"],durable.receipt.snapshot)
    self.assertEqual(result["output_tokens"],len(durable.answer["tokens"]))
    self.assertFalse(result["workflow_advanced"])

    # Bring the same service/store back, then resume the pending ledger return.
    port=int(url.rsplit(":",1)[1])
    adapter=CowAdapter(cow)
    text=CowTextAdapter(adapter,tok,_render,lambda m,r,a:_encode(tok,m,r,a),
     initial_root_mode=initial_root_mode,append_initial_user_suffix=append_initial_user_suffix,renderer_id="b"*64)
    server=make_server(adapter,host="127.0.0.1",port=port,api_key="receipt-test",
     text_adapter=text,grammar_catalog=catalog,
     workspace=CowWorkspace(cow.store,tok,root_mode_resolver=text.root_mode_for_projection))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    resumed=subprocess.run([sys.executable,"-B","-m","branchwrite","resume",str(state),"--max-steps","1"],cwd=Path(__file__).resolve().parents[1],env=env,capture_output=True,text=True,timeout=45)
    self.assertIn(resumed.returncode,(0,3),resumed.stderr)
    self.assertEqual(client.head("worker"),committed_head)
    self.assertEqual(client.head("user-conversation"),head)
    self.assertEqual(models[0].backend.stats["forward_tokens"],native_work)
    run_status=subprocess.run([sys.executable,"-B","-m","branchwrite","status",str(state),"--json"],cwd=Path(__file__).resolve().parents[1],env=env,capture_output=True,text=True,timeout=15)
    self.assertEqual(run_status.returncode,0,run_status.stderr)
    final_status=json.loads(run_status.stdout)
    self.assertGreater(final_status["events"],0)
    self.assertEqual(final_status["pending_model_recovery"],[])
   finally:
    if server is not None:
     try: server.shutdown()
     except Exception: pass
     server.server_close()
    if thread is not None: thread.join(5)
    if catalog is not None: catalog.close()
    cow.close()

if __name__=="__main__":unittest.main()
