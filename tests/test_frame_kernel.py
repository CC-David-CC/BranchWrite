"""Real durable controller tests; no mocked GPU or autonomy claim."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from branchwrite.records import RuntimeLog, WriterPoisoned, CorruptLog
from branchwrite.kernel import FrameKernel, CallSpec, ResultContract, TransitionError

class FrameKernelTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'run';self.log=RuntimeLog(self.root);self.addCleanup(self.close)
        self.kernel=FrameKernel(self.log)
        self.program=self.log.put_artifact(b'FLOW test\nEND\n');self.inputs=self.log.put_artifact(b'exact inputs')
        self.contract=ResultContract('ToolOutcome','record')
        self.kernel.create_root('root','attempt-root',self.program,self.inputs,self.contract)
    def close(self):
        if not self.log._closed:self.log.close()
    def call(self,name,slot=None):
        return CallSpec(name,'attempt-'+name,slot or name,'tool.operation',self.program,self.inputs,self.contract)
    def spawn(self,names=('A',)):
        return self.kernel.spawn('root',expected_epoch=0,calls=tuple(self.call(n) for n in names),next_pc=1)
    def dispatch(self,name):
        request=self.log.put_artifact(('exact-request-'+name).encode())
        self.kernel.dispatch(name,'operation-'+name,request)
        return request
    def return_(self,name,value=None,settled=True):
        return self.kernel.record_result(name,'operation-'+name,{'answer':name} if value is None else value,settled=settled)
    def test_call_and_named_wait_are_one_durable_event(self):
        before=self.log.event_count;epoch=self.spawn(('A','B'))
        self.assertEqual(self.log.event_count,before+1);self.assertEqual(epoch,1)
        self.assertEqual(self.kernel.frame('root')['state'],'Waiting')
        self.assertEqual(self.kernel.frame('A')['state'],'Ready')
        self.assertEqual(self.kernel.frame('B')['parent'],'root')
    def test_reverse_returns_bind_named_slots_not_arrival_order(self):
        self.spawn(('A','B'));self.dispatch('A');self.dispatch('B')
        self.return_('B');self.return_('A')
        self.assertEqual(self.kernel.slot_value('root',1,'A'),{'answer':'A'})
        self.assertEqual(self.kernel.slot_value('root',1,'B'),{'answer':'B'})
        self.assertTrue(self.kernel.resume('root',1));self.assertFalse(self.kernel.resume('root',1))
        self.assertEqual(self.kernel.frame('root')['pc'],1)
    def test_duplicate_return_is_idempotent_but_conflicting_value_is_rejected(self):
        self.spawn();self.dispatch('A');first=self.return_('A');before=self.log.event_count
        self.assertEqual(self.return_('A'),first);self.assertEqual(self.log.event_count,before)
        with self.assertRaises(TransitionError):self.return_('A',{'answer':'different'})
        self.assertEqual(self.kernel.slot_value('root',1,'A'),{'answer':'A'})
    def test_pending_resource_result_does_not_deliver_or_resume(self):
        self.spawn();self.dispatch('A');self.return_('A',settled=False)
        self.assertEqual(self.kernel.frame('A')['state'],'Settling')
        with self.assertRaises(TransitionError):self.kernel.resume('root',1)
        with self.assertRaises(KeyError):self.kernel.slot_value('root',1,'A')
        proof=self.log.put_artifact(b'observed process exit receipt')
        self.kernel.settle('A','operation-A',proof)
        self.assertEqual(self.kernel.frame('A')['state'],'Closed');self.assertTrue(self.kernel.resume('root',1))
    def test_undispatched_wrong_operation_and_wrong_type_cannot_return(self):
        self.spawn();before=self.log.event_count
        with self.assertRaises(TransitionError):self.return_('A')
        self.assertEqual(self.log.event_count,before);self.dispatch('A')
        with self.assertRaises(TransitionError):self.kernel.record_result('A','other-operation',{})
        with self.assertRaises(TransitionError):self.return_('A','wrong type')
        self.assertEqual(self.kernel.frame('A')['state'],'Waiting')
    def test_return_for_old_group_cannot_overwrite_a_new_wait(self):
        self.spawn();self.dispatch('A');self.return_('A');self.kernel.resume('root',1)
        self.kernel.spawn('root',expected_epoch=1,calls=(self.call('C','A'),),next_pc=2)
        self.return_('A')
        with self.assertRaises(KeyError):self.kernel.slot_value('root',2,'A')
        self.assertEqual(self.kernel.frame('root')['state'],'Waiting')
    def test_changed_spawn_duplicate_child_and_duplicate_slot_are_rejected(self):
        self.spawn();before=self.log.event_count
        self.assertEqual(self.spawn(),1);self.assertEqual(self.log.event_count,before)
        with self.assertRaises(TransitionError):self.spawn(('B',))
        with self.assertRaises(TransitionError):self.kernel.spawn('root',expected_epoch=1,calls=(self.call('X','same'),self.call('Y','same')),next_pc=2)
    def test_pending_dispatch_reopen_requires_reconciliation_instead_of_resend(self):
        self.spawn();request=self.dispatch('A');self.log.close();self.log=RuntimeLog(self.root)
        kernel=FrameKernel(self.log)
        self.assertFalse(kernel.dispatch('A','operation-A',request))
        with self.assertRaises(TransitionError):kernel.dispatch('A','new-operation',request)
        self.assertNotIn('A',kernel.ready())
    def test_restart_after_return_before_parent_resume_preserves_exact_value(self):
        self.spawn();self.dispatch('A');result=self.return_('A',{'bytes':b'\x00\xff','none':None})
        self.log.close();self.log=RuntimeLog(self.root);kernel=FrameKernel(self.log)
        self.assertEqual(kernel.frame('A')['state'],'Closed');self.assertEqual(kernel.frame('root')['state'],'Waiting')
        self.assertEqual(kernel.slot_value('root',1,'A'),{'bytes':b'\x00\xff','none':None})
        self.assertTrue(kernel.resume('root',1));self.assertFalse(kernel.resume('root',1))
        self.assertEqual(kernel.frame('A')['result'],(result.sha256,result.size_bytes))
    def test_projection_views_are_detached(self):
        value=self.kernel.frame('root');value['state']='Closed'
        self.assertEqual(self.kernel.frame('root')['state'],'Ready')
    def test_another_facade_cannot_dispatch_from_a_stale_projection(self):
        other=FrameKernel(self.log);self.spawn()
        with self.assertRaises(TransitionError):other.spawn('root',expected_epoch=0,calls=(self.call('B'),),next_pc=1)
    def test_uncertain_append_blocks_the_facade_until_reopen(self):
        original=os.fsync
        def fail_ledger_sync(fd):
            if os.readlink('/proc/self/fd/'+str(fd))==str(self.root/'events.bwl'):
                raise OSError('injected ledger sync failure')
            original(fd)
        with patch('branchwrite.records.os.fsync',side_effect=fail_ledger_sync):
            with self.assertRaises(OSError):self.spawn()
        with self.assertRaises(WriterPoisoned):self.kernel.frame('root')
        with self.assertRaises(WriterPoisoned):self.spawn()
        self.log.close();self.log=RuntimeLog(self.root);kernel=FrameKernel(self.log)
        self.assertEqual(kernel.frame('root')['state'],'Waiting')
    def test_result_contract_preserves_exact_bool_int_and_bytes_text_types(self):
        for shape,valid,invalid in [('bool',True,1),('int',1,True),('bytes',b'x','x'),('text','x',b'x')]:
            contract=ResultContract('Result-'+shape,shape)
            contract.check(valid)
            with self.subTest(shape=shape),self.assertRaises(TransitionError):contract.check(invalid)
    def test_semantically_invalid_but_checksummed_record_is_rejected_on_reopen(self):
        self.log.append({'schema':1,'kind':'resumed','parent':'missing','epoch':9})
        self.log.close();self.log=RuntimeLog(self.root)
        with self.assertRaises(CorruptLog):FrameKernel(self.log)

    def test_artifact_sync_failure_prevents_call_admission_without_poisoning_the_log(self):
        original=os.fsync
        def fail_artifact_sync(fd):
            path=os.readlink('/proc/self/fd/'+str(fd))
            if path.startswith(str(self.root/'artifacts')+'/'):raise OSError('injected artifact sync failure')
            original(fd)
        before=self.log.event_count
        with patch('branchwrite.records.os.fsync',side_effect=fail_artifact_sync):
            with self.assertRaises(OSError):self.spawn()
        self.assertEqual(self.log.event_count,before)
        self.assertEqual(self.kernel.frame('root')['state'],'Ready')
        self.assertEqual(self.spawn(),1)
    def test_duplicate_slots_and_children_are_rejected_while_parent_is_actually_ready(self):
        before=self.log.event_count
        for calls in [(self.call('X','same'),self.call('Y','same')),(self.call('X','one'),self.call('X','two'))]:
            with self.subTest(calls=calls),self.assertRaises(TransitionError):
                self.kernel.spawn('root',expected_epoch=0,calls=calls,next_pc=1)
            self.assertEqual(self.log.event_count,before)
        self.spawn(('X','Y'))
    def test_operation_id_cannot_be_shared_by_different_children(self):
        self.spawn(('A','B'));request=self.dispatch('A')
        with self.assertRaises(TransitionError):self.kernel.dispatch('B','operation-A',request)
        self.assertEqual(self.kernel.frame('B')['state'],'Ready')
    def test_real_effect_return_then_process_exit_resumes_without_repeating_effect(self):
        self.log.close()
        counter=Path(self.temp.name)/'world-counter'
        code = r"""
from pathlib import Path
import os,subprocess,sys
from branchwrite.records import RuntimeLog
from branchwrite.kernel import FrameKernel,CallSpec,ResultContract
with RuntimeLog(sys.argv[1]) as log:
 k=FrameKernel(log);parent=k.frame('root');definition=log.put_artifact(b'owned counter tool')
 inputs=log.put_artifact(sys.argv[2].encode())
 k.spawn('root',expected_epoch=0,calls=(CallSpec('effect','attempt-effect','output','tool.counter',definition,inputs,ResultContract('ToolOutcome','record')),),next_pc=1)
 request=log.put_artifact(b'exact registered counter request')
 assert k.dispatch('effect','operation-effect',request)
 command=[sys.executable,'-B','-c','from pathlib import Path;import sys;p=Path(sys.argv[1]);p.write_text(str(int(p.read_text())+1) if p.exists() else "1");print("observed")',sys.argv[2]]
 effect=subprocess.run(command,capture_output=True,check=True,timeout=5)
 provenance=log.put_artifact(effect.stdout)
 k.record_result('effect','operation-effect',{'exit':effect.returncode,'stdout':effect.stdout},provenance=(provenance,),settled=True)
 os._exit(47)
"""
        producer=subprocess.run([sys.executable,'-B','-c',code,str(self.root),str(counter)],capture_output=True,timeout=10)
        self.assertEqual(producer.returncode,47,producer.stderr.decode());self.assertEqual(counter.read_text(),'1')
        self.log=RuntimeLog(self.root);kernel=FrameKernel(self.log)
        self.assertEqual(kernel.frame('effect')['state'],'Closed')
        request=self.log.put_artifact(b'exact registered counter request')
        self.assertFalse(kernel.dispatch('effect','operation-effect',request))
        self.assertEqual(kernel.slot_value('root',1,'output'),{'exit':0,'stdout':b'observed\n'})
        self.assertTrue(kernel.resume('root',1));self.assertFalse(kernel.resume('root',1))
        self.assertEqual(counter.read_text(),'1')

    def test_flow_finishes_only_after_waits_resume_and_keeps_its_return_on_restart(self):
        self.spawn()
        with self.assertRaises(TransitionError):self.kernel.finish('root',{'done':True})
        self.dispatch('A');self.return_('A')
        with self.assertRaises(TransitionError):self.kernel.finish('root',{'done':True})
        self.kernel.resume('root',1)
        result=self.kernel.finish('root',{'done':True})
        self.assertEqual(self.kernel.frame('root')['state'],'Closed');self.assertEqual(self.kernel.ready(),())
        before=self.log.event_count
        self.assertEqual(self.kernel.finish('root',{'done':True}),result);self.assertEqual(self.log.event_count,before)
        with self.assertRaises(TransitionError):self.kernel.finish('root',{'done':False})
        self.log.close();self.log=RuntimeLog(self.root);kernel=FrameKernel(self.log)
        self.assertEqual(kernel.frame('root')['result'],(result.sha256,result.size_bytes))
        self.assertEqual(kernel.frame('root')['state'],'Closed')
    def test_nested_flow_returns_to_its_parent_but_an_undispatched_tool_cannot_finish(self):
        nested=CallSpec('builder','attempt-builder','built','FLOW',self.program,self.inputs,self.contract)
        self.kernel.spawn('root',expected_epoch=0,calls=(nested,),next_pc=1)
        self.kernel.spawn('builder',expected_epoch=0,calls=(self.call('effect'),),next_pc=1)
        with self.assertRaises(TransitionError):self.kernel.finish('effect',{'pretend':'effect success'})
        self.dispatch('effect');self.return_('effect');self.kernel.resume('builder',1)
        self.kernel.finish('builder',{'source':b'actual child bytes'})
        self.assertEqual(self.kernel.slot_value('root',1,'built'),{'source':b'actual child bytes'})
        self.kernel.resume('root',1);self.kernel.finish('root',{'result':'returned'})
        self.assertEqual(self.kernel.ready(),())
