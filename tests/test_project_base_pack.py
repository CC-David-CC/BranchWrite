"""Pack-backed versions share GoldenVersion and canonical COW roots."""
from collections import defaultdict
from dataclasses import replace
from pathlib import Path
import tempfile,unittest
import test_cow_client_flow as fixture
from branchwrite.golden_path import ProjectBase,Observation
from branchwrite.context_pack import build_pack,refresh_pack,StalePackError,PackError

class ProjectBasePackTests(unittest.TestCase):
 def setUp(self):
  self.case=fixture.CowClientFlowTests();self.addCleanup(self.case.doCleanups);self.case.setUp()
  self.client=self.case._client('http','base-pack')
  ns=self.client.create_namespace('Base pack','base-pack-ns')['namespace_id']
  self.base=ProjectBase(self.client,ns,eos_tokens=(299,))
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.root=Path(self.temp.name)/'source';self.root.mkdir();(self.root/'code.txt').write_text('Version one')
  self.output=Path(self.temp.name)/'packs'
  self.pack=build_pack(root=self.root,facts=['code.txt'],output=self.output,as_of='2026-10-19T00:00:00Z')
  self.case.models[0].plans=defaultdict(lambda:(257,299))
 def prepare(self,pack=None,**kw):
  pack=self.pack if pack is None else pack
  args=dict(branch='base-v0',purpose='Review the project.',pack_path=pack['pack_path'],expected_pack_id=pack['pack_id'],operation_id='base-v0-op')
  args.update(kw);return self.base.prepare_pack(**args)
 def changed_pack(self):
  (self.root/'code.txt').write_text('Version two')
  return refresh_pack(self.pack['pack_path'],output=self.output,as_of='2026-10-19T01:00:00Z')
 def test_initial_pack_version_binds_exact_identity(self):
  version=self.prepare()
  self.assertEqual(version.number,0);self.assertIsNone(version.parent_snapshot)
  self.assertEqual(version.manifest_sha256,self.pack['pack_id']);self.assertIsNone(version.summary)
  self.assertIn('Version one',str(self.client.history(version.branch).raw))
 def test_rebuilt_root_keeps_lineage_without_moving_old_worker(self):
  old=self.prepare();worker=self.base.fork_worker(old,'old-worker','old-worker-fork');before=self.client.head(old.branch)
  new=self.prepare(self.changed_pack(),branch='base-v1',operation_id='base-v1-op',source=old)
  self.assertEqual(new.number,1);self.assertEqual(new.parent_snapshot,old.snapshot)
  self.assertNotEqual(new.snapshot,old.snapshot);self.assertIsNone(new.summary)
  self.assertEqual(self.client.head(old.branch),before);self.assertEqual(self.client.head(worker.name),worker)
  self.base.question(new,'new-question','What changed?','new-question-fork','new-question-op',2)
  self.assertEqual(self.client.journal.read('new-question-op')['path'],'/cow/text/ask')
 def test_observation_refresh_after_rebuild_uses_closed_root_boundary(self):
  old=self.prepare();new=self.prepare(self.changed_pack(),branch='base-v1',operation_id='base-v1-op',source=old)
  obs=Observation.from_bytes('tests','test-run',b'OK','The checked tests passed.',observed_ns=10)
  summary=self.base.refresh(new,'summary-v2',(obs,),'summary-fork','summary-op',2,now_ns=11)
  self.assertEqual(self.client.journal.read('summary-op')['path'],'/cow/text/ask')
  self.assertEqual(summary.number,2);self.assertEqual(summary.parent_snapshot,new.snapshot)
 def test_same_operation_is_idempotent_without_reprefill(self):
  first=self.prepare();trace=list(self.case.trace);stats=dict(self.case.models[0].stats);second=self.prepare()
  self.assertEqual(second,first);self.assertEqual(self.case.trace,trace);self.assertEqual(self.case.models[0].stats,stats)
 def test_stale_source_rejected_before_context_mutation(self):
  self.changed_pack()
  with self.assertRaises(StalePackError):self.prepare()
  self.assertIsNone(self.client.journal.read('base-v0-op'))
 def test_wrong_pack_id_rejected_before_context_mutation(self):
  with self.assertRaises(PackError):self.prepare(expected_pack_id='0'*64)
  self.assertIsNone(self.client.journal.read('base-v0-op'))
 def test_foreign_parent_rejected_before_context_mutation(self):
  old=self.prepare()
  with self.assertRaises(ValueError):self.prepare(branch='foreign',operation_id='foreign-op',source=replace(old,endpoint_pin='another-endpoint'))
  self.assertIsNone(self.client.journal.read('foreign-op'))

 def test_rebuild_cannot_overwrite_existing_base_branch(self):
  from branchwrite.cow_client import RequestRejected
  old=self.prepare();head=self.client.head(old.branch)
  with self.assertRaises(RequestRejected):self.prepare(self.changed_pack(),operation_id='overwrite-op',source=old)
  self.assertEqual(self.client.head(old.branch),head)
