"""Idle prepared context and completed conversation select different APIs."""
import argparse,json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch,Mock
from branchwrite.coding_cli import build_launch,save_launch,read_launch,start
class PrefixAdmissionTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.project=self.root/'project';self.project.mkdir();(self.project/'app.py').write_text('pass\n')
  self.connection=dict(endpoint_url='http://127.0.0.1:1',endpoint_pin='owned',model_contract_id='m',execution_profile_id='p',eos_tokens=[256])
  self.path=self.root/'connection';self.path.write_text(json.dumps(self.connection))
  self.task=self.root/'task';self.task.write_text('Repair project')
 def build(self,**kwargs):
  return build_launch(self.project,'Repair project',self.connection,branch='child',read_paths=['app.py'],test_commands=['python3 -m unittest'],**kwargs)
 def args(self,*,prefix):
  return argparse.Namespace(project=self.project,task_file=self.task,connection=self.path,state=self.root/'state',branch='child',read=['app.py'],edit=[],create=[],test_command=['python3 -m unittest'],from_branch=None if prefix else 'parent',from_prefix='parent' if prefix else None,from_snapshot=None,shell_timeout=12,max_steps=1)
 def test_prefix_uses_ask_without_creating_another_root(self):
  value=self.build(from_prefix='parent',from_snapshot='a'*64)
  self.assertEqual(value['config']['cow']['mode'],'ask')
  self.assertNotIn('bootstrap',value['config']['cow'])
  self.assertEqual(value['fork'],dict(source_branch='parent',snapshot='a'*64))
  save_launch(self.root/'state',value);self.assertEqual(read_launch(self.root/'state'),value)
 def test_completed_source_still_uses_append_user(self):
  value=self.build(from_branch='parent',from_snapshot='b'*64)
  self.assertEqual(value['config']['cow']['mode'],'append_user')
 def test_source_forms_are_mutually_exclusive(self):
  with self.assertRaises(ValueError):self.build(from_branch='parent',from_prefix='prefix')
 def test_default_prefix_root_is_pinned_and_never_reselected(self):
  args=self.args(prefix=True);client=Mock();client.head.return_value=SimpleNamespace(root='a'*64,tip='b'*64)
  with patch('branchwrite.coding_cli._client',return_value=client),patch('branchwrite.coding_cli.run_saved',return_value=(0,{})):
   start(args);before=(args.state/'coding-launch.json').read_bytes()
   self.assertEqual(read_launch(args.state)['fork']['snapshot'],'a'*64)
   client.head.return_value=SimpleNamespace(root='c'*64,tip='d'*64)
   start(args);self.assertEqual((args.state/'coding-launch.json').read_bytes(),before)
  client.head.assert_called_once_with('parent')
 def test_default_completed_source_still_pins_current_tip(self):
  args=self.args(prefix=False);client=Mock();client.head.return_value=SimpleNamespace(root='a'*64,tip='b'*64)
  with patch('branchwrite.coding_cli._client',return_value=client),patch('branchwrite.coding_cli.run_saved',return_value=(0,{})):start(args)
  self.assertEqual(read_launch(args.state)['fork']['snapshot'],'b'*64)
