import copy,json,tempfile,unittest
from pathlib import Path
from branchwrite import base_choice
from test_base_choice import base,REV,PROFILE
import test_base_choice_launch as fixtures
class AutoBaseChoiceTests(unittest.TestCase):
 def choose(self,rows,**kw):
  return base_choice.select_host_base(rows,required_revision=REV,required_profile=PROFILE,reserve_tokens=kw.get('reserve_tokens',200))
 def test_longest_compatible_fitting_prefix_and_stable_tie(self):
  rows=[base('3',prefix_tokens=400),base('2',prefix_tokens=400),base('1',prefix_tokens=900),base('4',source_revision='f'*40)]
  before=copy.deepcopy(rows)
  for order in [rows,list(reversed(rows))]:self.assertEqual(self.choose(order)['base']['base_id'],'2'*64)
  self.assertEqual(rows,before)
 def test_no_compatible_base_is_explicit_failure(self):
  with self.assertRaisesRegex(ValueError,'no compatible'):self.choose([base(source_revision='f'*40)])
 def test_validation_is_not_bypassed(self):
  for rows in [[],[base(),base()],[base(capacity=True)]]:
   with self.subTest(rows=rows),self.assertRaises(ValueError):self.choose(rows)
  with self.assertRaises(ValueError):self.choose([base()],reserve_tokens=True)
 def test_auto_admission_records_exact_choice_without_proposal(self):
  fixture=fixtures.BaseChoiceLaunchTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
  launch=fixture.launch(base_proposal=None,auto_base=True)
  self.assertEqual(launch['fork']['snapshot'],fixture.row['snapshot'])
  choice=json.loads(launch['config']['bindings']['project_base_choice']['value'])
  self.assertIn('host-longest-fitting-v1',choice['reason'])
  with self.assertRaises(ValueError):fixture.launch(auto_base=True)

 def test_real_cli_pins_automatic_choice_before_dispatch(self):
  import io
  from contextlib import redirect_stdout,redirect_stderr
  from unittest.mock import patch
  from branchwrite.__main__ import main
  from branchwrite.coding_cli import read_launch
  fixture=fixtures.BaseChoiceLaunchTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
  root=fixture.root;connection=root/'connection.json';connection.write_text(json.dumps(fixture.connection))
  catalog=root/'bases.json';catalog.write_text(json.dumps([fixture.row]));state=root/'auto-state'
  args=['code',str(fixture.project),'--task','Repair project','--connection',str(connection),'--state',str(state),'--branch','auto-worker','--read','main.py','--test-command','python3 -m unittest discover -s tests -v','--project-bases',str(catalog),'--auto-base','--base-revision',fixture.revision,'--base-reserve-tokens','8192']
  with patch('branchwrite.coding_cli.run_saved',return_value=(0,{'status':'ADMISSION_ONLY'})) as dispatch,redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):self.assertEqual(main(args),0)
  dispatch.assert_called_once();original=read_launch(state)
  catalog.write_text(json.dumps([dict(fixture.row,snapshot='e'*64)]))
  self.assertEqual(read_launch(state),original)
  self.assertEqual(original['fork']['snapshot'],fixture.row['snapshot'])
