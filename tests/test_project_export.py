"""Export publishes a new artifact, never overwrites the user's checkout."""
import unittest,json,zipfile,hashlib
import test_full_project_review as fixture
class ProjectExportTests(unittest.TestCase):
 def setUp(self):
  self.case=fixture.FullProjectReviewTests();self.addCleanup(self.case.doCleanups);self.case.setUp()
 def test_complete_export_contains_exact_binary_and_text_bytes(self):
  c=self.case
  def action(p):
   (p/'app.py').write_bytes(b'new')
   (p/'new.txt').write_bytes(bytes([255,0,10]))
  c.make(action)
  from branchwrite.project_export import export_changes
  dest=c.root/'changes.zip';result=export_changes(c.state,dest)
  self.assertEqual(result['status'],'EXPORTED')
  with zipfile.ZipFile(dest) as z:
   manifest=json.loads(z.read('manifest.json'))
   self.assertTrue(manifest['review']['complete_project_patch'])
   for row in manifest['review']['changes']:
    payload=z.read('payloads/'+row['after_sha256'])
    self.assertEqual(hashlib.sha256(payload).hexdigest(),row['after_sha256'])
   self.assertEqual(z.read('payloads/'+hashlib.sha256(bytes([255,0,10])).hexdigest()),bytes([255,0,10]))
  self.assertEqual((c.source/'app.py').read_bytes(),b'old')
  self.assertEqual(dest.stat().st_mode&0o777,0o600)
 def test_existing_destination_is_preserved(self):
  c=self.case;c.make(lambda p:(p/'app.py').write_bytes(b'new'))
  from branchwrite.project_export import export_changes
  dest=c.root/'existing.zip';dest.write_bytes(b'keep')
  with self.assertRaises(FileExistsError):export_changes(c.state,dest)
  self.assertEqual(dest.read_bytes(),b'keep')
 def test_failed_review_creates_no_export(self):
  c=self.case;c.make(lambda p:(p/'protected.txt').write_bytes(b'wrong'))
  from branchwrite.project_export import export_changes
  dest=c.root/'changes.zip'
  with self.assertRaises(ValueError):export_changes(c.state,dest)
  self.assertFalse(dest.exists())

 def test_export_cannot_write_into_original_project_or_run_state(self):
  c=self.case;c.make(lambda p:(p/'app.py').write_bytes(b'new'))
  from branchwrite.project_export import export_changes
  for dest in [c.source/'result.zip',c.state/'world/workspace/result.zip',c.state/'result.zip']:
   with self.assertRaisesRegex(ValueError,'outside'):export_changes(c.state,dest)
   self.assertFalse(dest.exists())
 def test_actual_cli_exports_without_changing_the_ledger(self):
  import subprocess,sys
  c=self.case;c.make(lambda p:(p/'app.py').write_bytes(b'new'))
  ledger=c.state/'ledger'
  before={str(p.relative_to(ledger)):hashlib.sha256(p.read_bytes()).hexdigest() for p in ledger.rglob('*') if p.is_file()}
  dest=c.root/'cli.zip'
  result=subprocess.run([sys.executable,'-B','-m','branchwrite','export',str(c.state),str(dest)],capture_output=True,text=True)
  self.assertEqual(result.returncode,0,result.stderr);self.assertTrue(dest.is_file())
  self.assertFalse(json.loads(result.stdout)['checkout_modified'])
  self.assertEqual(before,{str(p.relative_to(ledger)):hashlib.sha256(p.read_bytes()).hexdigest() for p in ledger.rglob('*') if p.is_file()})
