"""Actual COW HTTP fixture: refreshed packs never rebrand existing roots."""
import tempfile,unittest
from pathlib import Path
import test_cow_client_flow as fixture
from branchwrite.context_pack import build_pack,refresh_pack,load_verified_prefix

class ContextPackRefreshHTTPTests(unittest.TestCase):
 def setUp(self):
  self.case=fixture.CowClientFlowTests();self.addCleanup(self.case.doCleanups);self.case.setUp()
 def test_new_pack_admission_preserves_original_base_and_worker(self):
  c=self.case._client('http','pack-refresh')
  ns=c.create_namespace('Pack refresh','pack-refresh-ns')['namespace_id']
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory)/'source';root.mkdir();(root/'facts.txt').write_text('Revision one: run the unit suite.')
   first=build_pack(root=root,facts=['facts.txt'],output=Path(directory)/'packs',as_of='2026-10-19T00:00:00Z')
   first_text=load_verified_prefix(first['pack_path'])
   a=c.load_context('base-v1',ns,[dict(role='system',content=first_text)],'base-v1-root')
   worker=c.fork('base-v1',a.receipt.snapshot,'worker-from-v1','worker-v1-fork')
   old_head=c.head('base-v1');old_history=c.history('base-v1')
   (root/'facts.txt').write_text('Revision two: run the unit suite and the parser suite.')
   second=refresh_pack(first['pack_path'],output=Path(directory)/'packs',as_of='2026-10-19T01:00:00Z')
   b=c.load_context('base-v2',ns,[dict(role='system',content=load_verified_prefix(second['pack_path']))],'base-v2-root')
   self.assertNotEqual(a.receipt.snapshot,b.receipt.snapshot)
   self.assertNotEqual(a.receipt.branch.root,b.receipt.branch.root)
   self.assertEqual(c.head('base-v1'),old_head)
   self.assertEqual(c.history('base-v1'),old_history)
   self.assertEqual(c.head('worker-from-v1'),worker)
   self.assertEqual(Path(first['pack_path'],'prefix.txt').read_text(),first_text)
