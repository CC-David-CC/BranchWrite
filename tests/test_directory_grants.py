"""Host-selected directory scope is frozen into exact grants, not a wildcard."""
import tempfile,unittest,json,contextlib,io
from pathlib import Path
from unittest.mock import patch
from branchwrite.__main__ import main
from branchwrite.coding_cli import read_launch
class DirectoryGrantTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name);self.project=self.root/'project';self.project.mkdir()
  (self.project/'src').mkdir();(self.project/'src/app.py').write_text('pass')
  (self.project/'src/雪.py').write_text('pass');(self.project/'.git').mkdir()
  (self.project/'.git/config').write_text('private');(self.project/'README.md').write_text('readme')
 def test_exact_sorted_files_skip_git_and_keep_unicode(self):
  from branchwrite.project_scope import expand_directories
  self.assertEqual(expand_directories(self.project,['.','src']),['README.md','src/app.py','src/雪.py'])
 def test_linked_directory_and_escape_are_refused(self):
  from branchwrite.project_scope import expand_directories
  (self.project/'link').symlink_to(self.root,target_is_directory=True)
  for path in ['link','../','/tmp','.git']:
   with self.subTest(path=path),self.assertRaises((ValueError,OSError)):
    expand_directories(self.project,[path])
 def test_linked_file_in_selected_tree_is_refused(self):
  from branchwrite.project_scope import expand_directories
  (self.project/'src/link').symlink_to(self.project/'README.md')
  with self.assertRaises(ValueError):expand_directories(self.project,['src'])
 def test_cli_freezes_read_and_edit_directory_without_creation_rights(self):
  connection=self.root/'connection.json'
  connection.write_text(json.dumps(dict(endpoint_url='http://127.0.0.1:1',endpoint_pin='x',model_contract_id='m',execution_profile_id='p',eos_tokens=[256])))
  state=self.root/'state'
  args=['code',str(self.project),'--task','Fix app','--connection',str(connection),'--state',str(state),'--branch','r','--read-dir','.','--edit-dir','src','--test-command','true']
  with patch('branchwrite.coding_cli.run_saved',return_value=(0,{'verified':True})),contextlib.redirect_stdout(io.StringIO()):
   try:code=main(args)
   except SystemExit as exc:code=exc.code
  self.assertEqual(code,0)
  grant=read_launch(state)['config']['grant']
  self.assertEqual(grant['edit_paths'],['src/app.py','src/雪.py'])
  self.assertEqual(grant['create_paths'],[])
  (self.project/'src/new.py').write_text('pass')
  self.assertNotIn('src/new.py',read_launch(state)['config']['grant']['read_paths'])
