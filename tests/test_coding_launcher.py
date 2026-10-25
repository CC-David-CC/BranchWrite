"""Project/task admission; launcher never owns another workflow or history."""
import json,tempfile,unittest
from pathlib import Path
class CodingLauncherTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.base=Path(self.tmp.name);self.project=self.base/'project';self.project.mkdir()
  (self.project/'app.py').write_text('broken')
  self.connection=dict(endpoint_url='http://127.0.0.1:1',endpoint_pin='owned',model_contract_id='model',execution_profile_id='profile',eos_tokens=[256])
 def build(self,**kwargs):
  from branchwrite.coding_cli import build_launch
  return build_launch(self.project,'Repair app.',self.connection,branch='coding',read_paths=['tests/test_app.py'],edit_paths=['app.py'],create_paths=['new.py'],test_commands=['python3 -m unittest'],**kwargs)
 def test_fresh_launch_uses_existing_workflow_and_explicit_grants(self):
  launch=self.build()
  cfg=launch['config']
  self.assertEqual(cfg['source'],str(self.project))
  self.assertEqual(cfg['cow']['bootstrap'],'coding')
  self.assertEqual(cfg['cow']['grammar_registration'],'inline')
  self.assertEqual(cfg['grant']['edit_paths'],['app.py'])
  self.assertEqual(set(cfg['grant']['read_paths']),{'app.py','new.py','tests/test_app.py'})
  self.assertIn('command-evidence-and-finish',launch['program'])
  self.assertEqual(cfg['verification']['commands'][0]['exit_code'],0)
 def test_experimental_check_progress_is_an_explicit_persisted_host_choice(self):
  from branchwrite.coding_cli import build_launch,save_launch,read_launch
  launch=build_launch(self.project,'Repair app.',self.connection,branch='progress',project_files=True)
  self.assertNotIn('progress_feedback',launch['config']['verification'])
  launch['config']['verification']['progress_feedback']=True
  state=self.base/'progress';save_launch(state,launch)
  self.assertEqual(read_launch(state),launch)
  bad=build_launch(self.project,'Repair app.',self.connection,branch='bad-progress',project_files=True)
  bad['config']['verification']['progress_feedback']=1
  with self.assertRaises(ValueError):save_launch(self.base/'bad-progress',bad)

 def test_exploration_is_opt_in_and_has_two_frozen_bounded_approaches(self):
  from branchwrite.coding_cli import enable_exploration,save_launch,read_launch
  original=self.build();self.assertNotIn('exploration',original['config'])
  launch=enable_exploration(self.build(),['Direct solution.','Alternative design.'])
  self.assertIn('PARALLEL.DO',launch['program'])
  self.assertIn('SELECT choose input=candidates rule=verified-first',launch['program'])
  self.assertEqual(launch['config']['exploration']['budget']['max_parallel'],2)
  state=self.base/'explore';save_launch(state,launch)
  self.assertEqual(read_launch(state),launch)
  with self.assertRaises(ValueError):enable_exploration(self.build(),['Only one.'])
 def test_retained_launch_does_not_bootstrap_or_rebase(self):
  launch=self.build(from_branch='parent',from_snapshot='a'*64)
  self.assertNotIn('bootstrap',launch['config']['cow'])
  self.assertEqual(launch['config']['cow']['mode'],'append_user')
  self.assertEqual(launch['fork'],dict(source_branch='parent',snapshot='a'*64))
 def test_connection_cannot_contain_credentials_or_unknown_fields(self):
  self.connection['api_key']='must-not-be-written'
  with self.assertRaises(ValueError):self.build()
 def test_manifest_reopens_exactly_and_cannot_be_replaced(self):
  from branchwrite.coding_cli import save_launch,read_launch
  launch=self.build();state=self.base/'run'
  save_launch(state,launch)
  self.assertEqual(read_launch(state),launch)
  changed=self.build();changed['config']['bindings']['task']['value']='Different task'
  with self.assertRaises(ValueError):save_launch(state,changed)
  self.assertEqual(read_launch(state),launch)
 def test_state_cannot_be_inside_source_or_a_symlink(self):
  from branchwrite.coding_cli import save_launch
  with self.assertRaises(ValueError):save_launch(self.project/'run',self.build())
  alias=self.base/'alias';alias.symlink_to(self.project,target_is_directory=True)
  with self.assertRaises(ValueError):save_launch(alias,self.build())
 def test_tampered_manifest_rejected(self):
  from branchwrite.coding_cli import save_launch,read_launch
  state=self.base/'run';save_launch(state,self.build())
  p=state/'coding-launch.json';raw=json.loads(p.read_text())
  raw['launch']['config']['bindings']['task']['value']='tampered'
  p.write_text(json.dumps(raw))
  with self.assertRaises(ValueError):read_launch(state)
 def test_interrupted_stage_cleanup_cannot_strand_a_published_manifest(self):
  from branchwrite.coding_cli import save_launch,read_launch
  from unittest.mock import patch
  original=Path.unlink
  def interrupted(path,*args,**kwargs):
   if path.name.startswith('.coding-launch-'):raise OSError('stage cleanup interrupted')
   return original(path,*args,**kwargs)
  state=self.base/'run';launch=self.build()
  with patch.object(Path,'unlink',interrupted):
   try:save_launch(state,launch)
   except OSError:pass
  self.assertEqual(read_launch(state),launch)
 def test_uncertain_fork_reports_original_id_and_never_starts_interpreter(self):
  from branchwrite.coding_cli import save_launch,run_saved
  from branchwrite.cow_client import OperationIndeterminate
  from unittest.mock import patch,Mock
  state=self.base/'run';launch=self.build(from_branch='parent',from_snapshot='a'*64);save_launch(state,launch)
  client=Mock();client.fork.side_effect=OperationIndeterminate('lost acknowledgment')
  with patch('branchwrite.coding_cli._client',return_value=client),patch('branchwrite.coding_cli.execute') as execute:
   with self.assertRaisesRegex(OperationIndeterminate,'bw-code-fork-'):
    run_saved(state)
   execute.assert_not_called()
  self.assertEqual(client.fork.call_args.args[:3],('parent','a'*64,'coding'))
 def test_unresolved_fork_cannot_be_published(self):
  from branchwrite.coding_cli import save_launch
  with self.assertRaises(ValueError):save_launch(self.base/'run',self.build(from_branch='parent'))

class CodingLauncherCommandTests(unittest.TestCase):
 setUp=CodingLauncherTests.setUp
 build=CodingLauncherTests.build
 def cli(self,*args):
  import os,subprocess,sys
  env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
  return subprocess.run([sys.executable,'-B','-m','branchwrite',*map(str,args)],capture_output=True,text=True,env=env,timeout=15)
 def test_code_and_resume_are_public_commands(self):
  r=self.cli('--help')
  self.assertEqual(r.returncode,0,r.stderr)
  self.assertIn('code',r.stdout);self.assertIn('resume',r.stdout)
 def test_invalid_connection_does_not_create_a_run(self):
  connection=self.base/'connection.json';connection.write_text(json.dumps(dict(self.connection,api_key='not-allowed')))
  task=self.base/'task.txt';task.write_text('Repair app')
  state=self.base/'run'
  r=self.cli('code',self.project,'--task-file',task,'--connection',connection,'--state',state,'--branch','new','--edit','app.py','--test-command','python3 -m unittest')
  self.assertEqual(r.returncode,2,r.stderr)
  self.assertIn('credentials',r.stderr)
  self.assertFalse(state.exists())
 def test_tampered_resume_does_not_create_a_world(self):
  from branchwrite.coding_cli import save_launch
  state=self.base/'run';save_launch(state,self.build())
  p=state/'coding-launch.json';value=json.loads(p.read_text());value['sha256']='0'*64;p.write_text(json.dumps(value))
  r=self.cli('resume',state)
  self.assertEqual(r.returncode,2)
  self.assertIn('integrity',r.stderr)
  self.assertFalse((state/'world').exists())

 def test_invalid_budget_fails_before_transport_or_state_creation(self):
  connection=self.base/'connection.json';connection.write_text(json.dumps(self.connection))
  task=self.base/'task.txt';task.write_text('Repair app')
  state=self.base/'run'
  r=self.cli('code',self.project,'--task-file',task,'--connection',connection,'--state',state,'--branch','new','--edit','app.py','--test-command','python3 -m unittest','--max-steps','0')
  self.assertEqual(r.returncode,2)
  self.assertIn('step budget',r.stderr)
  self.assertFalse(state.exists())
