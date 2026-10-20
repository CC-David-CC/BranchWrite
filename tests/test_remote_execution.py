import json,os,tempfile,unittest
from pathlib import Path

class RemoteTargetTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.key=self.root/'key';self.key.write_bytes(b'opaque private fixture key');self.key.chmod(0o600)
  self.known=self.root/'known';self.known.write_bytes(b'opaque known host fixture');self.known.chmod(0o600)
 def target(self,**kw):
  from branchwrite.remote_execution import RemoteTarget
  args=dict(name='admin01',host='127.0.0.1',port=22220,user='maint',identity_file=self.key,known_hosts_file=self.known,timeout=30)
  args.update(kw);return RemoteTarget(**args)
 def test_target_requires_literal_host_exact_types_and_bounded_arguments(self):
  for kw in [dict(host='example.com'),dict(host='127.0.0.1; touch /tmp/bad'),dict(port=True),dict(port=0),dict(user='maint;bad'),dict(name='../other'),dict(timeout=float('nan')),dict(timeout=0)]:
   with self.subTest(kw=kw),self.assertRaises(ValueError):self.target(**kw)
 def test_keys_are_private_regular_files_and_changed_identity_is_rejected(self):
  target=self.target();self.key.write_bytes(b'changed')
  with self.assertRaises(ValueError):target.check()
  self.key.chmod(0o644)
  with self.assertRaises(ValueError):self.target()
  self.key.unlink();self.key.symlink_to(self.known)
  with self.assertRaises(ValueError):self.target()
 def test_ssh_argv_uses_fixed_destination_and_no_agent_or_host_config(self):
  target=self.target();args=target.argv('pass')
  self.assertIn('maint@127.0.0.1',args);self.assertIn('StrictHostKeyChecking=yes',args)
  self.assertIn('IdentityAgent=none',args);self.assertIn('IdentitiesOnly=yes',args)
  self.assertIn('ProxyCommand=none',args);self.assertEqual(args[args.index('-F')+1],'/dev/null')
  self.assertNotIn('opaque private fixture key',repr(args))
 def test_unacknowledged_intent_cannot_be_resent(self):
  from branchwrite.remote_execution import RemoteTransport,RemoteIndeterminate
  t=RemoteTransport(self.root/'jobs',self.target());intent=t.intent('op-one','a'*64,'true')
  t.record_intent(intent)
  with self.assertRaises(RemoteIndeterminate):t.run('op-one','a'*64,'true')
  with self.assertRaisesRegex(ValueError,'different'):t.run('op-one','a'*64,'false')
 def test_read_receipt_is_non_executing_and_checks_original_binding(self):
  from branchwrite.remote_execution import RemoteTransport,RemoteIndeterminate
  t=RemoteTransport(self.root/'jobs',self.target())
  with self.assertRaises(RemoteIndeterminate):t.read_receipt('op-one','a'*64,'true')
  self.assertEqual(list(t.root.iterdir()),[])

 def test_direct_intent_recording_rejects_path_escape_and_incompatible_target(self):
  from branchwrite.remote_execution import RemoteTransport
  t=RemoteTransport(self.root/'jobs',self.target());intent=t.intent('op-one','a'*64,'true')
  for field,value in [('operation_id','../escape'),('target_identity','b'*64),('unknown','field')]:
   bad=dict(intent);bad[field]=value
   with self.subTest(field=field),self.assertRaises(ValueError):t.record_intent(bad)
  self.assertFalse((self.root/'escape').exists())
 def test_reply_validation_rejects_bool_exit_wrong_hash_and_wrong_process_identity(self):
  import base64,hashlib
  from branchwrite.remote_execution import RemoteTransport
  t=RemoteTransport(self.root/'jobs',self.target());intent=t.intent('op-one','a'*64,'true')
  reply=dict(schema=1,operation_id='op-one',request_sha256=hashlib.sha256(t._request(intent)).hexdigest(),disposition='exited',exit_code=0,stdout_b64='',stderr_b64='',elapsed_seconds=.1,command_pid=10,worker_pid=9)
  self.assertEqual(t._decode(intent,reply).exit_code,0)
  for field,value in [('exit_code',True),('request_sha256','b'*64),('worker_pid',None),('command_pid',None),('elapsed_seconds',float('nan'))]:
   with self.subTest(field=field),self.assertRaises(ValueError):t._decode(intent,{**reply,field:value})

 def test_resource_identity_is_shared_across_aliases_users_and_timeout(self):
  import dataclasses
  target=self.target()
  changed=dataclasses.replace(target,name='second-alias',user='other',timeout=2)
  self.assertEqual(target.resource_identity,changed.resource_identity)
  self.assertNotEqual(target.identity,changed.identity)
  self.assertNotEqual(target.resource_identity,dataclasses.replace(target,port=22221).resource_identity)

 def test_shared_app_container_can_be755_but_target_ownership_is_private(self):
  from unittest.mock import patch
  from branchwrite.remote_execution import RemoteTransport
  home=self.root/'home';base=home/'.local/state/branchwrite';base.mkdir(parents=True,mode=0o755)
  t=RemoteTransport(self.root/'jobs',self.target())
  with patch('pathlib.Path.home',return_value=home):owner=t._ownership()
  self.assertEqual(owner.root.stat().st_mode&0o777,0o700)
  self.assertEqual(base.stat().st_mode&0o777,0o755)

 def test_corrupt_retained_outcome_is_indeterminate_not_a_preexecution_rejection(self):
  from branchwrite.remote_execution import RemoteTransport,RemoteIndeterminate,_write
  t=RemoteTransport(self.root/'jobs',self.target());intent=t.intent('op-one','a'*64,'true');t.record_intent(intent)
  _write(t.root/'op-one/receipt.json',{'schema':1,'corrupt':True})
  with self.assertRaises(RemoteIndeterminate):t.read_receipt('op-one','a'*64,'true')

 def test_stdin_payload_is_bound_to_original_receipt_and_cannot_be_changed(self):
  from branchwrite.remote_execution import RemoteTransport
  t=RemoteTransport(self.root/'jobs',self.target())
  a=t.intent('payload-op','a'*64,'cat',stdin=b'one\x00two')
  self.assertNotEqual(t._request(a),t._request(t.intent('payload-op','a'*64,'cat',stdin=b'different')))
  self.assertTrue(t.record_intent(a))
  with self.assertRaises(ValueError):t.record_intent(t.intent('payload-op','a'*64,'cat',stdin=b'changed'))
  for value in ['not bytes',b'x'*(4*1024*1024+1)]:
   with self.assertRaises(ValueError):t.intent('large','a'*64,'cat',stdin=value)
