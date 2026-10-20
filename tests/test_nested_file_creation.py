import errno,hashlib,json,os,stat,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from branchwrite.execution import Executor,Grant,ToolRejected
from branchwrite.tool_registry import ToolRegistry,EffectIndeterminate

class NestedCreateTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.source=self.root/'source';self.source.mkdir();(self.source/'keep.txt').write_bytes(b'unchanged\n')
  self.executor=Executor.create(self.source,self.root/'world');self.path='literal data/deeper/hello.txt'
  self.payload="hello 'friend' $HOME\nnext: \u0394 e\u0301\n".encode('utf8')
  self.grant=Grant((),False,create_paths=(self.path,),read_paths=(self.path,))
  self.registry=ToolRegistry(self.executor,self.grant)
 def proposal(self,tool='create_file',**kw):
  return json.dumps(dict(tool=tool,arguments=kw or dict(path=self.path,content=self.payload.decode('utf8'))))
 def assert_untouched(self):
  self.assertEqual(list(self.executor.workspace.iterdir()),[self.executor.workspace/'keep.txt'])
  self.assertEqual((self.executor.workspace/'keep.txt').read_bytes(),b'unchanged\n')
 def test_missing_parent_plan_is_read_only(self):
  self.registry.freeze(self.proposal());self.assert_untouched()
 def test_exact_nested_create_then_actual_readback_and_no_overwrite(self):
  plan=self.registry.freeze(self.proposal());result=self.registry.execute(plan,'create-once')
  self.assertEqual(result.disposition,'created');self.assertEqual((self.executor.workspace/self.path).read_bytes(),self.payload)
  read=self.registry.execute(self.registry.freeze(self.proposal('read_file',path=self.path)),'read-real')
  self.assertEqual(read.stdout,self.payload);self.assertEqual(read.observation.sha256,hashlib.sha256(self.payload).hexdigest())
  with self.assertRaises(ToolRejected):self.registry.execute(plan,'no-overwrite')
  for rel in ['literal data','literal data/deeper']:
   self.assertEqual(stat.S_IMODE((self.executor.workspace/rel).stat().st_mode),0o700)
 def test_existing_parent_permissions_and_neighbor_are_preserved(self):
  d=self.executor.workspace/'literal data';d.mkdir(mode=0o750);(d/'neighbor').write_bytes(b'keep')
  self.registry.execute(self.registry.freeze(self.proposal()),'create-child')
  self.assertEqual(stat.S_IMODE(d.stat().st_mode),0o750);self.assertEqual((d/'neighbor').read_bytes(),b'keep')
 def test_other_leaf_denied_before_any_directory_creation(self):
  with self.assertRaises(ToolRejected):self.registry.freeze(self.proposal(path='other/deep/no.txt',content='no'))
  with self.assertRaises(ToolRejected):self.executor.create_file('denied',self.grant,'other/deep/no.txt',b'no')
  self.assert_untouched()
 def test_symlink_parent_cannot_escape_workspace(self):
  out=self.root/'outside';out.mkdir();(self.executor.workspace/'literal data').symlink_to(out,target_is_directory=True)
  with self.assertRaises(ToolRejected):self.registry.freeze(self.proposal())
  self.assertEqual(list(out.iterdir()),[])
 def test_regular_file_parent_rejected_without_new_paths(self):
  f=self.executor.workspace/'literal data';f.write_bytes(b'not a directory')
  with self.assertRaises(ToolRejected):self.registry.freeze(self.proposal())
  self.assertEqual(f.read_bytes(),b'not a directory')
 def test_parent_symlink_inserted_after_plan_is_rejected_before_act(self):
  plan=self.registry.freeze(self.proposal());out=self.root/'outside';out.mkdir();(self.executor.workspace/'literal data').symlink_to(out,target_is_directory=True)
  with self.assertRaises(ToolRejected):self.registry.execute(plan,'stale-parent')
  self.assertEqual(list(out.iterdir()),[])
 def test_read_missing_parent_never_creates_it(self):
  with self.assertRaises(ToolRejected):self.registry.freeze(self.proposal('read_file',path=self.path))
  self.assert_untouched()
 def test_link_failure_rolls_back_only_new_empty_directories(self):
  plan=self.registry.freeze(self.proposal())
  with patch('branchwrite.execution.os.link',side_effect=OSError(errno.ENOSPC,'test full filesystem')):
   with self.assertRaises(EffectIndeterminate):self.registry.execute(plan,'failed-link')
  self.assert_untouched()
 def test_lost_receipt_keeps_published_file_and_never_overwrites(self):
  plan=self.registry.freeze(self.proposal())
  with patch.object(self.executor,'_result',side_effect=OSError('test lost receipt')):
   with self.assertRaises(EffectIndeterminate):self.registry.execute(plan,'lost-receipt')
  self.assertEqual((self.executor.workspace/self.path).read_bytes(),self.payload)
  with self.assertRaises(ToolRejected):self.registry.execute(plan,'do-not-replay')
 def test_parent_flush_failure_rolls_back_new_empty_paths(self):
  plan=self.registry.freeze(self.proposal())
  with patch('branchwrite.execution.os.fsync',side_effect=OSError(errno.EIO,'test parent flush failure')):
   with self.assertRaises(EffectIndeterminate):self.registry.execute(plan,'parent-flush-failed')
  self.assert_untouched()
 def test_creation_depth_is_bounded_before_effects(self):
  path='/'.join(['d']*66+['leaf']);grant=Grant((),False,create_paths=(path,))
  with self.assertRaisesRegex(ToolRejected,'depth'):self.executor.create_file('deep-denied',grant,path,b'no')
  self.assert_untouched()

 def test_failed_nested_creates_do_not_leak_directory_descriptors(self):
  before=len(list(Path('/proc/self/fd').iterdir()))
  for i in range(16):
   plan=self.registry.freeze(self.proposal())
   with patch('branchwrite.execution.os.link',side_effect=OSError(errno.ENOSPC,'test full filesystem')):
    with self.assertRaises(EffectIndeterminate):self.registry.execute(plan,'failed-'+str(i))
   self.assert_untouched()
  self.assertEqual(len(list(Path('/proc/self/fd').iterdir())),before)

if __name__=='__main__':unittest.main()
