"""Read-only run status uses the canonical kernel, never a second state store."""
import contextlib,hashlib,io,json,tempfile,unittest
from pathlib import Path
from branchwrite.__main__ import main
from branchwrite.records import RuntimeLog,encode
from branchwrite.kernel import FrameKernel,ResultContract,CallSpec

class CodingStatusTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.state=Path(self.tmp.name)/'state';self.ledger=self.state/'ledger'
 def make(self,closed=False):
  with RuntimeLog(self.ledger) as log:
   k=FrameKernel(log);definition=log.put_artifact(b'canonical program')
   inputs=log.put_artifact(encode({'schema':1,'bindings':{}}))
   k.create_root('program','attempt',definition,inputs,ResultContract('ProgramResult','record'))
   if closed:k.finish('program',{'schema':1,'verified':True,'bindings':{}})
 def snapshot(self):
  return {str(p.relative_to(self.state)):hashlib.sha256(p.read_bytes()).hexdigest() for p in self.state.rglob('*') if p.is_file()}
 def invoke(self,*extra):
  out=io.StringIO();err=io.StringIO()
  with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
   try:code=main(['status',str(self.state),*extra])
   except SystemExit as exc:code=exc.code
  return code,out.getvalue(),err.getvalue()
 def test_closed_result_is_recorded_not_claimed_reverified(self):
  self.make(True);before=self.snapshot();code,out,err=self.invoke('--json')
  self.assertEqual(code,0,err);r=json.loads(out)
  self.assertEqual(r['state'],'Closed');self.assertIs(r['recorded_verified'],True)
  self.assertIs(r['workspace_rechecked'],False);self.assertEqual(r['events'],2)
  self.assertEqual(self.snapshot(),before)
 def test_incomplete_run_does_not_claim_success(self):
  self.make();code,out,err=self.invoke('--json');self.assertEqual(code,0,err)
  r=json.loads(out);self.assertEqual(r['state'],'Ready');self.assertIsNone(r['recorded_verified'])
 def test_unsettled_operation_is_visible(self):
  self.make()
  with RuntimeLog(self.ledger) as log:
   k=FrameKernel(log);a=log.put_artifact(b'def');i=log.put_artifact(encode({}))
   k.spawn('program',expected_epoch=0,calls=(CallSpec('child','attempt2','slot','ACT',a,i,ResultContract('ToolOutcome','record')),),next_pc=1)
   k.dispatch('child','owned-op',i)
  code,out,err=self.invoke('--json');self.assertEqual(code,0,err)
  self.assertEqual(json.loads(out)['pending_operations'],[{'frame':'child','operation_id':'owned-op','state':'Waiting'}])
 def test_missing_state_is_not_created(self):
  code,out,err=self.invoke('--json');self.assertEqual(code,2);self.assertFalse(self.state.exists())
 def test_active_writer_is_reported_without_ledger_read(self):
  self.make();before=self.snapshot()
  with RuntimeLog(self.ledger):
   code,out,err=self.invoke('--json');self.assertEqual(code,2);self.assertIn('busy',err.lower())
  self.assertEqual(self.snapshot(),before)
 def test_corrupt_log_is_not_repaired(self):
  self.make();f=self.ledger/'events.bwl';f.write_bytes(f.read_bytes()+b'torn')
  before=self.snapshot();code,out,err=self.invoke('--json');self.assertEqual(code,2)
  self.assertEqual(self.snapshot(),before)
 def test_human_output_labels_verification_scope(self):
  self.make(True);code,out,err=self.invoke()
  self.assertEqual(code,0,err);self.assertIn('Closed',out);self.assertIn('recorded',out.lower())
  self.assertIn('not rechecked',out.lower())

 def native_pending(self):
  self.make()
  with RuntimeLog(self.ledger) as log:
   k=FrameKernel(log);a=log.put_artifact(b'model');i=log.put_artifact(encode({}))
   k.spawn('program',expected_epoch=0,calls=(CallSpec('model','model-attempt','proposal','FLOW',a,i,ResultContract('ModelOutput','record')),),next_pc=1)
   k.spawn('model',expected_epoch=0,calls=(CallSpec('native','native-attempt','native','EXPAND',a,i,ResultContract('COWNativeReceipt','record')),),next_pc=1)
   k.dispatch('native','owned-model-op',i)
 def test_pending_model_status_supplies_exact_recovery_argv_without_execution(self):
  self.native_pending();before=self.snapshot();code,out,err=self.invoke('--json');self.assertEqual(code,0,err)
  rows=json.loads(out)['pending_model_recovery'];self.assertEqual(len(rows),1)
  self.assertEqual(rows[0]['operation_id'],'owned-model-op')
  self.assertEqual(rows[0]['diagnose_argv'],['branchwrite','diagnose',str(self.state.absolute()),'--operation-id','owned-model-op'])
  self.assertEqual(rows[0]['reconcile_argv'],['branchwrite','reconcile',str(self.state.absolute()),'--operation-id','owned-model-op'])
  self.assertEqual(rows[0]['resume_argv'],['branchwrite','resume',str(self.state.absolute())])
  self.assertEqual(rows[0]['receipt_argv'],['branchwrite','receipt',str(self.state.absolute()),'--operation-id','owned-model-op'])
  self.assertEqual(self.snapshot(),before)
 def test_pending_tool_is_not_presented_as_model_output_recovery(self):
  self.make()
  with RuntimeLog(self.ledger) as log:
   k=FrameKernel(log);a=log.put_artifact(b'tool');i=log.put_artifact(encode({}))
   k.spawn('program',expected_epoch=0,calls=(CallSpec('tool','tool-attempt','out','ACT',a,i,ResultContract('ToolOutcome','record')),),next_pc=1);k.dispatch('tool','owned-tool-op',i)
  before=self.snapshot();code,out,err=self.invoke('--json');self.assertEqual(code,0,err)
  self.assertEqual(json.loads(out)['pending_model_recovery'],[]);self.assertEqual(self.snapshot(),before)
 def test_status_shows_bounded_recent_activity_without_payloads(self):
  self.native_pending()
  code,out,err=self.invoke('--json','--tail','3')
  self.assertEqual(code,0,err)
  result=json.loads(out);rows=result['recent_activity']
  self.assertEqual([row['kind'] for row in rows],['spawn','spawn','dispatched'])
  self.assertEqual(rows[0]['steps'],['FLOW'])
  self.assertEqual(rows[1]['steps'],['EXPAND'])
  self.assertEqual(rows[2]['operation_id'],'owned-model-op')
  self.assertTrue(all('request' not in row and 'artifact' not in row for row in rows))
  self.assertEqual(len(rows),3)
 def test_status_activity_zero_hides_tail_and_human_output_names_step(self):
  self.native_pending()
  code,out,err=self.invoke('--json','--tail','0')
  self.assertEqual(code,0,err);self.assertEqual(json.loads(out)['recent_activity'],[])
  code,out,err=self.invoke()
  self.assertEqual(code,0,err);self.assertIn('Recent activity',out)
  self.assertIn('dispatched',out);self.assertIn('owned-model-op',out)
 def test_status_rejects_unbounded_activity_tail(self):
  self.native_pending()
  code,out,err=self.invoke('--json','--tail','65')
  self.assertEqual(code,2);self.assertIn('between 0 and 64',err.lower())
 def test_model_guidance_explains_durable_only_recovery_and_resume(self):
  self.native_pending();code,out,err=self.invoke();self.assertEqual(code,0,err)
  self.assertIn('reconcile',out);self.assertIn('resume',out);self.assertIn('durable',out.lower())
