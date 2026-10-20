"""New coding admissions choose presets; saved runs remain exact."""
import contextlib,io,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from branchwrite.coding_cli import build_launch,save_launch,read_launch
from branchwrite.coding_defaults import generation_profile
from branchwrite.__main__ import main

class CodingSamplerChoiceTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.project=self.root/'project';self.project.mkdir()
  self.connection=dict(endpoint_url='http://127.0.0.1:1',endpoint_pin='owned',model_contract_id='model',execution_profile_id='profile',eos_tokens=[256])
 def build(self,**kw):return build_launch(self.project,'Repair.',self.connection,branch='candidate',test_commands=['python3 -m unittest'],**kw)
 def test_new_admissions_select_exact_existing_presets(self):
  for sampler in ['greedy','min-p','dry-min-p']:
   with self.subTest(sampler=sampler):self.assertEqual(self.build(sampler=sampler)['config']['profiles']['control'],generation_profile(sampler))
 def test_default_keeps_existing_greedy_launch_bytes(self):
  self.assertEqual(self.build(),self.build(sampler='greedy'))
 def test_unknown_preset_fails_before_state_or_network(self):
  with self.assertRaises(ValueError):self.build(sampler='invented')
  self.assertEqual(list(self.root.iterdir()),[self.project])
 def test_saved_sampler_cannot_be_replaced_on_same_run(self):
  state=self.root/'state';original=self.build(sampler='min-p');save_launch(state,original)
  with self.assertRaises(ValueError):save_launch(state,self.build(sampler='dry-min-p'))
  self.assertEqual(read_launch(state),original)
 def test_cli_defaults_project_to_terminal_directory(self):
  args=['code','--connection',str(self.root/'connection.json'),'--state',str(self.root/'state'),'--task','Make a small page.','--branch','candidate','--test-command','python3 -m unittest']
  with patch('pathlib.Path.cwd',return_value=self.project),patch('branchwrite.coding_cli.start',return_value=(0,{})) as start,contextlib.redirect_stdout(io.StringIO()):
   self.assertEqual(main(args),0)
  self.assertEqual(start.call_args.args[0].project,self.project)
 def test_cli_defaults_connection_to_operator_config(self):
  args=['code','--state',str(self.root/'state'),'--task','Make a page.','--branch','candidate','--test-command','python3 -m unittest']
  expected=self.root/'.config'/'branchwrite'/'connection.json'
  with patch('pathlib.Path.cwd',return_value=self.project),patch('pathlib.Path.home',return_value=self.root),patch('branchwrite.coding_cli.start',return_value=(0,{})) as start,contextlib.redirect_stdout(io.StringIO()):
   self.assertEqual(main(args),0)
  self.assertEqual(start.call_args.args[0].connection,expected)
 def test_cli_generates_durable_state_and_branch_when_omitted(self):
  args=['code','--connection',str(self.root/'connection.json'),'--task','Make a page.','--test-command','python3 -m unittest']
  with patch('pathlib.Path.cwd',return_value=self.project),patch.dict('os.environ',{'XDG_STATE_HOME':str(self.root/'state-home')}),patch('branchwrite.coding_cli.start',return_value=(0,{})) as start,contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
   self.assertEqual(main(args),0)
  parsed=start.call_args.args[0]
  self.assertTrue(parsed.branch.startswith('bw-'))
  self.assertEqual(parsed.state,Path(self.root/'state-home'/'branchwrite'/'runs'/parsed.branch))
  self.assertRegex(parsed.branch,r'^bw-[0-9a-f]{16}$')
 def test_default_state_parent_is_created_private(self):
  from branchwrite.coding_cli import _prepare_default_state_parent
  state=self.root/'state-home'/'branchwrite'/'runs'/'bw-test'
  _prepare_default_state_parent(state)
  self.assertEqual((state.parents[1].stat().st_mode & 0o777),0o700)
  self.assertEqual((state.parent.stat().st_mode & 0o777),0o700)
 def test_default_state_inside_project_fails_before_creating_files(self):
  from types import SimpleNamespace
  from branchwrite.coding_cli import start
  state=self.project/'.local'/'state'/'branchwrite'/'runs'/'bw-test'
  args=SimpleNamespace(max_steps=10,_generated_state=True,state=state,project=self.project)
  with self.assertRaisesRegex(ValueError,'outside the source project'):start(args)
  self.assertEqual(list(self.project.iterdir()),[])
 def test_default_state_parent_rejects_xdg_symlink(self):
  from branchwrite.coding_cli import _prepare_default_state_parent
  target=self.root/'real-state';target.mkdir()
  link=self.root/'linked-state';link.symlink_to(target,target_is_directory=True)
  with self.assertRaises(ValueError):
   _prepare_default_state_parent(link/'branchwrite'/'runs'/'bw-test')
 def test_generated_branch_is_reported_when_state_is_explicit(self):
  args=['code','--connection',str(self.root/'connection.json'),'--state',str(self.root/'state'),'--task','Make a page.','--test-command','python3 -m unittest']
  stderr=io.StringIO()
  with patch('pathlib.Path.cwd',return_value=self.project),patch('branchwrite.coding_cli.start',return_value=(0,{})) as start,contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(stderr):
   self.assertEqual(main(args),0)
  branch=start.call_args.args[0].branch
  self.assertRegex(branch,r'^bw-[0-9a-f]{16}$')
  self.assertIn('Context COW branch: '+branch,stderr.getvalue())
 def test_cli_passes_explicit_choice_to_normal_admission(self):
  args=['code',str(self.project),'--connection',str(self.root/'connection.json'),'--state',str(self.root/'state'),'--task','Repair.','--branch','candidate','--test-command','python3 -m unittest','--sampler','min-p']
  with patch('branchwrite.coding_cli.start',return_value=(0,{})) as start,contextlib.redirect_stdout(io.StringIO()):
   self.assertEqual(main(args),0)
  self.assertEqual(start.call_args.args[0].sampler,'min-p')
