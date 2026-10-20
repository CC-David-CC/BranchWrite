import json,tempfile,unittest
from pathlib import Path
from branchwrite.execution import Executor,Grant,ToolRejected
from branchwrite.tool_registry import ToolRegistry
from branchwrite.remote_execution import RemoteTarget
from branchwrite.records import decode

class RemoteToolTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  source=self.root/'source';source.mkdir();self.executor=Executor.create(source,self.root/'world')
  self.key=self.root/'key';self.key.write_text('opaque fixture private key');self.key.chmod(0o600)
  self.known=self.root/'known';self.known.write_text('opaque known-host fixture');self.known.chmod(0o600)
  self.target=RemoteTarget('admin01','127.0.0.1',22220,'maint',self.key,self.known,30)
 def registry(self):return ToolRegistry(self.executor,Grant((),False,remote_targets=('admin01',)),remote_targets=(self.target,))
 def test_remote_configuration_does_not_implicitly_grant_authority(self):
  registry=ToolRegistry(self.executor,Grant((),False),remote_targets=(self.target,))
  self.assertNotIn('remote_command',registry._definitions)
  with self.assertRaises(ToolRejected):registry.parse(json.dumps(dict(tool='remote_command',arguments=dict(target='admin01',command='true'))))
 def test_missing_granted_target_fails_before_inference_or_execution(self):
  with self.assertRaises(ToolRejected):ToolRegistry(self.executor,Grant((),False,remote_targets=('admin01',)))
 def test_one_definition_table_exposes_target_alias_but_no_credentials(self):
  registry=self.registry();schema=json.dumps(registry.model_schema());grammar=registry.model_gbnf()
  self.assertIn('remote_command',schema);self.assertIn('check_remote',schema)
  self.assertIn('admin01',schema);self.assertIn('admin01',grammar)
  for private in [str(self.key),str(self.known),'127.0.0.1','opaque fixture private key']:self.assertNotIn(private,schema)
  self.assertEqual(registry.operation_kind('remote_command'),'ACT');self.assertEqual(registry.operation_kind('check_remote'),'ACT')
 def test_frozen_remote_plan_binds_registry_target_and_exact_command(self):
  registry=self.registry();command="printf '%s\\n' '$HOME caf\u00e9'"
  plan=registry.freeze(json.dumps(dict(tool='remote_command',arguments=dict(target='admin01',command=command))))
  row=decode(plan.data);self.assertEqual(row[:4],('bw.tool-plan.v2',registry.identity,registry.world,'remote_command'));self.assertEqual(row[4]['command'],command)
  self.key.write_text('changed key')
  with self.assertRaises(ToolRejected):registry.freeze(json.dumps(dict(tool='remote_command',arguments=dict(target='admin01',command=command))))
 def test_ungranted_target_bad_type_and_oversize_command_are_rejected(self):
  registry=self.registry()
  for args in [dict(target='other',command='true'),dict(target='admin01',command=True),dict(target='admin01',command=''),dict(target='admin01',command='x'*16385),dict(target='admin01',command='\0')]:
   with self.subTest(args=str(args)[:80]),self.assertRaises(ToolRejected):registry.parse(json.dumps(dict(tool='remote_command',arguments=args)))
 def test_reconciliation_does_not_dispatch_an_unknown_effect(self):
  from branchwrite.tool_registry import EffectIndeterminate
  registry=self.registry();plan=registry.freeze(json.dumps(dict(tool='remote_command',arguments=dict(target='admin01',command='true'))))
  with self.assertRaises(EffectIndeterminate):registry.reconcile(plan,'unknown-operation')

 def test_receipt_conversion_failure_after_remote_return_is_not_preexecution_rejection(self):
  from unittest.mock import patch
  from branchwrite.tool_registry import EffectIndeterminate
  registry=self.registry();plan=registry.freeze(json.dumps(dict(tool='remote_command',arguments=dict(target='admin01',command='true'))))
  # CPU fault at the host return boundary, not GPU/SSH acceptance evidence.
  with patch.object(registry,'_remote_transport') as transport,patch.object(registry,'_remote_outcome',side_effect=ValueError('receipt conversion failed')):
   transport.return_value.run.return_value=object()
   with self.assertRaises(EffectIndeterminate):registry.execute(plan,'original-operation')

 def test_identical_helper_bytes_in_another_install_location_keep_definition_identity(self):
  from unittest.mock import patch
  from branchwrite import remote_execution,remote_guest,remote_ownership
  from contextlib import ExitStack
  first=self.registry();other=self.root/'another-install';other.mkdir()
  with ExitStack() as stack:
   for module in [remote_execution,remote_guest,remote_ownership]:
    original=Path(module.__file__);copy=other/original.name;copy.write_bytes(original.read_bytes())
    stack.enter_context(patch.object(module,'__file__',str(copy)))
   second=self.registry()
   self.assertEqual(first.identity,second.identity)

 def test_pending_kernel_remote_call_settles_original_receipt_without_execute(self):
  from unittest.mock import patch
  from branchwrite.records import RuntimeLog
  from branchwrite.kernel import FrameKernel,ResultContract
  from branchwrite.tool_registry import EffectIndeterminate,ToolOutcome
  from branchwrite.tool_dispatch import admit_tool,dispatch_tool
  registry=self.registry()
  with RuntimeLog(self.root/'ledger') as log:
   kernel=FrameKernel(log);definition=log.put_artifact(b'FLOW remote\nEND\n');inputs=log.put_artifact(b'task')
   kernel.create_root('root','attempt',definition,inputs,ResultContract('AgentResult','record'))
   admit_tool(kernel,registry,'root',expected_epoch=0,child_id='remote-call',attempt_id='remote-attempt',slot='outcome',next_pc=1,proposal=json.dumps(dict(tool='remote_command',arguments=dict(target='admin01',command='true'))))
   with patch.object(registry,'execute',side_effect=EffectIndeterminate('unknown','a'*64)):
    with self.assertRaises(EffectIndeterminate):dispatch_tool(kernel,registry,'remote-call')
   frame=kernel.frame('remote-call');original=frame['dispatch'][0]
   known=ToolOutcome('exited',0,.1,b'known returned bytes',b'',original,frame['inputs'][0],'remote_command')
   with patch.object(registry,'execute',side_effect=AssertionError('must not execute again')),patch.object(registry,'reconcile',return_value=known) as recovered:
    value=dispatch_tool(kernel,registry,'remote-call')
    self.assertEqual(value['operation_id'],original);self.assertEqual(kernel.frame('remote-call')['state'],'Closed');recovered.assert_called_once()

 def test_upload_requires_read_grant_and_freezes_exact_file_revision(self):
  registry=self.registry();self.assertNotIn('upload_file',registry._definitions)
  (self.executor.workspace/'index.html').write_bytes(b'original')
  registry=ToolRegistry(self.executor,Grant((),False,read_paths=('index.html',),remote_targets=('admin01',)),remote_targets=(self.target,))
  plan=registry.freeze(json.dumps(dict(tool='upload_file',arguments=dict(target='admin01',path='index.html'))))
  self.assertEqual(decode(plan.data)[5][0][1],__import__('hashlib').sha256(b'original').hexdigest())
  self.assertIn('upload_file',json.dumps(registry.model_schema()));self.assertIn('upload_file',registry.model_gbnf())
  (self.executor.workspace/'index.html').write_bytes(b'changed')
  with self.assertRaisesRegex(ToolRejected,'stale'):registry.execute(plan,'stale-upload')
 def test_upload_local_file_must_remain_inside_granted_scope(self):
  registry=ToolRegistry(self.executor,Grant((),False,read_paths=('index.html',),remote_targets=('admin01',)),remote_targets=(self.target,))
  for path in ['../escape','/etc/passwd','secret.key']:
   with self.subTest(path=path),self.assertRaises(ToolRejected):registry.freeze(json.dumps(dict(tool='upload_file',arguments=dict(target='admin01',path=path))))
