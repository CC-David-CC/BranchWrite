"""Real Kernel -> registry -> Executor -> durable return, no native/model claims."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from branchwrite.execution import Executor,Grant
from branchwrite.records import RuntimeLog,Artifact
from branchwrite.kernel import FrameKernel,ResultContract
from branchwrite.tool_registry import ToolRegistry,EffectIndeterminate
from branchwrite.tool_dispatch import admit_tool,dispatch_tool,ReconciliationRequired

class ToolDispatchTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);source=self.root/'source';source.mkdir();(source/'data.txt').write_bytes(b'actual data')
        self.executor=Executor.create(source,self.root/'world')
        self.registry=ToolRegistry(self.executor,Grant((),False,read_paths=('data.txt',),create_paths=('new.txt',)))
        self.log=RuntimeLog(self.root/'run');self.addCleanup(self.close);self.kernel=FrameKernel(self.log)
        code=self.log.put_artifact(b'FLOW general-tool-client\nEND\n');inputs=self.log.put_artifact(b'original task')
        self.kernel.create_root('root','root-attempt',code,inputs,ResultContract('AgentResult','record'))
    def close(self):
        if not self.log._closed:self.log.close()
    def admit(self,tool,**args):
        return admit_tool(self.kernel,self.registry,'root',expected_epoch=0,child_id='tool-call',
            attempt_id='tool-attempt',slot='outcome',next_pc=1,proposal=json.dumps(dict(tool=tool,arguments=args)))
    def test_actual_read_returns_to_the_exact_parent_slot(self):
        self.admit('read_file',path='data.txt')
        value=dispatch_tool(self.kernel,self.registry,'tool-call')
        self.assertEqual(value['disposition'],'read')
        self.assertEqual(self.log.read_artifact(Artifact(*value['stdout'])),b'actual data')
        self.assertEqual(self.kernel.slot_value('root',1,'outcome'),value)
        self.assertTrue(self.kernel.resume('root',1))
    def test_finished_call_replays_saved_result_after_reopen_without_dispatch(self):
        self.admit('read_file',path='data.txt');original=dispatch_tool(self.kernel,self.registry,'tool-call')
        self.log.close();self.log=RuntimeLog(self.root/'run');self.kernel=FrameKernel(self.log)
        (self.executor.workspace/'data.txt').write_bytes(b'later world revision')
        with patch.object(self.registry,'execute',side_effect=AssertionError('must not execute again')):
            replayed=dispatch_tool(self.kernel,self.registry,'tool-call')
        self.assertEqual(replayed,original)
    def test_relevant_change_becomes_a_durable_known_preflight_rejection(self):
        self.admit('read_file',path='data.txt');(self.executor.workspace/'data.txt').write_bytes(b'changed')
        value=dispatch_tool(self.kernel,self.registry,'tool-call')
        self.assertEqual(value['disposition'],'rejected_before_execution')
        self.assertEqual(self.kernel.frame('tool-call')['state'],'Closed')
        self.assertTrue(self.kernel.resume('root',1))
    def test_after_effect_failure_leaves_waiting_and_never_resends(self):
        self.admit('create_file',path='new.txt',content='written once')
        with patch.object(self.executor,'_result',side_effect=OSError('injected receipt failure')):
            with self.assertRaises(EffectIndeterminate):dispatch_tool(self.kernel,self.registry,'tool-call')
        self.assertEqual((self.executor.workspace/'new.txt').read_bytes(),b'written once')
        self.assertEqual(self.kernel.frame('tool-call')['state'],'Waiting')
        with patch.object(self.registry,'execute',side_effect=AssertionError('pending work must not be resent')):
            with self.assertRaises(ReconciliationRequired):dispatch_tool(self.kernel,self.registry,'tool-call')
        self.assertEqual(self.kernel.frame('root')['state'],'Waiting')
    def test_finish_is_a_pure_request_not_an_acceptance_or_automatic_flow_close(self):
        self.admit('finish',answer='Work is ready to verify.')
        value=dispatch_tool(self.kernel,self.registry,'tool-call')
        self.assertTrue(value['requested_finish']);self.assertNotIn('accepted',value)
        self.assertEqual(self.kernel.frame('root')['state'],'Waiting')
        self.kernel.resume('root',1);self.kernel.finish('root',value)
        self.assertEqual(self.kernel.frame('root')['state'],'Closed')
