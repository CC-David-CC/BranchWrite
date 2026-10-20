"""Explicit new-run refresh connects current source bytes to an immutable COW root."""
import io,json,tempfile,unittest
from pathlib import Path
from contextlib import redirect_stdout,redirect_stderr
from unittest.mock import patch
from branchwrite.context_pack import build_pack,refresh_pack,PackError
from branchwrite.coding_cli import build_launch,read_launch

class CodingPackRefreshAdmissionTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.project=self.root/'project';self.project.mkdir();(self.project/'app.py').write_text('pass')
  self.refs=self.root/'references';self.refs.mkdir();(self.refs/'facts.txt').write_text('Old observed command.')
  self.pack=build_pack(root=self.refs,facts=['facts.txt'],output=self.root/'packs',as_of='2026-10-19T00:00:00Z')
  self.connection=dict(endpoint_url='http://127.0.0.1:1',endpoint_pin='host',model_contract_id='model',execution_profile_id='a'*64,eos_tokens=[1])
 def launch(self,**kw):
  args=dict(branch='worker',read_paths=['app.py'],test_commands=['python3 -m unittest'],context_pack=self.pack['pack_path'],context_pack_id=self.pack['pack_id'],refresh_context_pack=True)
  args.update(kw);return build_launch(self.project,'Inspect.',self.connection,**args)
 def test_changed_pack_gets_new_identity_and_frozen_provenance(self):
  old=Path(self.pack['pack_path']);before={p.name:p.read_bytes() for p in old.iterdir()}
  (self.refs/'facts.txt').write_text('New observed command.')
  launch=self.launch();pin=launch['config']['context_pack']
  self.assertNotEqual(pin['pack_id'],self.pack['pack_id'])
  self.assertIn('New observed command.',(Path(pin['path'])/'prefix.txt').read_text())
  self.assertEqual(before,{p.name:p.read_bytes() for p in old.iterdir()})
  provenance=json.loads(launch['config']['bindings']['project_base_refresh']['value'])
  self.assertEqual(provenance['previous_pack_id'],self.pack['pack_id'])
  self.assertEqual(provenance['pack_id'],pin['pack_id']);self.assertEqual(provenance['action'],'rebuilt')
 def test_unchanged_pack_retains_exact_identity(self):
  launch=self.launch();self.assertEqual(launch['config']['context_pack']['pack_id'],self.pack['pack_id'])
  self.assertEqual(len(list((self.root/'packs').iterdir())),1)
 def test_wrong_original_identity_rejected_before_new_pack(self):
  (self.refs/'facts.txt').write_text('Changed.')
  with self.assertRaises(PackError):self.launch(context_pack_id='f'*64)
  self.assertEqual(len(list((self.root/'packs').iterdir())),1)
 def test_refresh_requires_a_pack_and_new_root(self):
  for kw in [dict(context_pack=None,context_pack_id=None),dict(from_prefix='old'),dict(refresh_context_pack=1)]:
   with self.subTest(kw=kw),self.assertRaises(ValueError):self.launch(**kw)
 def test_missing_selected_source_does_not_shrink_pack(self):
  (self.refs/'facts.txt').unlink()
  with self.assertRaises(PackError):self.launch()
  self.assertEqual(len(list((self.root/'packs').iterdir())),1)
 def test_refresh_api_binds_expected_old_identity(self):
  with self.assertRaises(PackError):
   refresh_pack(self.pack['pack_path'],output=self.root/'packs',as_of='2026-10-19T01:00:00Z',expected_id='f'*64)
 def test_cli_refresh_and_resume_preserve_admission(self):
  from branchwrite.__main__ import main
  connection=self.root/'connection.json';connection.write_text(json.dumps(self.connection));state=self.root/'state'
  argv=['code',str(self.project),'--connection',str(connection),'--state',str(state),'--task','Inspect.','--branch','worker','--read','app.py','--test-command','python3 -m unittest','--context-pack',self.pack['pack_path'],'--context-pack-id',self.pack['pack_id'],'--refresh-context-pack']
  (self.refs/'facts.txt').write_text('New before admission.')
  with patch('branchwrite.coding_cli.run_saved',return_value=(0,dict(status='setup-only'))) as run,redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):
   self.assertEqual(main(argv),0);run.assert_called_once()
  admitted=read_launch(state);count=len(list((self.root/'packs').iterdir()))
  (self.refs/'facts.txt').write_text('Later external edit.')
  with patch('branchwrite.coding_cli.run_saved',return_value=(0,dict(status='resumed'))) as run,redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):
   self.assertEqual(main(['resume',str(state)]),0);run.assert_called_once_with(state,max_steps=1024)
   self.assertEqual(main(argv),2)
  self.assertEqual(read_launch(state),admitted);self.assertEqual(len(list((self.root/'packs').iterdir())),count)

if __name__=='__main__':unittest.main()
