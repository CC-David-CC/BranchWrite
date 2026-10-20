import json,tempfile,unittest
from pathlib import Path
from branchwrite.coding_cli import build_launch,save_launch,read_launch
class BaseChoiceLaunchTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name);self.project=self.root/'project';self.project.mkdir();(self.project/'main.py').write_text('pass\n')
  self.profile='b'*64;self.revision='a'*40
  self.connection=dict(endpoint_url='http://127.0.0.1:1',endpoint_pin='host-pin',model_contract_id='c'*64,execution_profile_id=self.profile,eos_tokens=[1])
  self.row=dict(base_id='1'*64,branch='reference',snapshot='d'*64,source_revision=self.revision,execution_profile_id=self.profile,prefix_tokens=30000,capacity=262144)
  self.proposal=json.dumps(dict(schema=1,base_id='1'*64,reason='Compact source fits the task.'))
 def launch(self,**changes):
  kw=dict(branch='worker',read_paths=['main.py'],test_commands=['python3 -m unittest discover -s tests -v'],base_catalog=[self.row],base_proposal=self.proposal,base_revision=self.revision,base_reserve_tokens=8192);kw.update(changes)
  return build_launch(self.project,'Repair this project.',self.connection,**kw)
 def test_selected_snapshot_and_provenance_enter_existing_launch(self):
  launch=self.launch();self.assertEqual(launch['fork'],dict(source_branch='reference',snapshot='d'*64));self.assertEqual(launch['config']['cow']['mode'],'ask');self.assertNotIn('bootstrap',launch['config']['cow'])
  decision=json.loads(launch['config']['bindings']['project_base_choice']['value']);self.assertEqual(decision['base'],self.row);self.assertEqual(decision['reason'],'Compact source fits the task.')
 def test_incompatible_selection_rejected(self):
  with self.assertRaises(ValueError):self.launch(base_revision='f'*40)
  with self.assertRaises(ValueError):self.launch(base_reserve_tokens=262144)
 def test_no_mixed_source_selection(self):
  for key in ['from_prefix','from_branch','from_snapshot']:
   with self.subTest(key=key),self.assertRaises(ValueError):self.launch(**{key:'other'})
 def test_complete_host_selection_input_required(self):
  for key in ['base_catalog','base_proposal','base_revision','base_reserve_tokens']:
   with self.subTest(key=key),self.assertRaises(ValueError):self.launch(**{key:None})
 def test_saved_choice_survives_reopen_and_changed_choice_is_rejected(self):
  launch=self.launch();state=self.root/'state';save_launch(state,launch);self.assertEqual(read_launch(state),launch)
  altered=self.launch(base_proposal=json.dumps(dict(schema=1,base_id='1'*64,reason='Different proposal.')))
  with self.assertRaises(ValueError):save_launch(state,altered)
 def test_real_cli_parser_saves_choice_before_execution(self):
  from unittest.mock import patch
  from contextlib import redirect_stdout,redirect_stderr
  import io
  from branchwrite.__main__ import main
  connection=self.root/'connection.json';connection.write_text(json.dumps(self.connection))
  catalog=self.root/'catalog.json';catalog.write_text(json.dumps([self.row]))
  proposal=self.root/'proposal.json';proposal.write_text(self.proposal)
  state=self.root/'cli-state'
  argv=['code',str(self.project),'--task','Repair this project.','--connection',str(connection),'--state',str(state),'--branch','worker','--read','main.py','--test-command','python3 -m unittest discover -s tests -v','--project-bases',str(catalog),'--base-choice',str(proposal),'--base-revision',self.revision,'--base-reserve-tokens','8192']
  with patch('branchwrite.coding_cli.run_saved',return_value=(0,{'status':'setup-only'})) as run,redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):
   self.assertEqual(main(argv),0);run.assert_called_once()
  launch=read_launch(state);self.assertEqual(launch['fork']['snapshot'],self.row['snapshot']);self.assertIn('project_base_choice',launch['config']['bindings'])
if __name__=='__main__':unittest.main()
