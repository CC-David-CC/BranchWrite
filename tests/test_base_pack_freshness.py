import json,tempfile,unittest
from pathlib import Path
from branchwrite.context_pack import build_pack,StalePackError
from branchwrite.base_choice import select_host_base,resolve_base_proposal
from test_base_choice import base,REV,PROFILE
class BasePackFreshnessTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.sources=self.root/'source';self.sources.mkdir();(self.sources/'facts.txt').write_text('current source facts\n')
  receipt=build_pack(root=self.sources,facts=['facts.txt'],output=self.root/'packs',as_of='2026-10-19T12:00:00Z')
  self.row=base(reference_pack_path=str(self.root/'packs'/receipt['pack_id']),reference_pack_id=receipt['pack_id'])
 def choose(self,rows):return select_host_base(rows,required_revision=REV,required_profile=PROFILE,reserve_tokens=200)
 def test_fresh_pack_bound_base_is_selected_and_binding_preserved(self):self.assertEqual(self.choose([self.row])['base'],self.row)
 def test_changed_source_excludes_stale_base_and_selects_fresh_alternative(self):
  (self.sources/'facts.txt').write_text('changed facts\n')
  receipt=build_pack(root=self.sources,facts=['facts.txt'],output=self.root/'packs',as_of='2026-10-19T13:00:00Z')
  fallback=base('2',prefix_tokens=50,reference_pack_path=str(self.root/'packs'/receipt['pack_id']),reference_pack_id=receipt['pack_id'])
  self.assertEqual(self.choose([self.row,fallback])['base'],fallback)
  with self.assertRaisesRegex(ValueError,'no compatible'):self.choose([self.row])
 def test_explicit_choice_cannot_bypass_source_freshness(self):
  (self.sources/'facts.txt').unlink()
  with self.assertRaises(StalePackError):resolve_base_proposal(json.dumps(dict(schema=1,base_id=self.row['base_id'],reason='Use it')), [self.row],required_revision=REV,required_profile=PROFILE,reserve_tokens=200)
 def test_partial_binding_and_relative_pack_path_rejected(self):
  for row in [dict(self.row,reference_pack_path='relative'),{k:v for k,v in self.row.items() if k!='reference_pack_id'}]:
   with self.subTest(row=row),self.assertRaises(ValueError):self.choose([row])
 def test_wrong_pack_identity_fails_without_fallback(self):
  with self.assertRaises(ValueError):self.choose([dict(self.row,reference_pack_id='f'*64),base('2')])

 def test_pack_catalog_does_not_fall_back_to_unverified_legacy_entry(self):
  (self.sources/'facts.txt').write_text('changed\n')
  with self.assertRaisesRegex(ValueError,'no compatible'):self.choose([self.row,base('2')])
 def test_incompatible_pack_is_not_opened(self):
  incompatible=dict(self.row,base_id='2'*64,execution_profile_id='f'*64,reference_pack_path='/does/not/exist')
  self.assertEqual(self.choose([self.row,incompatible])['base'],self.row)

 def test_stale_pack_fails_cli_admission_before_state_or_dispatch(self):
  import io
  from contextlib import redirect_stdout,redirect_stderr
  from unittest.mock import patch
  import test_base_choice_launch as fixtures
  from branchwrite.__main__ import main
  f=fixtures.BaseChoiceLaunchTests();f.setUp();self.addCleanup(f.doCleanups)
  connection=f.root/'connection.json';connection.write_text(json.dumps(f.connection))
  offered=dict(f.row,reference_pack_path=self.row['reference_pack_path'],reference_pack_id=self.row['reference_pack_id'])
  catalog=f.root/'catalog.json';catalog.write_text(json.dumps([offered]));state=f.root/'state'
  (self.sources/'facts.txt').write_text('now stale\n')
  args=['code',str(f.project),'--task','Repair project','--connection',str(connection),'--state',str(state),'--branch','worker','--project-bases',str(catalog),'--auto-base','--base-revision',f.revision,'--base-reserve-tokens','8192','--read','main.py','--test-command','python3 -m unittest']
  with patch('branchwrite.coding_cli.run_saved') as dispatch,redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):self.assertEqual(main(args),2)
  dispatch.assert_not_called();self.assertFalse(state.exists())
