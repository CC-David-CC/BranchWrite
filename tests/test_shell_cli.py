"""Generic shell admission and real namespace execution; no model-output simulation."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,tempfile,time,unittest
from unittest.mock import patch
from branchwrite.execution import Executor,Grant,ToolRejected
from branchwrite.tool_registry import ToolRegistry,EffectIndeterminate

class ShellTests(unittest.TestCase):
 def make(self,root,*,timeout=2,allow=True):
  from branchwrite.terminal import ShellConfig
  s=root/'source';s.mkdir();(s/'marker.txt').write_bytes(b'marker-123\n');(s/'hidden.txt').write_bytes(b'not-granted\n')
  e=Executor.create(s,root/'run',shell=ShellConfig(timeout=timeout))
  g=Grant((),False,read_paths=('marker.txt',),allow_shell=allow)
  return e,g,ToolRegistry(e,g)
 def proposal(self,text):return json.dumps(dict(tool='run_shell',arguments=dict(command=text)))
 def test_real_shell_quotes_streams_exit_and_pipeline_semantics(self):
  with tempfile.TemporaryDirectory() as t:
   e,g,r=self.make(Path(t))
   command="printf '%s\\n' 'literal $HOME' 'Δ'; printf 'error-only\\n' >&2; exit 7"
   v=r.execute(r.freeze(self.proposal(command)),'streams')
   self.assertEqual((v.disposition,v.exit_code,v.stdout,v.stderr),('exited',7,'literal $HOME\nΔ\n'.encode(),b'error-only\n'))
   self.assertEqual(v.metadata['argv'][-1],command);self.assertEqual(v.metadata['isolation']['namespace_members_after'],[])
   for index,(text,code) in enumerate([("(exit 7) | cat",0),("set -o pipefail; (exit 7) | cat",7)]):
    v=r.execute(r.freeze(self.proposal(text)),'pipeline-'+str(index));self.assertEqual(v.exit_code,code)
 def test_ungranted_shell_is_absent_and_rejects_before_spawn(self):
  with tempfile.TemporaryDirectory() as t:
   e,g,r=self.make(Path(t),allow=False)
   self.assertNotIn('run_shell',[v['properties']['tool']['enum'][0] for v in r.model_schema()['oneOf']])
   with patch('subprocess.Popen') as spawn:
    with self.assertRaises(ToolRejected):r.freeze(self.proposal('echo denied'))
    with self.assertRaises(ToolRejected):e.run_shell('denied',g,'echo denied')
   spawn.assert_not_called()
 def test_schema_grammar_and_host_agree_on_granted_command_field(self):
  with tempfile.TemporaryDirectory() as t:
   e,g,r=self.make(Path(t))
   schema=next(v for v in r.model_schema()['oneOf'] if v['properties']['tool']['enum']==['run_shell'])
   self.assertEqual(schema['properties']['arguments']['required'],['command'])
   self.assertEqual(schema['properties']['arguments']['properties']['command']['maxLength'],16384)
   self.assertIn('shell-command',r.model_gbnf())
   for value in ['', 'x'*16385, '\u03bb'*9000, 'bad\0command']:
    with self.subTest(value=value[:30]),self.assertRaises(ToolRejected):r.freeze(self.proposal(value))
 def test_actual_host_binding_and_readable_marker_are_preserved(self):
  with tempfile.TemporaryDirectory() as t:
   e,g,r=self.make(Path(t));v=r.execute(r.freeze(self.proposal('pwd; cat marker.txt; id -u; id -ru; id -g; cat /etc/os-release')),'host')
   self.assertEqual(v.exit_code,0,v.stderr)
   lines=v.stdout.decode().splitlines()
   self.assertEqual(lines[:5],[str(e.workspace),'marker-123',str(os.geteuid()),str(os.getuid()),str(os.getgid())])
   self.assertEqual(v.metadata['execution_host'],dict(hostname=os.uname().nodename,uid=os.getuid(),euid=os.geteuid(),gid=os.getgid()))
   self.assertEqual(v.metadata['inputs'][0]['sha256'],hashlib.sha256(b'marker-123\n').hexdigest())
 def test_shell_cannot_write_workspace_or_read_hidden_home_credentials_devices(self):
  with tempfile.TemporaryDirectory() as t:
   e,g,r=self.make(Path(t))
   code='! test -e hidden.txt && ! test -e /home/dflanag3/.ssh && ! test -e /dev/nvidia0 && test -z "$(printenv BW_TEST_SECRET)" && ! (printf bad >marker.txt) && ! (printf bad >new.txt) && cat marker.txt'
   with patch.dict(os.environ,{'BW_TEST_SECRET':'not-for-child'}):
    v=r.execute(r.freeze(self.proposal(code)),'isolation')
   self.assertEqual(v.exit_code,0,v.stderr);self.assertEqual(v.stdout,b'marker-123\n')
   self.assertEqual((e.workspace/'marker.txt').read_bytes(),b'marker-123\n');self.assertFalse((e.workspace/'new.txt').exists())
 def test_frozen_shell_plan_rejects_changed_world_before_execution(self):
  with tempfile.TemporaryDirectory() as t:
   e,g,r=self.make(Path(t));plan=r.freeze(self.proposal('cat marker.txt'))
   (e.workspace/'marker.txt').write_bytes(b'changed\n')
   with patch('subprocess.Popen') as spawn:
    with self.assertRaisesRegex(ToolRejected,'stale'):r.execute(plan,'stale')
   spawn.assert_not_called()
 def test_config_identity_changes_and_substitution_are_rejected(self):
  from branchwrite.terminal import ShellConfig
  with tempfile.TemporaryDirectory() as t:
   e,g,r=self.make(Path(t));plan=r.freeze(self.proposal('cat marker.txt'))
   e._shell=ShellConfig(timeout=1)
   with self.assertRaises(ToolRejected):r.execute(plan,'substitution')
   other=ToolRegistry(e,g);self.assertNotEqual(r.identity,other.identity)
   with self.assertRaises(ToolRejected):other.execute(plan,'foreign')
 def test_timeout_kills_descendants_before_publication(self):
  with tempfile.TemporaryDirectory() as t:
   e,g,r=self.make(Path(t),timeout=.2)
   started=time.monotonic();v=r.execute(r.freeze(self.proposal('sleep 60 & wait')),'timeout')
   self.assertEqual(v.disposition,'timeout');self.assertLess(time.monotonic()-started,5)
   self.assertEqual(v.metadata['isolation']['namespace_members_after'],[])
 def test_receipt_failure_remains_indeterminate(self):
  with tempfile.TemporaryDirectory() as t:
   e,g,r=self.make(Path(t));plan=r.freeze(self.proposal('printf observed'))
   with patch.object(e,'_result',side_effect=OSError('injected receipt failure')):
    with self.assertRaises(EffectIndeterminate):r.execute(plan,'original')
 def test_shell_configuration_validates_before_workspace_creation(self):
  from branchwrite.terminal import ShellConfig
  for timeout in [True,0,-1,float('nan'),121]:
   with self.subTest(timeout=timeout),self.assertRaises(ToolRejected):ShellConfig(timeout=timeout)
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);source=root/'source';source.mkdir()
   with self.assertRaises(ToolRejected):Executor.create(source,root/'run',shell={'timeout':2})
   self.assertFalse((root/'run').exists())

class ShellCliTests(unittest.TestCase):
 def test_real_subprocess_cli_shell_then_read_finish_and_offline_reopen(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);source=root/'source';source.mkdir();(source/'marker.txt').write_bytes(b'original\n')
   actions=[('shell','run_shell',dict(command="printf 'out\\n'; printf 'err\\n' >&2; exit 7")),
    ('read','read_file',dict(path='marker.txt')),('finish','finish',dict(answer='actual file unchanged'))]
   cfg=dict(schema=1,source=str(source),run_id='shell-cli',grant=dict(edit_paths=[],read_paths=['marker.txt'],create_paths=[],allow_tests=False,allow_shell=True),
    shell=dict(timeout=2),profiles={},verification=dict(schema=1,files=[dict(path='marker.txt',sha256=hashlib.sha256(b'original\n').hexdigest())]),
    bindings={n:dict(type='ToolProposal',value=json.dumps(dict(tool=tool,arguments=args))) for n,tool,args in actions})
   config=root/'config.json';config.write_text(json.dumps(cfg))
   code=['FLOW shell']
   for n,_,_ in actions:code.extend([f'PLAN plan-{n} from={n} against=world -> plan',f'ACT act-{n} plan=plan -> outcome'])
   code.extend(['VERIFY check input=outcome contract=file-readback-and-finish -> verified','END'])
   program=root/'job.bw';program.write_text('\n'.join(code)+'\n');state=root/'state'
   command=[sys.executable,'-B','-m','branchwrite','run',str(program),'--config',str(config),'--state',str(state)]
   done=subprocess.run(command,capture_output=True,timeout=20)
   self.assertEqual(done.returncode,0,done.stderr);self.assertTrue(json.loads(done.stdout)['verified'])
   from branchwrite.records import RuntimeLog,Artifact,decode
   from branchwrite.kernel import FrameKernel
   with RuntimeLog(state/'ledger') as log:
    kernel=FrameKernel(log);values=[]
    for frame in kernel.frames():
     if frame['contract']==('ToolOutcome','record') and frame['result']:
      values.append(decode(log.read_artifact(Artifact(*frame['result'])))[2])
    row=next(v for v in values if v['tool']=='run_shell')
    self.assertEqual(row['exit_code'],7);self.assertEqual(log.read_artifact(Artifact(*row['stdout'])),b'out\n')
    self.assertEqual(log.read_artifact(Artifact(*row['stderr'])),b'err\n')
   before={str(f.relative_to(state)):f.read_bytes() for f in state.rglob('*') if f.is_file()}
   again=subprocess.run(command,capture_output=True,timeout=20)
   self.assertEqual((again.returncode,again.stdout),(done.returncode,done.stdout),again.stderr)
   self.assertEqual(before,{str(f.relative_to(state)):f.read_bytes() for f in state.rglob('*') if f.is_file()})
   self.assertEqual((source/'marker.txt').read_bytes(),b'original\n')
 def test_shell_grants_require_explicit_configuration_and_prefix_uses_it(self):
  from branchwrite.run_cli import _config
  from branchwrite.coding_defaults import system_prefix
  cfg=dict(schema=1,source='/source',run_id='denied',grant=dict(edit_paths=[],read_paths=[],create_paths=[],allow_tests=False,allow_shell=True),bindings={})
  with self.assertRaises(ValueError):_config(json.dumps(cfg))
  cfg['shell']=dict(timeout=3)
  self.assertEqual(_config(json.dumps(cfg))['shell'],dict(timeout=3))
  with tempfile.TemporaryDirectory() as t:
   _,_,registry=ShellTests().make(Path(t))
   prefix=system_prefix(registry.model_schema())
   self.assertIn('run_shell',prefix);self.assertNotIn('Do not use shell commands.',prefix)
   self.assertIn('read-only',prefix)

class ShellCowIntegrationTests(unittest.TestCase):
 def test_actual_http_model_flow_receives_real_shell_streams_and_status(self):
  # Scripted CPU model choices test transport, not model quality or GPU.
  import test_cow_client_flow as fixture
  from collections import defaultdict
  from branchwrite.coding_defaults import workflow_source
  case=fixture.CowClientFlowTests();self.addCleanup(case.doCleanups);case.setUp()
  root=Path(case.temp.name);source=root/'source';source.mkdir();(source/'marker.txt').write_bytes(b'unchanged\n')
  actions=[dict(tool='run_shell',arguments=dict(command="printf 'literal $HOME\\n'; printf 'real-error\\n' >&2; exit 7")),
   dict(tool='read_file',arguments=dict(path='marker.txt')),dict(tool='finish',arguments=dict(answer='actual status was seven; marker unchanged'))]
  stream=iter(tuple(json.dumps(x).encode())+(299,) for x in actions)
  case.models[0].plans=defaultdict(lambda:next(stream))
  cfg=dict(schema=1,source=str(source),run_id='shell-http',grant=dict(edit_paths=[],read_paths=['marker.txt'],create_paths=[],allow_tests=False,allow_shell=True),
   shell=dict(timeout=2),bindings=dict(task=dict(type='Text',value='Run a shell probe and read marker.txt.')),
   verification=dict(schema=1,files=[dict(path='marker.txt',sha256=hashlib.sha256(b'unchanged\n').hexdigest())]),
   profiles=dict(control=dict(output_format='text',settings=dict(temperature=0),request_tokens=1024)),
   cow=dict(endpoint_url=case.base_url,endpoint_pin='flow-model-free',model_contract_id='flow-model',execution_profile_id='flow-profile',eos_tokens=[299],branch='shell-cpu',mode='ask',bootstrap='coding'))
  config=root/'config.json';config.write_text(json.dumps(cfg))
  program=root/'coding.bw';program.write_text(workflow_source().replace('contract=unit-tests-and-finish','contract=file-readback-and-finish'))
  command=[sys.executable,'-B','-m','branchwrite','run',str(program),'--config',str(config),'--state',str(root/'run')]
  env={**os.environ,'BW_COW_API_KEY':'cpu-flow-secret'}
  done=subprocess.run(command,capture_output=True,env=env,timeout=20)
  self.assertEqual(done.returncode,0,done.stderr);self.assertTrue(json.loads(done.stdout)['verified'])
  self.assertEqual(len(case.trace),3)
  history=case._client('http','inspect-shell').history('shell-cpu')
  text='\n'.join(m['text'] for m in history.messages)
  self.assertIn('literal $HOME',text);self.assertIn('real-error',text)
  self.assertIn('"exit_code":7',text.replace(' ',''))
  case._stop_server()
  again=subprocess.run(command,capture_output=True,env=env,timeout=20)
  self.assertEqual((again.returncode,again.stdout),(done.returncode,done.stdout),again.stderr)
  self.assertEqual((source/'marker.txt').read_bytes(),b'unchanged\n')


 def test_actual_gbnf_and_json_schema_compile_shell_and_reject_ungranted_tools(self):
  from serve.cow_grammar import GrammarRegistry
  from test_grammar_first import TinyByteTokenizer
  from context_time_travel.store import IntegrityError
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);_,_,registry=ShellTests().make(root)
   tokenizer=TinyByteTokenizer()
   for fmt,source,sort_keys in [('gbnf',registry.model_gbnf(),False),('json_schema',registry.model_schema(),True)]:
    with self.subTest(format=fmt):
     f=root/(fmt+'.json');f.write_text(json.dumps(dict(schema=1,states=dict(SHELL=dict(format=fmt,source=source)))))
     grammar=GrammarRegistry.load(f,tokenizer,[tokenizer.EOS])
     def consume(text):
      state=grammar.start('SHELL','cpu-shell-contract',[],len(tokenizer.tokens));session=grammar.restore(state,[])
      for token in tokenizer.encode(text,parse_special=False):state=session.consume(state,token,tokenizer.token_bytes(token),False)
      return session
     def proposal(tool,**arguments):return json.dumps(dict(tool=tool,arguments=arguments),sort_keys=sort_keys)
     self.assertTrue(consume(proposal('run_shell',command='printf "literal $HOME\\n"; exit 7')).is_complete())
     with self.assertRaises(IntegrityError):consume(proposal('grant_shell',command='echo denied'))

if __name__=='__main__':unittest.main()
