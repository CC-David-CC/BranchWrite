"""Real launcher admission: reject ambiguous JSON before any effects."""
import argparse,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from branchwrite.coding_cli import start
class ConnectionAdmissionTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name);self.project=self.root/'project';self.project.mkdir()
  (self.project/'app.py').write_text('pass\n')
  self.task=self.root/'task.txt';self.task.write_text('Repair the project')
  self.connection=dict(endpoint_url='http://127.0.0.1:1',endpoint_pin='owned',model_contract_id='model',execution_profile_id='profile',eos_tokens=[256])
  self.path=self.root/'connection.json'
  self.args=argparse.Namespace(max_steps=10,connection=str(self.path),project=str(self.project),task_file=str(self.task),branch='new',read=[],edit=['app.py'],create=[],test_command=['python3 -m unittest'],from_branch=None,from_snapshot=None,shell_timeout=120,state=str(self.root/'state'))
 def test_each_duplicate_identity_is_rejected_before_effects(self):
  for field,value in self.connection.items():
   with self.subTest(field=field):
    self.path.write_text(json.dumps(self.connection)[:-1]+','+json.dumps(field)+':'+json.dumps(value)+'}')
    with patch('branchwrite.coding_cli.run_saved') as run,patch('branchwrite.coding_cli._client') as client:
     with self.assertRaises(ValueError):start(self.args)
     run.assert_not_called();client.assert_not_called()
    self.assertFalse(Path(self.args.state).exists())
 def test_valid_connection_still_prepares_exact_launch(self):
  self.path.write_text(json.dumps(self.connection))
  with patch('branchwrite.coding_cli.run_saved',return_value={'ok':True}) as run:
   self.assertEqual(start(self.args),{'ok':True});run.assert_called_once()
  from branchwrite.coding_cli import read_launch
  cfg=read_launch(self.args.state)['config']['cow']
  for k,v in self.connection.items():self.assertEqual(cfg[k],v)
 def test_expression_is_not_executed(self):
  marker=self.root/'executed'
  self.path.write_text("__import__('pathlib').Path("+repr(str(marker))+").touch()")
  with patch('branchwrite.coding_cli.run_saved') as run:
   with self.assertRaises(ValueError):start(self.args)
   run.assert_not_called()
  self.assertFalse(marker.exists());self.assertFalse(Path(self.args.state).exists())
