import hashlib,json,os,tempfile,unittest
from pathlib import Path

class RemoteUploadTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.home=Path(self.tmp.name)
 def store(self,body=b'hello\n',name='index.html'):
  from branchwrite.remote_upload import store
  return store(self.home,name,hashlib.sha256(body).hexdigest(),body)
 def test_exact_bytes_unicode_name_and_content_addressed_path(self):
  body=b'\x00binary\xff\r\n'+bytes(range(256));v=self.store(body,'caf\u00e9 $HOME.html')
  p=Path(v['remote_path']);self.assertEqual(p.read_bytes(),body)
  self.assertEqual(v['sha256'],hashlib.sha256(body).hexdigest());self.assertEqual(v['bytes'],len(body))
  self.assertEqual(p.parent.name,v['sha256']);self.assertEqual(p.name,'caf\u00e9 $HOME.html')
  self.assertEqual(p.stat().st_mode&0o777,0o400)
 def test_same_bytes_reuse_without_replacing_published_inode(self):
  a=self.store();p=Path(a['remote_path']);inode=p.stat().st_ino;b=self.store()
  self.assertEqual(a,b);self.assertEqual(p.stat().st_ino,inode)
 def test_bad_hash_and_bad_name_do_not_publish(self):
  from branchwrite.remote_upload import store
  for name in ['../escape','/tmp/escape','.','a/b','a\x00b']:
   with self.subTest(name=name),self.assertRaises(ValueError):store(self.home,name,'0'*64,b'hello')
  with self.assertRaises(ValueError):store(self.home,'index.html','0'*64,b'hello')
  self.assertEqual(list(self.home.iterdir()),[])
 def test_symlinked_parent_or_file_is_rejected_without_following(self):
  other=self.home/'other';other.mkdir();(self.home/'.branchwrite-uploads').symlink_to(other,target_is_directory=True)
  with self.assertRaises((ValueError,OSError)):self.store()
  self.assertEqual(list(other.iterdir()),[])
  (self.home/'.branchwrite-uploads').unlink();v=self.store();p=Path(v['remote_path']);p.unlink();outside=self.home/'outside';outside.write_bytes(b'untouched');p.symlink_to(outside)
  with self.assertRaises((ValueError,OSError)):self.store()
  self.assertEqual(outside.read_bytes(),b'untouched')
 def test_corrupt_or_hardlinked_blob_is_not_silently_replaced(self):
  v=self.store();p=Path(v['remote_path']);p.chmod(0o600);p.write_bytes(b'corrupt')
  with self.assertRaises((ValueError,OSError)):self.store()
  self.assertEqual(p.read_bytes(),b'corrupt')
  p.unlink();v=self.store();p=Path(v['remote_path']);os.link(p,self.home/'alias')
  with self.assertRaises((ValueError,OSError)):self.store()
 def test_payload_bound_is_enforced_before_creating_directories(self):
  from branchwrite.remote_upload import store,MAX_UPLOAD
  body=b'x'*(MAX_UPLOAD+1)
  with self.assertRaises(ValueError):store(self.home,'index',hashlib.sha256(body).hexdigest(),body)
  self.assertEqual(list(self.home.iterdir()),[])

 def test_group_writable_common_share_is_not_used_or_changed(self):
  shared=self.home/'.local/share';shared.mkdir(parents=True);shared.chmod(0o775)
  v=self.store();self.assertEqual(Path(v['remote_path']).parts[-3],'.branchwrite-uploads')
  self.assertEqual(shared.stat().st_mode&0o777,0o775);self.assertEqual(list(shared.iterdir()),[])
