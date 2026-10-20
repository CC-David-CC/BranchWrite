"""Application publishes an exclusive owned copy, never edits the source."""
import unittest,hashlib
import test_full_project_review as fixture
from branchwrite.project_export import export_changes
class ProjectApplyTests(unittest.TestCase):
 def setUp(self):
  self.case=fixture.FullProjectReviewTests();self.addCleanup(self.case.doCleanups);self.case.setUp()
  c=self.case;c.make(lambda p:(p/'app.py').write_bytes(b'new'))
  self.archive=c.root/'changes.zip';self.export=export_changes(c.state,self.archive)
 def apply(self,destination=None,sha=None):
  from branchwrite.project_apply import apply_export
  c=self.case
  return apply_export(self.archive,c.source,destination or c.root/'result',expected_sha256=sha or self.export['sha256'])
 def test_exact_copy_applied_without_touching_original(self):
  c=self.case;r=self.apply();self.assertEqual(r['status'],'APPLIED_NEW_COPY')
  self.assertEqual((c.root/'result/app.py').read_bytes(),b'new')
  self.assertEqual((c.source/'app.py').read_bytes(),b'old')
  self.assertEqual((c.root/'result/protected.txt').read_bytes(),b'protected')
 def test_wrong_archive_hash_is_rejected_before_output(self):
  with self.assertRaisesRegex(ValueError,'hash'):self.apply(sha='0'*64)
  self.assertFalse((self.case.root/'result').exists())
 def test_source_drift_is_rejected(self):
  c=self.case;(c.source/'protected.txt').write_bytes(b'changed')
  with self.assertRaisesRegex(ValueError,'baseline'):self.apply()
  self.assertFalse((c.root/'result').exists())
 def test_existing_empty_destination_is_not_replaced(self):
  c=self.case;(c.root/'result').mkdir()
  with self.assertRaises(FileExistsError):self.apply()
  self.assertEqual(list((c.root/'result').iterdir()),[])
 def test_overlapping_destination_is_rejected(self):
  with self.assertRaisesRegex(ValueError,'outside'):self.apply(self.case.source/'result')

 def test_destination_created_at_publication_is_preserved(self):
  from unittest.mock import patch
  from branchwrite.project_apply import _rename_new
  dest=self.case.root/'result'
  def race(source,target):
   target.mkdir()
   _rename_new(source,target)
  with patch('branchwrite.project_apply._rename_new',side_effect=race):
   with self.assertRaises(FileExistsError):self.apply()
  self.assertEqual(list(dest.iterdir()),[])
 def test_flush_failure_before_publication_leaves_no_output(self):
  from unittest.mock import patch
  with patch('branchwrite.project_apply._sync_tree',side_effect=OSError('injected flush failure')):
   with self.assertRaises(OSError):self.apply()
  self.assertFalse((self.case.root/'result').exists())
  self.assertFalse(list(self.case.root.glob('.bw-apply-*')))

 def test_hash_pinned_but_malformed_manifest_is_rejected(self):
  import zipfile
  c=self.case
  bad=c.root/'bad.zip'
  with zipfile.ZipFile(bad,'w') as z:z.writestr('manifest.json','[]')
  from branchwrite.project_apply import apply_export
  sha=hashlib.sha256(bad.read_bytes()).hexdigest()
  with self.assertRaises(ValueError):apply_export(bad,c.source,c.root/'result',expected_sha256=sha)
  self.assertFalse((c.root/'result').exists())
