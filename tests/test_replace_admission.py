"""Real preflight/effect boundaries for rejected exact replacements.

Fresh synthetic files, independent of protected workload answers. Fault injection
checks that a completed write with a lost receipt remains indeterminate.
"""
import hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from branchwrite.execution import Executor,Grant,ToolRejected
from branchwrite.tool_registry import ToolRegistry,FrozenToolPlan,EffectIndeterminate
from branchwrite.records import RuntimeLog,encode,decode
from branchwrite.kernel import FrameKernel
from branchwrite.interpreter import Interpreter,Value

class ReplaceAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.source=self.root/'source';self.source.mkdir()
        (self.source/'note.txt').write_bytes(b'alpha beta\n')
        self.executor=Executor.create(self.source,self.root/'world')
        self.registry=ToolRegistry(self.executor,Grant(('note.txt',),False,read_paths=('note.txt',)))
    def proposal(self,before,after):
        data=(self.executor.workspace/'note.txt').read_bytes()
        return json.dumps(dict(tool='replace',arguments=dict(path='note.txt',before=before,after=after)))
    def read(self):
        return self.registry.execute(self.registry.freeze(json.dumps(dict(tool='read_file',arguments=dict(path='note.txt')))),'read')
    def assert_rejected_without_effect(self,proposal):
        read=self.read();before=(self.executor.workspace/'note.txt').read_bytes();artifacts=set(self.executor.artifacts.iterdir())
        with patch.object(self.executor,'replace',side_effect=AssertionError('must reject before effect entry')):
            with self.assertRaisesRegex(ToolRejected,'preimage|file limit'):
                self.registry.freeze(proposal,observations=(read.observation,))
        self.assertEqual((self.executor.workspace/'note.txt').read_bytes(),before)
        self.assertEqual(set(self.executor.artifacts.iterdir()),artifacts)
        self.assertFalse(list(self.executor.workspace.glob('.*.tmp')))
    def test_missing_preimage_is_rejected_before_plan_or_write(self):
        self.assert_rejected_without_effect(self.proposal('beta not present','gamma'))
    def test_ambiguous_preimage_is_rejected_before_plan_or_write(self):
        (self.executor.workspace/'note.txt').write_bytes(b'two two\n')
        self.assert_rejected_without_effect(self.proposal('two','one'))
    def test_replacement_cannot_exceed_existing_file_limit_at_admission(self):
        # The existing Executor limit is 4 MiB. A full file plus one new byte
        # exercises the output bound, not a mocked allocator or altered limit.
        (self.executor.workspace/'note.txt').write_bytes(b'x'*(4*1024*1024-1)+b'!')
        self.assert_rejected_without_effect(self.proposal('!','!!'))
    def test_unique_unicode_replacement_still_writes_exact_bytes(self):
        (self.executor.workspace/'note.txt').write_text('prefix \u03bb suffix\n')
        read=self.read();plan=self.registry.freeze(self.proposal('\u03bb','\u03b2'),observations=(read.observation,))
        result=self.registry.execute(plan,'unicode-edit')
        self.assertEqual(result.disposition,'applied')
        self.assertEqual((self.executor.workspace/'note.txt').read_bytes(),'prefix \u03b2 suffix\n'.encode())
        self.assertEqual((self.source/'note.txt').read_bytes(),b'alpha beta\n')
    def test_execution_rechecks_pure_preconditions_even_for_forged_plan(self):
        read=self.read();plan=self.registry.freeze(self.proposal('beta','gamma'),observations=(read.observation,))
        row=list(decode(plan.data));row[4]=dict(row[4],before='not in file');forged=FrozenToolPlan(encode(tuple(row)))
        with patch.object(self.executor,'replace',side_effect=AssertionError('must reject before effect entry')):
            with self.assertRaisesRegex(ToolRejected,'preimage'):self.registry.execute(forged,'forged-plan')
        self.assertEqual((self.executor.workspace/'note.txt').read_bytes(),b'alpha beta\n')
    def test_lost_receipt_after_write_remains_indeterminate(self):
        read=self.read();plan=self.registry.freeze(self.proposal('beta','gamma'),observations=(read.observation,))
        with patch.object(self.executor,'_result',side_effect=OSError('receipt lost after actual write')):
            with self.assertRaises(EffectIndeterminate):self.registry.execute(plan,'uncertain-write')
        self.assertEqual((self.executor.workspace/'note.txt').read_bytes(),b'alpha gamma\n')
    def test_executor_still_rejects_nonmatching_text_without_a_write(self):
        sha=hashlib.sha256(b'alpha beta\n').hexdigest()
        with self.assertRaisesRegex(ToolRejected,'preimage'):
            self.executor.replace('direct-reject',self.registry._grant,'note.txt',sha,b'absent',b'changed')
        self.assertEqual((self.executor.workspace/'note.txt').read_bytes(),b'alpha beta\n')
    def test_interpreter_returns_rejection_then_accepts_valid_edit_and_reopens_offline(self):
        sha=hashlib.sha256(b'alpha beta\n').hexdigest()
        def proposal(tool,**args):return Value('ToolProposal',json.dumps(dict(tool=tool,arguments=args)))
        bindings={'read-request':proposal('read_file',path='note.txt'),
            'bad-request':proposal('replace',path='note.txt',before='beta not present',after='gamma'),
            'good-request':proposal('replace',path='note.txt',before='beta',after='gamma')}
        program='FLOW repair\nPLAN r from=read-request against=world -> read-plan\nACT r plan=read-plan -> read\nPLAN b from=bad-request against=world -> bad-plan\nACT b plan=bad-plan -> rejected\nTRANSFORM f input=rejected contract=tool-feedback -> feedback\nPLAN g from=good-request against=world -> good-plan\nACT g plan=good-plan -> edited\nEND\n'
        with RuntimeLog(self.root/'ledger') as log:
            kernel=FrameKernel(log);runtime=Interpreter(kernel,self.registry);runtime.start(program,bindings)
            result=runtime.run(max_steps=128)
            self.assertEqual(result.status,'complete')
            self.assertEqual(result.value['bindings']['rejected'][1]['disposition'],'rejected_before_admission')
            feedback=json.loads(result.value['bindings']['feedback'][1]);self.assertIn('preimage',feedback['stderr'])
            self.assertEqual(result.value['bindings']['edited'][1]['disposition'],'applied')
            self.assertTrue(all(f['state']=='Closed' for f in kernel.frames()))
        with RuntimeLog(self.root/'ledger') as log:
            runtime=Interpreter(FrameKernel(log),self.registry)
            with patch.object(self.executor,'replace',side_effect=AssertionError('completed reopen must not execute')):
                reopened=runtime.run(max_steps=16)
            self.assertEqual(reopened.value,result.value)
        self.assertEqual((self.executor.workspace/'note.txt').read_bytes(),b'alpha gamma\n')
