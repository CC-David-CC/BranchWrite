import json,socket,tempfile,unittest
from pathlib import Path

class RemoteConfigTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.spec={'admin01':dict(host='127.0.0.1',port=22220,user='maint',identity_file='/operator/key',known_hosts_file='/operator/hosts',timeout=30,owner_hostname=socket.gethostname())}
 def test_validation_is_data_only_and_rejects_unknown_fields_and_bad_types(self):
  from branchwrite.remote_config import validate_targets
  self.assertEqual(validate_targets(self.spec),self.spec)
  for key,value in [('extra','not allowed'),('port',True),('identity_file','relative'),('timeout',float('inf'))]:
   wrong={'admin01':{**self.spec['admin01'],key:value}}
   with self.subTest(key=key),self.assertRaises(ValueError):validate_targets(wrong)
 def test_operator_file_is_private_and_wrong_client_cannot_load_capability(self):
  from branchwrite.remote_config import load_file,load_targets
  p=self.root/'targets.json';p.write_text(json.dumps(dict(schema=1,targets=self.spec)));p.chmod(0o644)
  with self.assertRaises(ValueError):load_file(p)
  p.chmod(0o600);self.assertEqual(load_file(p),self.spec)
  wrong={'admin01':{**self.spec['admin01'],'owner_hostname':'different-client'}}
  with self.assertRaisesRegex(ValueError,'client'):load_targets(wrong)
 def test_coding_launch_grants_remotes_only_in_work_mode_and_pins_them(self):
  from branchwrite.coding_cli import build_launch,save_launch,read_launch
  project=self.root/'project';project.mkdir();connection=dict(endpoint_url='http://127.0.0.1:1',endpoint_pin='owned',model_contract_id='model',execution_profile_id='profile',eos_tokens=[256])
  work=build_launch(project,'Prepare the test web machine.',connection,branch='work',project_files=True,remotes=self.spec)
  self.assertEqual(work['config']['grant']['remote_targets'],['admin01']);self.assertEqual(work['config']['remotes'],self.spec)
  state=self.root/'state';state.mkdir(mode=0o700);save_launch(state,work);self.assertEqual(read_launch(state),work)
  for mode in ['plan','chat','aside']:
   launch=build_launch(project,'Discuss the test machine.',connection,branch=mode,project_files=True,mode=mode,remotes=self.spec)
   self.assertNotIn('remotes',launch['config']);self.assertFalse(launch['config']['grant'].get('remote_targets'))
