"""CLI exposes the existing pinned reference-pack bootstrap."""
import io,json,tempfile,unittest
from contextlib import redirect_stdout,redirect_stderr
from pathlib import Path
from unittest.mock import patch
from branchwrite.context_pack import build_pack,StalePackError
from branchwrite.coding_cli import build_launch,save_launch,read_launch

class CodingPackLaunchTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
  self.project=self.root/'project';self.project.mkdir();(self.project/'app.py').write_text('pass')
  self.refs=self.root/'references';self.refs.mkdir();(self.refs/'example.txt').write_text('A reviewed example.')
  self.pack=build_pack(root=self.refs,examples=['example.txt'],output=self.root/'packs',as_of='2026-10-19T00:00:00Z')
  self.connection=dict(endpoint_url='http://127.0.0.1:1',endpoint_pin='pinned-host',model_contract_id='model',execution_profile_id='a'*64,eos_tokens=[1])
 def launch(self,**kw):
  args=dict(branch='worker',read_paths=['app.py'],test_commands=['python3 -m unittest'],context_pack=self.pack['pack_path'],context_pack_id=self.pack['pack_id']);args.update(kw)
  return build_launch(self.project,'Inspect the project.',self.connection,**args)
 def test_pack_identity_is_saved_in_existing_launch(self):
  launch=self.launch();self.assertEqual(launch['config']['context_pack'],dict(path=self.pack['pack_path'],pack_id=self.pack['pack_id']))
  self.assertEqual(launch['config']['cow']['bootstrap'],'coding');self.assertIsNone(launch['fork'])
  state=self.root/'state';save_launch(state,launch)
  (self.refs/'example.txt').write_text('Changed after admission.')
  self.assertEqual(read_launch(state),launch)
 def test_pair_is_required(self):
  for key in ['context_pack','context_pack_id']:
   with self.subTest(key=key),self.assertRaises(ValueError):self.launch(**{key:None})
 def test_stale_pack_rejected_for_new_admission(self):
  (self.refs/'example.txt').write_text('Changed before admission.')
  with self.assertRaises(StalePackError):self.launch()
 def test_pack_cannot_be_mixed_with_existing_prefix(self):
  with self.assertRaises(ValueError):self.launch(from_prefix='old-base')
  with self.assertRaises(ValueError):self.launch(from_branch='old-conversation')
 def test_cli_parser_retains_explicit_pack(self):
  from branchwrite.__main__ import main
  connection=self.root/'connection.json';connection.write_text(json.dumps(self.connection));state=self.root/'cli-state'
  argv=['code',str(self.project),'--connection',str(connection),'--state',str(state),'--task','Inspect the project.','--branch','worker','--read','app.py','--test-command','python3 -m unittest','--context-pack',self.pack['pack_path'],'--context-pack-id',self.pack['pack_id']]
  with patch('branchwrite.coding_cli.run_saved',return_value=(0,dict(status='setup-only'))) as run,redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):
   self.assertEqual(main(argv),0);run.assert_called_once()
  self.assertEqual(read_launch(state)['config']['context_pack']['pack_id'],self.pack['pack_id'])
