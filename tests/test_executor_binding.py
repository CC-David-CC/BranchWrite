"""Expected-host admission, real CLI denial, and existing frozen tool boundary."""
from pathlib import Path
import dataclasses,json,os,subprocess,sys,tempfile,threading,types,unittest
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from unittest.mock import patch
from branchwrite.execution import Executor,Grant,ToolRejected
from branchwrite.tool_registry import ToolRegistry

class ExecutorBindingTests(unittest.TestCase):
 def test_actual_expected_host_is_immutable_and_in_execution_identity(self):
  from branchwrite.terminal import ShellConfig
  a=ShellConfig(timeout=2,expected_hostname=os.uname().nodename)
  b=ShellConfig(timeout=2)
  self.assertNotEqual(a.wire,b.wire)
  self.assertIn(os.uname().nodename,str(a.wire))
  with self.assertRaises(dataclasses.FrozenInstanceError):a.expected_hostname='elsewhere'
 def test_wrong_host_rejects_before_process_or_workspace_creation(self):
  from branchwrite.terminal import ShellConfig
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);source=root/'source';source.mkdir()
   with patch('subprocess.Popen') as spawn:
    with self.assertRaisesRegex(ToolRejected,'executor host mismatch'):
     Executor.create(source,root/'world',shell=ShellConfig(timeout=2,expected_hostname='wrong-'+os.uname().nodename))
   spawn.assert_not_called();self.assertFalse((root/'world').exists())
 def test_hostname_admission_rejects_malformed_or_nontext_bindings(self):
  from branchwrite.terminal import ShellConfig
  for value in ['',True,1,'with space','line\nbreak','/path','x'*254]:
   with self.subTest(value=value),self.assertRaises(ToolRejected):ShellConfig(expected_hostname=value)
 def test_cli_configuration_preserves_explicit_binding_and_legacy_omission(self):
  from branchwrite.run_cli import _config
  base=dict(schema=1,source='/source',run_id='binding',grant=dict(edit_paths=[],read_paths=[],create_paths=[],allow_tests=False,allow_shell=True),bindings={},shell=dict(timeout=2))
  self.assertEqual(_config(json.dumps(base))['shell'],dict(timeout=2))
  base['shell']['expected_hostname']=os.uname().nodename
  self.assertEqual(_config(json.dumps(base))['shell']['expected_hostname'],os.uname().nodename)
  base['shell']['trust_model_hostname']=True
  with self.assertRaises(ValueError):_config(json.dumps(base))
 def test_frozen_plan_rechecks_host_before_any_effect(self):
  from branchwrite.terminal import ShellConfig
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);source=root/'source';source.mkdir();(source/'note.txt').write_text('unchanged\n')
   executor=Executor.create(source,root/'world',shell=ShellConfig(expected_hostname=os.uname().nodename))
   registry=ToolRegistry(executor,Grant((),False,read_paths=('note.txt',),allow_shell=True))
   plan=registry.freeze(json.dumps(dict(tool='read_file',arguments=dict(path='note.txt'))))
   with patch('branchwrite.terminal.os.uname',return_value=types.SimpleNamespace(nodename='changed-host')),patch('subprocess.Popen') as spawn:
    with self.assertRaisesRegex(ToolRejected,'executor host mismatch'):registry.execute(plan,'original-operation')
   spawn.assert_not_called();self.assertEqual((executor.workspace/'note.txt').read_text(),'unchanged\n')
 def test_real_cli_wrong_host_stops_before_http_or_state_creation(self):
  seen=[]
  class Handler(BaseHTTPRequestHandler):
   def do_GET(self):
    seen.append(self.path);self.send_response(500);self.end_headers()
   def log_message(self,*a):pass
  server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
  thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  try:
   with tempfile.TemporaryDirectory() as t:
    root=Path(t);source=root/'source';source.mkdir();(source/'keep.txt').write_bytes(b'untouched\n')
    expected='wrong-'+os.uname().nodename;port=server.server_address[1]
    cfg=dict(schema=1,source=str(source),run_id='wrong-host',grant=dict(edit_paths=[],read_paths=[],create_paths=[],allow_tests=False,allow_shell=True),shell=dict(timeout=2,expected_hostname=expected),profiles={},
     bindings=dict(done=dict(type='ToolProposal',value=json.dumps(dict(tool='finish',arguments=dict(answer='not reached'))))),
     cow=dict(endpoint_url='http://127.0.0.1:'+str(port),endpoint_pin='owned-listener',model_contract_id='not-used',execution_profile_id='not-used',eos_tokens=[1],branch='not-used',mode='ask'))
    config=root/'host.json';config.write_text(json.dumps(cfg))
    program=root/'job.bw';program.write_text('FLOW test\nPLAN p from=done against=world -> plan\nACT a plan=plan -> outcome\nEND\n')
    state=root/'state'
    r=subprocess.run([sys.executable,'-B','-m','branchwrite','run',str(program),'--config',str(config),'--state',str(state)],capture_output=True,text=True,timeout=10,env={**os.environ,'BW_COW_API_KEY':'unused-test-key'})
    self.assertEqual(r.returncode,2,r.stderr);self.assertIn('executor host mismatch',r.stderr)
    self.assertIn(expected,r.stderr);self.assertIn(os.uname().nodename,r.stderr)
    self.assertEqual(seen,[]);self.assertFalse(state.exists());self.assertEqual((source/'keep.txt').read_bytes(),b'untouched\n')
  finally:server.shutdown();thread.join(timeout=3);server.server_close()
if __name__=='__main__':unittest.main()
