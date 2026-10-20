"""Derived catalog publication must preserve existing files and reject aliases."""
import json,os,tempfile,unittest
from pathlib import Path
from branchwrite.base_cli import _publish
class BaseCatalogPublicationTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
 def test_identical_publication_keeps_same_file_and_changed_value_fails(self):
  _publish(self.root,'base-catalog.json',[{'id':'one'}]);p=self.root/'base-catalog.json';before=(p.stat().st_ino,p.stat().st_mtime_ns,p.read_bytes())
  _publish(self.root,'base-catalog.json',[{'id':'one'}]);self.assertEqual((p.stat().st_ino,p.stat().st_mtime_ns,p.read_bytes()),before)
  with self.assertRaises(ValueError):_publish(self.root,'base-catalog.json',[{'id':'two'}])
  self.assertEqual(p.read_bytes(),before[2]);self.assertEqual(p.stat().st_mode & 0o777,0o600)
 def test_symlink_target_is_not_read_or_overwritten(self):
  target=self.root/'protected';target.write_bytes(b'preserve');(self.root/'base-catalog.json').symlink_to(target)
  with self.assertRaises(OSError):_publish(self.root,'base-catalog.json',[])
  self.assertEqual(target.read_bytes(),b'preserve')
 def test_hardlinked_catalog_is_rejected(self):
  _publish(self.root,'base-catalog.json',[]);os.link(self.root/'base-catalog.json',self.root/'alias')
  with self.assertRaises(ValueError):_publish(self.root,'base-catalog.json',[])
 def test_oversize_publication_creates_no_catalog(self):
  with self.assertRaises(ValueError):_publish(self.root,'base-catalog.json',{'text':'x'*(1024*1024)})
  self.assertFalse((self.root/'base-catalog.json').exists())
