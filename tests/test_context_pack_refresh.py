"""Refresh derives a new immutable pack; existing contexts remain pinned."""
import contextlib,io,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from branchwrite import context_pack as packs

class ContextPackRefreshTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.root=Path(self.temp.name)/'source';self.root.mkdir()
  (self.root/'facts').mkdir();(self.root/'facts/a.txt').write_text('old source\n')
  self.output=Path(self.temp.name)/'packs'
  self.old=packs.build_pack(root=self.root,facts=['facts'],output=self.output,as_of='2026-10-19T00:00:00Z')
  self.path=Path(self.old['pack_path'])
  self.before={p.name:p.read_bytes() for p in self.path.iterdir()}
  self.next=Path(self.temp.name)/'next'
 def refresh(self):
  return packs.refresh_pack(self.path,output=self.next,as_of='2026-10-19T01:00:00Z')
 def assert_old_unchanged(self):
  self.assertEqual({p.name:p.read_bytes() for p in self.path.iterdir()},self.before)
 def test_unchanged_does_not_publish_or_retimestamp(self):
  r=self.refresh()
  self.assertEqual(r['action'],'unchanged');self.assertEqual(r['pack_id'],self.old['pack_id'])
  self.assertEqual(r['as_of'],self.old['as_of']);self.assertFalse(self.next.exists())
  self.assertEqual(r['changes'],[]);self.assert_old_unchanged()
 def test_modified_source_builds_new_identity_with_exact_content(self):
  (self.root/'facts/a.txt').write_text('new source\n')
  r=self.refresh();self.assertEqual(r['action'],'rebuilt')
  self.assertEqual(r['previous_pack_id'],self.old['pack_id']);self.assertNotEqual(r['pack_id'],self.old['pack_id'])
  self.assertEqual(r['changes'],[dict(section='facts',path='facts/a.txt',kind='modified')])
  self.assertEqual(packs.verify_pack(r['pack_path'])['status'],'fresh')
  self.assertIn('new source\n',packs.load_verified_prefix(r['pack_path']))
  self.assertEqual(packs.verify_pack(self.path)['status'],'stale');self.assert_old_unchanged()
 def test_directory_additions_and_deletions_are_reported(self):
  (self.root/'facts/a.txt').unlink();(self.root/'facts/b.txt').write_text('replacement')
  r=self.refresh()
  self.assertEqual(r['changes'],[dict(section='facts',path='facts/a.txt',kind='deleted'),dict(section='facts',path='facts/b.txt',kind='added')])
  self.assert_old_unchanged()
 def test_missing_explicit_selection_is_an_error_not_scope_expansion(self):
  selected=packs.build_pack(root=self.root,facts=['facts/a.txt'],output=self.output,as_of='2026-10-19T00:00:00Z')
  (self.root/'facts/a.txt').unlink()
  with self.assertRaises(packs.SourceError):packs.refresh_pack(selected['pack_path'],output=self.next,as_of='2026-10-19T01:00:00Z')
  self.assertFalse(self.next.exists());self.assert_old_unchanged()
 def test_link_in_source_is_rejected_without_publication(self):
  outside=Path(self.temp.name)/'private.txt';outside.write_text('not selected')
  (self.root/'facts/link.txt').symlink_to(outside)
  with self.assertRaises(packs.SourceError):self.refresh()
  self.assertFalse(self.next.exists());self.assert_old_unchanged()
 def test_corrupt_old_pack_is_not_a_refreshable_source(self):
  payload=self.path/'prefix.txt';payload.chmod(0o600);payload.write_text('corrupt')
  with self.assertRaises(packs.PackError):self.refresh()
  self.assertFalse(self.next.exists())
 def test_invalid_as_of_is_rejected_even_when_unchanged(self):
  with self.assertRaises(packs.SourceError):packs.refresh_pack(self.path,output=self.next,as_of='not a time')
  self.assertFalse(self.next.exists());self.assert_old_unchanged()
 def test_cli_refresh_reports_new_identity(self):
  (self.root/'facts/a.txt').write_text('CLI update')
  r=subprocess.run([sys.executable,'-B','-m','branchwrite.context_pack','refresh',str(self.path),'--output',str(self.next),'--as-of','2026-10-19T01:00:00Z'],capture_output=True,text=True,timeout=10)
  self.assertEqual(r.returncode,0,r.stderr)
  result=json.loads(r.stdout);self.assertEqual(result['action'],'rebuilt');self.assertNotEqual(result['pack_id'],self.old['pack_id']);self.assert_old_unchanged()
