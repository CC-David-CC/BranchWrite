import hashlib,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from branchwrite.remote_execution import _json,_write,_private,RemoteIndeterminate

class RemoteOwnershipTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name);self.resource='a'*64
 def owner(self):
  from branchwrite.remote_ownership import TargetOwnership
  return TargetOwnership(self.root/'leases',self.resource)
 def test_real_process_lock_prevents_overlap_and_releases_on_exit(self):
  from branchwrite.remote_ownership import RemoteTargetBusy
  owner=self.owner()
  with owner.hold():
   command='from branchwrite.remote_ownership import TargetOwnership,RemoteTargetBusy; import sys; o=TargetOwnership(sys.argv[1],sys.argv[2]);\ntry:\n with o.hold(): raise AssertionError("overlap")\nexcept RemoteTargetBusy: print("busy")'
   env={**os.environ,'PYTHONPATH':str(Path(__file__).resolve().parents[1])}
   f=subprocess.run([sys.executable,'-c',command,str(owner.root),self.resource],env=env,capture_output=True,text=True,timeout=5)
   self.assertEqual(f.returncode,0,f.stderr);self.assertEqual(f.stdout.strip(),'busy')
  with self.owner().hold():pass
 def test_pending_reservation_survives_owner_close_and_new_ids_cannot_bypass(self):
  owner=self.owner();folder=self.root/'old-operation';folder.mkdir(mode=0o700)
  intent=dict(operation_id='original',plan_sha256='b'*64);_write(folder/'intent.json',intent)
  with owner.hold() as held:held.reserve(folder/'intent.json',intent)
  with self.owner().hold() as held:
   with self.assertRaises(RemoteIndeterminate):held.check_available(lambda *args:None)
  self.assertTrue(owner.marker.exists())
 def test_only_matching_validated_durable_receipt_clears_reservation(self):
  owner=self.owner();folder=self.root/'old-operation';folder.mkdir(mode=0o700);intent=dict(operation_id='original',plan_sha256='b'*64);_write(folder/'intent.json',intent)
  with owner.hold() as held:held.reserve(folder/'intent.json',intent)
  with owner.hold() as held:
   def receipt(path,original):
    self.assertEqual(path,folder);self.assertEqual(original,intent);return True
   held.check_available(receipt)
  self.assertFalse(owner.marker.exists())
 def test_altered_or_missing_prior_intent_keeps_target_blocked(self):
  owner=self.owner();folder=self.root/'old-operation';folder.mkdir(mode=0o700);intent=dict(operation_id='original',plan_sha256='b'*64);_write(folder/'intent.json',intent)
  with owner.hold() as held:held.reserve(folder/'intent.json',intent)
  _write(folder/'intent.json',{**intent,'plan_sha256':'c'*64})
  with owner.hold() as held:
   with self.assertRaises(RemoteIndeterminate):held.check_available(lambda *args:True)
  self.assertTrue(owner.marker.exists())
 def test_reserve_cannot_overwrite_pending_work_and_requires_durable_exact_intent(self):
  owner=self.owner();folder=self.root/'old-operation';folder.mkdir(mode=0o700);intent=dict(operation_id='original',plan_sha256='b'*64);_write(folder/'intent.json',intent)
  with owner.hold() as held:
   with self.assertRaises(ValueError):held.reserve(folder/'intent.json',{**intent,'plan_sha256':'c'*64})
   held.reserve(folder/'intent.json',intent)
   with self.assertRaises(RemoteIndeterminate):held.reserve(folder/'intent.json',intent)
 def test_unlink_is_not_an_implicit_successful_release(self):
  owner=self.owner();folder=self.root/'old-operation';folder.mkdir(mode=0o700);intent=dict(operation_id='original',plan_sha256='b'*64);_write(folder/'intent.json',intent)
  with owner.hold() as held:
   held.reserve(folder/'intent.json',intent)
   with self.assertRaises(RemoteIndeterminate):held.complete(lambda *args:None)
  self.assertTrue(owner.marker.exists())

 def test_foreign_thread_and_closed_lease_cannot_change_ownership(self):
  import threading
  owner=self.owner();errors=[]
  with owner.hold() as held:
   def foreign():
    try:held.check_available(lambda *args:True)
    except Exception as e:errors.append(e)
   worker=threading.Thread(target=foreign);worker.start();worker.join()
   self.assertEqual(len(errors),1);self.assertIsInstance(errors[0],ValueError)
   held.check_available(lambda *args:True)
  with self.assertRaises(ValueError):held.check_available(lambda *args:True)

 def test_only_validated_settlement_updates_latest_call_and_pending_work_hides_it(self):
  owner=self.owner();folder=self.root/'old-operation';folder.mkdir(mode=0o700);intent=dict(operation_id='original',plan_sha256='b'*64);_write(folder/'intent.json',intent)
  self.assertIsNone(owner.latest_intent())
  with owner.hold() as held:held.reserve(folder/'intent.json',intent)
  with self.assertRaises(RemoteIndeterminate):owner.latest_intent()
  with owner.hold() as held:held.complete(lambda *args:True)
  self.assertEqual(owner.latest_intent(),hashlib.sha256(_json(intent)).hexdigest())
