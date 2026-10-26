"""Scripted CPU machinery through real BW/COW/OS boundaries, not model learning."""
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from branchwrite.coding_cli import build_launch, save_launch, run_saved
from branchwrite.lesson_capture import capture_failure, capture_correction, read_capture, CaptureRefused
from branchwrite.records import RuntimeLog, WriterBusy


class LessonCaptureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.project = self.root / 'project'; self.project.mkdir()
        (self.project / 'value.txt').write_bytes(b'wrong\n')
        self.actions = []
        from test_thinking_grammar import ThinkingTokenizer
        from serve.test_cow_grammar_canonical_flow import GrammarCPUBackend, _render, _encode, _initial_root_mode
        from context_time_travel.real import BranchingModel
        from context_time_travel.coordinator import ContextCoordinator
        from context_time_travel.pools import PoolConfig
        from serve.cow_adapter import CowAdapter
        from serve.cow_text_adapter import CowTextAdapter
        from serve.cow_grammar_disk import DurableGrammarCatalog
        from serve.cow_http import make_server
        self.tokenizer = ThinkingTokenizer()
        profile = dict(model_contract_id='a'*64, execution_profile_id='b'*64, model_weights_sha256='c'*64,
            execution=dict(GPU=[0], resume_contract='identical-native-operators-v1',
                generated_operator='normal-verifier-decode', selected_token_protocol='consumed-selected-receipt-v1',
                sampling_protocol='full-vocab-min-p-u53-v2',
                native_request_protocol='consumed-greedy-ack-v1', prefill_chunk=16, capacity=131072, eos_tokens=[256]))
        owner = self
        class ScriptedBackend(GrammarCPUBackend):
            def __init__(self, p, tok):
                super().__init__(p, tok); self.index = 0; self.cursor = 0
            def selected(self):
                action = owner.actions[min(self.index, len(owner.actions)-1)]
                body = json.dumps(action, separators=(',', ':')).encode()
                return body[self.cursor] if self.cursor < len(body) else 256
            def logits(self, lease):
                desired = self.selected() if owner.actions else 256
                return tuple(1000. if t == desired else -1000. for t in range(self.vocab_size))
            def sample_legal(self, lease, mask, *args, **kwargs):
                token = self.selected()
                if not mask[token >> 3] & (1 << (token & 7)): raise AssertionError('Script does not fit real grammar')
                return token
            def consume_generated(self, lease, ids):
                super().consume_generated(lease, ids)
                for token in ids:
                    if token == 256: self.index += 1; self.cursor = 0
                    else: self.cursor += 1
        coordinator = ContextCoordinator(self.root/'cow-store', PoolConfig(gpus=(0,), ram_bytes=64*1024**2,
            disk_bytes=256*1024**2, min_available_bytes=0),
            lambda gpu: BranchingModel(self.root/'cow-store', ScriptedBackend(profile, self.tokenizer), profile))
        self.coordinator = coordinator
        self.addCleanup(coordinator.close); coordinator.ready(5)
        adapter = CowAdapter(coordinator)
        text = CowTextAdapter(adapter, self.tokenizer, _render,
            lambda messages, rendered, add_generation_prompt: _encode(self.tokenizer, messages, rendered, add_generation_prompt),
            initial_root_mode=lambda canonical, controller: ('context_only' if controller == {'status':'idle'} else 'unsupported'),
            append_initial_user_suffix=lambda canonical, controller, content: tuple(self.tokenizer.encode('\nuser:'+content+'\nassistant:', parse_special=False)),
            append_user_suffix=lambda canonical, controller, content: tuple(self.tokenizer.encode('\nuser:'+content+'\nassistant:', parse_special=False)),
            renderer_id='d'*64)
        catalog = DurableGrammarCatalog(self.root/'grammars', self.tokenizer, [256]); self.addCleanup(catalog.close)
        server = make_server(adapter, api_key='capture-fixture', text_adapter=text, grammar_catalog=catalog,
            connection_info=dict(model_contract_id=profile['model_contract_id'], execution_profile_id=profile['execution_profile_id'], eos_tokens=[256]))
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        self.addCleanup(lambda: (server.shutdown(), server.server_close(), thread.join(5)))
        self.connection = dict(endpoint_url='http://127.0.0.1:'+str(server.server_port), endpoint_pin='owned-scripted-cpu',
            model_contract_id=profile['model_contract_id'], execution_profile_id=profile['execution_profile_id'], eos_tokens=[256])
        self.environment = patch.dict(os.environ, BW_COW_API_KEY='capture-fixture'); self.environment.start(); self.addCleanup(self.environment.stop)

    def run_case(self, name, corrected=False, steps=1024, partial=False, no_check=False):
        self.actions[:] = [dict(tool='read_file', arguments=dict(path='value.txt'))]
        if corrected: self.actions.append(dict(tool='replace', arguments=dict(path='value.txt', before='wrong', after='right')))
        if not no_check:
            self.actions += [dict(tool='run_check', arguments=dict(name='content', command='test "$(cat value.txt)" = right')),
                             dict(tool='finish', arguments=dict(answer='Scripted CPU host-boundary exercise'))]
        if partial:self.actions[:]=[dict(tool='finish',arguments=dict(answer='x'*8192))]
        # Each fresh server backend keeps one script cursor; use a separate test
        # state but reset the deterministic selector before this fresh workflow.
        for worker in self.coordinator_workers():
            worker.index = worker.cursor = 0
        state = self.root/name
        launch = build_launch(self.project, 'Make value.txt contain right followed by newline.', self.connection,
            branch=name, project_files=True, thinking_mode='off', instruction_style='compact-finish-request', shell_timeout=2)
        save_launch(state, launch)
        returned = []; native_returned=[]
        def progress(event):
            if event == 'tool_returned': returned.append(event)
            if event == 'model_step_returned':native_returned.append(event)
        _, result = run_saved(state, max_steps=steps, progress=progress,
            control=(lambda: bool(native_returned)) if partial else (lambda: len(returned) >= len(self.actions)) if no_check
                else None if corrected else lambda: len(returned) >= 2)
        return state, result

    def coordinator_workers(self):
        # Saved in the test only, never a product receipt or alternate authority.
        return [self.coordinator._workers[0]['model'].backend]

    def test_actual_scripted_failed_capture_then_verified_correction(self):
        failed, result = self.run_case('failed')
        self.assertFalse(result['verified'])
        first = capture_failure(failed, self.root/'failure-capture')
        self.assertEqual(first.file_bytes('value.txt'), b'wrong\n')
        self.assertFalse(first.independently_verified)
        fixed, result = self.run_case('fixed', True)
        self.assertTrue(result['verified'])
        from branchwrite.lesson_cli import main
        output=[]
        with patch('branchwrite.lesson_cli._client',side_effect=AssertionError('capture must not construct transport')):
            self.assertEqual(main(['capture-correction',str(fixed),'--failure-capture',str(first.directory),
                '--output',str(self.root/'correction-capture')],output=output.append),0,output)
        second=read_capture(self.root/'correction-capture')
        self.assertEqual(second.file_bytes('value.txt'), b'right\n')
        self.assertEqual(second.failure_capture_id, first.capture_id)
        self.assertGreater(len(second.manifest['evidence']['native']), 0)
        self.assertFalse(second.training_approved)
        self.assertEqual(read_capture(second.directory).capture_id, second.capture_id)
        # Original operational paths (including COW journals and worlds) disappear.
        # The correction archive also embeds the exact preceding failure archive.
        failed.rename(self.root/'hidden-failed');fixed.rename(self.root/'hidden-fixed')
        first.directory.rename(self.root/'hidden-failure-archive')
        self.project.rename(self.root/'hidden-project')
        self.assertEqual(read_capture(second.directory,expected_capture_id=second.capture_id).file_bytes('value.txt'),b'right\n')
        if os.environ.get('BW_CAPTURE_CPU_EVIDENCE'):
            import shutil
            destination=Path(os.environ['BW_CAPTURE_CPU_EVIDENCE'])/'scripted-cpu-correction'
            shutil.copytree(second.directory,destination)
            self.assertEqual(read_capture(destination,expected_capture_id=second.capture_id).capture_id,second.capture_id)
        fixed=self.root/'hidden-fixed'
        (fixed/'world/workspace/value.txt').write_bytes(b'later\n')
        self.assertEqual(second.file_bytes('value.txt'), b'right\n')

    def test_stopped_failure_without_live_effect_is_captureable(self):
        state, result = self.run_case('stopped', steps=128)
        self.assertFalse(result['verified'])
        captured = capture_failure(state, self.root/'stopped-capture')
        self.assertFalse(captured.training_approved)

    def test_settled_read_only_no_check_failure_archives_actual_baseline_without_grade(self):
        state,result=self.run_case('no-check',no_check=True)
        self.assertFalse(result['verified']);self.assertEqual(result['status'],'interrupted')
        captured=capture_failure(state,self.root/'no-check-failure')
        evidence=captured.manifest['evidence']
        self.assertEqual(evidence['checks'],[])
        self.assertIsNone(evidence['recorded_workflow_verified'])
        self.assertEqual(evidence['world_binding'],'unchanged-baseline-no-check-v1')
        self.assertEqual(evidence['baseline_inventory'],captured.manifest['inventory'])
        self.assertEqual([t['tool'] for t in evidence['tools']],['read_file'])
        self.assertGreater(len(evidence['native']),0)
        self.assertEqual(captured.file_bytes('value.txt'),b'wrong\n')
        self.assertFalse(captured.independently_verified);self.assertFalse(captured.training_approved)

    def test_no_check_boundary_cannot_be_promoted_to_correction(self):
        state,_=self.run_case('no-check',no_check=True)
        captured=capture_failure(state,self.root/'no-check-failure')
        with self.assertRaisesRegex(CaptureRefused,'current passing checks'):
            capture_correction(state,self.root/'no-check-correction',captured.directory)

    def test_settled_unchecked_write_refuses_instead_of_inventing_state_proof(self):
        state,_=self.run_case('unchecked-write',corrected=True,no_check=True)
        self.assertEqual((state/'world/workspace/value.txt').read_bytes(),b'right\n')
        with self.assertRaisesRegex(CaptureRefused,'unchecked changed/file-effect world'):
            capture_failure(state,self.root/'unsupported-unchecked-write')

    def test_live_writer_and_writer_during_capture_are_excluded(self):
        state, _ = self.run_case('failed')
        with RuntimeLog(state/'ledger'):
            with self.assertRaises(WriterBusy): capture_failure(state, self.root/'busy')
        from branchwrite import lesson_capture
        original = lesson_capture._capture_files
        def held(*args, **kwargs):
            with self.assertRaises(WriterBusy):
                with RuntimeLog(state/'ledger'): pass
            return original(*args, **kwargs)
        with patch.object(lesson_capture, '_capture_files', side_effect=held):
            capture_failure(state, self.root/'leased')

    def test_alias_symlink_hardlink_changed_file_and_bounds_refuse(self):
        state, _ = self.run_case('failed')
        with self.assertRaises(CaptureRefused): capture_failure(state, state/'capture')
        alias=self.root/'alias'; alias.symlink_to(state, target_is_directory=True)
        with self.assertRaises(CaptureRefused): capture_failure(alias, self.root/'alias-capture')
        work=state/'world/workspace'; (work/'link').symlink_to(work/'value.txt')
        with self.assertRaises(CaptureRefused): capture_failure(state, self.root/'linked')
        (work/'link').unlink(); os.link(work/'value.txt', work/'hard')
        with self.assertRaises(CaptureRefused): capture_failure(state, self.root/'hardlinked')
        (work/'hard').unlink()
        with patch('branchwrite.lesson_capture.MAX_WORLD_BYTES', 2):
            with self.assertRaises(CaptureRefused): capture_failure(state, self.root/'large')
        (work/'value.txt').write_bytes(b'changed since check\n')
        with self.assertRaises(CaptureRefused): capture_failure(state, self.root/'stale')

    def test_capture_reader_detects_changes_and_correction_needs_original_failure(self):
        state, _ = self.run_case('failed')
        saved=capture_failure(state, self.root/'capture')
        blob=saved.directory/'objects'/saved.manifest['files'][0]['sha256']
        blob.chmod(0o600);blob.write_bytes(b'tampered')
        with self.assertRaises(CaptureRefused): read_capture(saved.directory)
        fixed, _=self.run_case('fixed',True)
        with self.assertRaises((CaptureRefused,FileNotFoundError)):
            capture_correction(fixed,self.root/'missing',self.root/'does-not-exist')

    def test_cli_capture_and_show_never_construct_a_transport(self):
        from branchwrite.lesson_cli import main
        state,_=self.run_case('failed'); output=[]
        with patch('branchwrite.lesson_cli._client',side_effect=AssertionError('no transport')):
            self.assertEqual(main(['capture-failure',str(state),'--output',str(self.root/'cli-capture')],output=output.append),0,output)
            record=json.loads(output[-1]); identity=record['capture_id']
            self.assertFalse(record['independently_verified']);self.assertFalse(record['training_approved'])
            self.assertEqual(main(['capture-show',str(self.root/'cli-capture'),'--expected-capture-id',identity],output=output.append),0)
            self.assertEqual(main(['capture-show',str(self.root/'cli-capture'),'--expected-capture-id','0'*64],output=output.append),2)

    def test_pending_or_changed_native_journal_refuses_without_network(self):
        from branchwrite.cow_client import OperationJournal,_record_digest
        state,_=self.run_case('failed'); journal=OperationJournal(state/'cow-operations')
        path=next(p for p in journal.directory.iterdir() if '/cow/text/ask' in p.read_text())
        row=json.loads(path.read_text());row['state']='pending';row['record_sha256']=_record_digest(row)
        path.write_text(json.dumps(row))
        with self.assertRaises(CaptureRefused):capture_failure(state,self.root/'pending-native')

    def test_complete_flag_cannot_hide_native_output_conflict(self):
        from branchwrite.cow_client import _record_digest
        state,_=self.run_case('failed')
        path=next(p for p in (state/'cow-operations').iterdir() if '/cow/text/ask' in p.read_text())
        row=json.loads(path.read_text());row['answer']['text']='different retained text'
        row['record_sha256']=_record_digest(row);path.write_text(json.dumps(row))
        with self.assertRaises(CaptureRefused):capture_failure(state,self.root/'forged-complete')

    def test_actual_closed_partial_generation_is_not_a_finished_model_turn(self):
        state,_=self.run_case('partial',partial=True)
        rows=[json.loads(p.read_text()) for p in (state/'cow-operations').iterdir()]
        self.assertTrue(any(r.get('state')=='complete' and r.get('answer',{}).get('stopped') is False for r in rows))
        with self.assertRaisesRegex(CaptureRefused,'partial logical model output'):
            capture_failure(state,self.root/'partial-capture')

    def test_unfinished_state_cannot_be_called_a_correction(self):
        state,_=self.run_case('failed');first=capture_failure(state,self.root/'original-failure')
        with self.assertRaisesRegex(CaptureRefused,'current passing checks'):
            capture_correction(state,self.root/'no-finish',first.directory)

    def test_live_dispatched_tool_refuses_and_never_grades_current_files(self):
        from branchwrite.kernel import FrameKernel,CallSpec,ResultContract
        from branchwrite.records import Artifact,decode
        state,_=self.run_case('failed')
        with RuntimeLog(state/'ledger') as log:
            kernel=FrameKernel(log)
            closed=[f for f in kernel.frames() if f['contract']==('ToolOutcome','record') and f['state']=='Closed'][-1]
            parent=kernel.frame(closed['parent'])
            kernel.resume(parent['id'],parent['epoch'])
            kernel.spawn(parent['id'],expected_epoch=kernel.frame(parent['id'])['epoch'],calls=(CallSpec('unsettled-tool','uncertain-attempt','new','ACT',Artifact(*closed['definition']),Artifact(*closed['inputs']),ResultContract('ToolOutcome','record')),),next_pc=parent['pc']+1)
            kernel.dispatch('unsettled-tool','uncertain-operation',Artifact(*closed['inputs']))
        with self.assertRaisesRegex(CaptureRefused,'settled ledger result'):
            capture_failure(state,self.root/'uncertain')

    def test_world_change_during_continuous_inspection_refuses(self):
        state,_=self.run_case('failed')
        from branchwrite import lesson_capture
        original=lesson_capture._capture_files; calls=[]
        def changing(*args,**kwargs):
            value=original(*args,**kwargs)
            if not calls:
                calls.append(1);(state/'world/workspace/value.txt').write_bytes(b'concurrent owner edit\n')
            return value
        with patch.object(lesson_capture,'_capture_files',side_effect=changing):
            with self.assertRaisesRegex(CaptureRefused,'changed during archival'):
                capture_failure(state,self.root/'changing')
        self.assertFalse((self.root/'changing/capture.json').exists())

    def test_live_namespace_observation_cannot_be_overridden_by_retired_flag(self):
        state,_=self.run_case('failed')
        with patch('branchwrite.browser_isolation.await_namespace_retirement',return_value=[12345]):
            with self.assertRaisesRegex(CaptureRefused,'namespace is still present'):
                capture_failure(state,self.root/'unretired')

    def test_recomputed_manifest_cannot_pair_new_bytes_with_old_check_inventory(self):
        import hashlib
        from branchwrite.lesson_capture import _canonical
        state,_=self.run_case('failed');saved=capture_failure(state,self.root/'original')
        value=saved.manifest;row=next(r for r in value['files'] if r['path']=='value.txt')
        old=saved.directory/'objects'/row['sha256'];old.unlink()
        raw=b'unchecked bytes\n';row['sha256']=hashlib.sha256(raw).hexdigest();row['bytes']=len(raw)
        (saved.directory/'objects'/row['sha256']).write_bytes(raw)
        value['capture_id']=hashlib.sha256(_canonical({k:v for k,v in value.items() if k!='capture_id'})).hexdigest()
        path=saved.directory/'capture.json';path.chmod(0o600);path.write_bytes(_canonical(value))
        with self.assertRaisesRegex(CaptureRefused,'inventory does not describe'):
            read_capture(saved.directory)

    def test_reader_refuses_changed_validator_helper_source_identity(self):
        state,_=self.run_case('failed');saved=capture_failure(state,self.root/'capture')
        from branchwrite import lesson_capture
        identity=lesson_capture._implementation();identity['kernel.py']='0'*64
        with patch.object(lesson_capture,'_implementation',return_value=identity):
            with self.assertRaisesRegex(CaptureRefused,'validator/helper source differs'):
                read_capture(saved.directory)


if __name__ == '__main__': unittest.main()
