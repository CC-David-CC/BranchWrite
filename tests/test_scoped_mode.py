"""Real permission changes remain grant-bound,observed and content-preserving."""
from pathlib import Path
import hashlib,json,os,stat,tempfile,unittest
from branchwrite.execution import Executor,Grant,ToolRejected
from branchwrite.tool_registry import ToolRegistry

class ScopedModeTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name);src=self.root/'source';src.mkdir()
  self.body=b'#!/bin/sh\nprintf "owner-only\\n"\n'.replace(b'\\n',b'\n')
  (src/'task.sh').write_bytes(self.body);(src/'task.sh').chmod(0o640)
  self.executor=Executor.create(src,self.root/'run')
  self.target=self.executor.workspace/'task.sh'
  self.sha=hashlib.sha256(self.body).hexdigest()
 def grant(self):return Grant((),False,read_paths=('task.sh',),mode_paths=('task.sh',),mode_mask=0o100)
 def test_real_bit_change_preserves_bytes_and_other_mode_bits(self):
  result=self.executor.set_mode('mode-1',self.grant(),'task.sh',self.sha,'0740')
  self.assertEqual(result.exit_code,0);self.assertEqual(self.target.read_bytes(),self.body)
  self.assertEqual(stat.S_IMODE(self.target.stat().st_mode),0o740)
  self.assertEqual(json.loads(result.stdout.read_bytes())['before_mode'],'0640')
  self.assertEqual((self.executor.source/'task.sh').stat().st_mode&0o777,0o640)
 def test_reject_ungranted_bits_paths_stale_bytes_and_special_modes(self):
  for grant,path,sha,mode in [(Grant((),False),'task.sh',self.sha,'0740'),
   (self.grant(),'task.sh',self.sha,'0750'),(self.grant(),'task.sh','0'*64,'0740'),
   (self.grant(),'../task.sh',self.sha,'0740'),(self.grant(),'task.sh',self.sha,'4740'),
   (self.grant(),'task.sh',self.sha,'740'),(self.grant(),'task.sh',self.sha,True)]:
   with self.subTest(mode=mode,path=path),self.assertRaises(ToolRejected):
    self.executor.set_mode('denied',grant,path,sha,mode)
   self.assertEqual(self.target.stat().st_mode&0o777,0o640)
 def test_symlink_and_hardlink_rejected_without_changing_outside_file(self):
  other=self.root/'outside';other.write_bytes(self.body);other.chmod(0o640)
  self.target.unlink();self.target.symlink_to(other)
  with self.assertRaises(ToolRejected):self.executor.set_mode('link',self.grant(),'task.sh',self.sha,'0740')
  self.target.unlink();os.link(other,self.target)
  with self.assertRaises(ToolRejected):self.executor.set_mode('hardlink',self.grant(),'task.sh',self.sha,'0740')
  self.assertEqual(other.stat().st_mode&0o777,0o640)
 def test_registry_requires_read_and_rejects_plan_after_mode_change(self):
  reg=ToolRegistry(self.executor,self.grant())
  proposal=json.dumps(dict(tool='set_mode',arguments=dict(path='task.sh',mode='0740')))
  with self.assertRaises(ToolRejected):reg.freeze(proposal)
  read=reg.execute(reg.freeze(json.dumps(dict(tool='read_file',arguments=dict(path='task.sh')))),'read')
  plan=reg.freeze(proposal,observations=(read.observation,))
  self.target.chmod(0o600)
  with self.assertRaises(ToolRejected):reg.execute(plan,'stale-mode')
  self.assertEqual(self.target.stat().st_mode&0o777,0o600)
 def test_registry_dispatch_and_grammar_expose_only_explicit_capability(self):
  self.assertNotIn('"set_mode"',json.dumps(ToolRegistry(self.executor,Grant((),False)).model_schema()))
  reg=ToolRegistry(self.executor,self.grant())
  self.assertIn('set_mode',reg.model_gbnf())
  read=reg.execute(reg.freeze(json.dumps(dict(tool='read_file',arguments=dict(path='task.sh')))),'read')
  out=reg.execute(reg.freeze(json.dumps(dict(tool='set_mode',arguments=dict(path='task.sh',mode='0740'))),observations=(read.observation,)),'mode')
  self.assertEqual(out.exit_code,0);self.assertEqual(out.observation.sha256,self.sha)
 def test_invalid_grants_rejected_before_tools(self):
  for kwargs in [dict(mode_mask=True),dict(mode_mask=0o10000),dict(mode_mask=0),
                 dict(mode_paths=('task.sh','task.sh'),mode_mask=0o100)]:
   defaults=dict(mode_paths=('task.sh',));defaults.update(kwargs)
   with self.subTest(kwargs=kwargs),self.assertRaises(ToolRejected):
    Grant((),False,read_paths=('task.sh',),**defaults)

class ModeCliAndFailureTests(unittest.TestCase):
 setUp=ScopedModeTests.setUp
 grant=ScopedModeTests.grant
 def test_cli_admits_and_binds_mode_grant(self):
  from branchwrite.run_cli import _config
  c=dict(schema=1,source=str(self.executor.source),run_id='mode-cli',
   grant=dict(edit_paths=[],read_paths=['task.sh'],create_paths=[],allow_tests=False,
              mode_paths=['task.sh'],mode_mask=0o100),bindings={})
  self.assertEqual(_config(json.dumps(c))['grant']['mode_mask'],0o100)
  for value in [True,512,-1,'0100']:
   c['grant']['mode_mask']=value
   with self.subTest(value=value),self.assertRaises((ToolRejected,ValueError)):
    _config(json.dumps(c))
 def test_mode_change_without_content_edit_grant_and_removing_read_access(self):
  grant=Grant((),False,read_paths=('task.sh',),mode_paths=('task.sh',),mode_mask=0o400)
  reg=ToolRegistry(self.executor,grant)
  read=reg.execute(reg.freeze(json.dumps(dict(tool='read_file',arguments=dict(path='task.sh')))),'read')
  out=reg.execute(reg.freeze(json.dumps(dict(tool='set_mode',arguments=dict(path='task.sh',mode='0240'))),observations=(read.observation,)),'write')
  self.assertEqual(out.observation.sha256,self.sha)
  self.assertEqual(self.target.stat().st_mode&0o777,0o240)
  # Restore only this test-owned file so TemporaryDirectory can clean it.
  self.target.chmod(0o640)
 def test_failed_receipt_publication_is_indeterminate_after_real_chmod(self):
  from unittest.mock import patch
  from branchwrite.tool_registry import EffectIndeterminate
  reg=ToolRegistry(self.executor,self.grant())
  read=reg.execute(reg.freeze(json.dumps(dict(tool='read_file',arguments=dict(path='task.sh')))),'read')
  plan=reg.freeze(json.dumps(dict(tool='set_mode',arguments=dict(path='task.sh',mode='0740'))),observations=(read.observation,))
  with patch.object(self.executor,'_result',side_effect=OSError('receipt write failure')):
   with self.assertRaises(EffectIndeterminate):reg.execute(plan,'ambiguous')
  self.assertEqual(self.target.stat().st_mode&0o777,0o740)
  self.assertEqual(self.target.read_bytes(),self.body)

class ModeReadbackPolicyTests(unittest.TestCase):
 setUp=ScopedModeTests.setUp
 grant=ScopedModeTests.grant
 def test_unchanged_bytes_do_not_qualify_missing_execute_bit(self):
  from branchwrite.verification import FileReadbackPolicy
  from branchwrite.records import RuntimeLog
  reg=ToolRegistry(self.executor,self.grant())
  policy=FileReadbackPolicy.admit(dict(schema=1,files=[dict(path='task.sh',sha256=self.sha,mode='0740')]),reg)
  with RuntimeLog(self.root/'ledger') as log:
   read=reg.execute(reg.freeze(json.dumps(dict(tool='read_file',arguments=dict(path='task.sh')))),'read')
   val,_=read.publish(log);outcomes=[(dict(id='read'),val)]
   self.assertEqual(policy.verify(reg,log,outcomes)['status'],'fail')
   reg.execute(reg.freeze(json.dumps(dict(tool='set_mode',arguments=dict(path='task.sh',mode='0740'))),observations=(read.observation,)),'mode')
   self.assertEqual(policy.verify(reg,log,outcomes)['status'],'pass')
 def test_mode_requirement_changes_identity_and_rejects_special_bits(self):
  from branchwrite.verification import FileReadbackPolicy
  reg=ToolRegistry(self.executor,self.grant())
  legacy=FileReadbackPolicy.admit(dict(schema=1,files=[dict(path='task.sh',sha256=self.sha)]),reg)
  mode=FileReadbackPolicy.admit(dict(schema=1,files=[dict(path='task.sh',sha256=self.sha,mode='0740')]),reg)
  self.assertNotEqual(legacy.identity,mode.identity)
  for value in [True,'4740','740',0o740]:
   with self.subTest(value=value),self.assertRaises(ValueError):
    FileReadbackPolicy.admit(dict(schema=1,files=[dict(path='task.sh',sha256=self.sha,mode=value)]),reg)
if __name__=='__main__':unittest.main()
