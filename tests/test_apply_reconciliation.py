"""An exact owned publication can be acknowledged again without rewriting."""
import unittest,shutil
import test_project_apply as fixture
class ApplyReconciliationTests(unittest.TestCase):
 def setUp(self):
  self.case=fixture.ProjectApplyTests();self.addCleanup(self.case.doCleanups);self.case.setUp()
 def apply(self,operation='owned-op'):
  from branchwrite.project_apply import apply_export
  c=self.case.case
  return apply_export(self.case.archive,c.source,c.root/'result',expected_sha256=self.case.export['sha256'],operation_id=operation)
 def test_retry_returns_identical_receipt_after_source_changes(self):
  c=self.case.case;first=self.apply();inode=(c.root/'result').stat().st_ino
  (c.source/'app.py').write_bytes(b'new original')
  self.assertEqual(self.apply(),first);self.assertEqual((c.root/'result').stat().st_ino,inode)
 def test_other_operation_cannot_claim_existing_output(self):
  self.apply()
  with self.assertRaisesRegex(ValueError,'operation'):self.apply('other-op')
 def test_modified_published_result_is_not_acknowledged(self):
  c=self.case.case;self.apply();(c.root/'result/app.py').write_bytes(b'changed later')
  with self.assertRaisesRegex(ValueError,'inventory'):self.apply()
 def test_copying_the_receipt_does_not_copy_publication_ownership(self):
  c=self.case.case;self.apply();dest=c.root/'result';saved=c.root/'saved'
  dest.rename(saved);shutil.copytree(saved,dest)
  with self.assertRaisesRegex(ValueError,'identity'):self.apply()

 def test_process_exit_after_publication_is_reconciled_in_new_process(self):
  import subprocess,sys,json
  c=self.case.case;dest=c.root/'result'
  code="import os,sys;import branchwrite.project_apply as m;m._sync_parent=lambda dest:os._exit(71);m.apply_export(sys.argv[1],sys.argv[2],sys.argv[3],expected_sha256=sys.argv[4],operation_id='crash-op')"
  child=subprocess.run([sys.executable,'-B','-c',code,str(self.case.archive),str(c.source),str(dest),self.case.export['sha256']],capture_output=True,text=True,timeout=20)
  self.assertEqual(child.returncode,71,child.stderr);self.assertTrue(dest.is_dir());inode=dest.stat().st_ino
  args=[sys.executable,'-B','-m','branchwrite','apply',str(self.case.archive),'--source',str(c.source),'--destination',str(dest),'--sha256',self.case.export['sha256'],'--operation-id','crash-op']
  one=subprocess.run(args,capture_output=True,text=True,timeout=20)
  two=subprocess.run(args,capture_output=True,text=True,timeout=20)
  self.assertEqual(one.returncode,0,one.stderr);self.assertEqual(two.returncode,0,two.stderr)
  self.assertEqual(one.stdout,two.stdout);self.assertEqual(dest.stat().st_ino,inode)
 def test_process_exit_before_publication_can_retry_without_partial_output(self):
  import subprocess,sys
  c=self.case.case;dest=c.root/'result'
  code="import os,sys;import branchwrite.project_apply as m;m._rename_new=lambda *args:os._exit(72);m.apply_export(sys.argv[1],sys.argv[2],sys.argv[3],expected_sha256=sys.argv[4],operation_id='crash-op')"
  child=subprocess.run([sys.executable,'-B','-c',code,str(self.case.archive),str(c.source),str(dest),self.case.export['sha256']],capture_output=True,text=True,timeout=20)
  self.assertEqual(child.returncode,72,child.stderr);self.assertFalse(dest.exists())
  self.assertEqual(self.apply('crash-op')['status'],'APPLIED_NEW_COPY')
