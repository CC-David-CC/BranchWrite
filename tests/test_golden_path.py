"""Golden summaries use ordinary COW histories, never a shadow transcript."""
import hashlib
import json
import tempfile
import unittest

import test_cow_client_flow as fixture


class GoldenPathTests(unittest.TestCase):
    def setUp(self):
        from branchwrite.golden_path import GoldenPath, Observation
        self.Observation = Observation
        self.case = fixture.CowClientFlowTests()
        self.addCleanup(self.case.doCleanups)
        self.case.setUp()
        self.client = self.case._client('cli', 'golden')
        namespace = self.client.create_namespace('Golden', 'golden-ns')['namespace_id']
        self.golden = GoldenPath(self.client, namespace, eos_tokens=(299,))
        self.root = self.golden.start('golden-root', 'Make verified work useful.',
                                      ('An observed passing test is evidence, not permission.',), 'golden-root-op')
        self.raw = b'Ran 7 tests\nOK\n'
        self.observation = Observation.from_bytes('unit-tests', 'test-run-1', self.raw,
                                                  'Seven tests passed.', observed_ns=100)

    def test_summary_forks_prior_tip_and_binds_host_facts_in_canonical_messages(self):
        version = self.golden.refresh(self.root, 'golden-v1', (self.observation,),
                                      'golden-fork', 'ask-a', 2, now_ns=101)
        self.assertEqual(version.number, 1)
        self.assertEqual(version.parent_snapshot, self.root.snapshot)
        self.assertEqual(version.summary, 'hi')
        self.assertEqual(self.client.head('golden-root').tip, self.root.snapshot)
        history = self.client.history(version.branch).messages
        user = next(item['text'] for item in history if item['role'] == 'user')
        manifest = json.loads(user.split('\n', 1)[1])
        self.assertEqual(manifest['observations'][0]['evidence_sha256'], hashlib.sha256(self.raw).hexdigest())
        self.assertIn('Seven tests passed.', user)
        self.assertEqual(version.manifest_sha256, hashlib.sha256(user.encode()).hexdigest())
        self.assertEqual(version.endpoint_pin, 'flow-model-free')

    def test_incomplete_summary_preserves_old_version_and_exposes_partial_receipt(self):
        from branchwrite.golden_path import IncompleteSummary
        with self.assertRaises(IncompleteSummary) as caught:
            self.golden.refresh(self.root, 'golden-partial', (self.observation,),
                                'partial-fork', 'answer-op', 1, now_ns=101)
        self.assertEqual(caught.exception.result.answer['tokens'], [257])
        self.assertEqual(self.client.head('golden-root').tip, self.root.snapshot)
        self.assertEqual(self.client.head('golden-partial').tip,
                         caught.exception.result.receipt.snapshot)

    def test_stale_or_duplicate_facts_reject_before_fork(self):
        before = len(self.case.trace)
        expired = self.Observation.from_bytes('old', 'old-run', b'old', 'Old fact.',
                                               observed_ns=90, expires_ns=100)
        for facts in ((expired,), (self.observation, self.observation)):
            with self.assertRaises(ValueError):
                self.golden.refresh(self.root, 'must-not-exist', facts,
                                    'no-fork', 'ask-a', 2, now_ns=101)
        self.assertEqual(len(self.case.trace), before)
        self.assertIsNone(self.client.journal.read('no-fork'))

    def test_worker_forks_exact_summary_version_and_cannot_move_golden(self):
        version = self.golden.refresh(self.root, 'golden-v1', (self.observation,),
                                      'golden-fork', 'ask-a', 2, now_ns=101)
        head = self.golden.fork_worker(version, 'worker', 'worker-fork')
        self.assertEqual(head.tip, version.snapshot)
        self.client.append_user('worker', head.revision, 'user-op', 'Propose the next check.', 2)
        self.assertEqual(self.client.head(version.branch).tip, version.snapshot)
        original = self.client.journal.read('worker-fork')['source_binding']
        self.assertEqual(original['snapshot'], version.snapshot)

    def test_refresh_after_completed_summary_uses_new_turn_without_changing_old_version(self):
        first = self.golden.refresh(self.root, 'golden-v1', (self.observation,),
                                   'golden-fork', 'ask-a', 2, now_ns=101)
        second = self.golden.refresh(first, 'golden-v2', (self.observation,),
                                    'second-fork', 'user-op', 2, now_ns=102)
        self.assertEqual(second.number, 2)
        self.assertEqual(second.parent_snapshot, first.snapshot)
        self.assertEqual(second.summary, 'next')
        self.assertEqual(self.client.head(first.branch).tip, first.snapshot)
        record = self.client.journal.read('user-op')
        self.assertEqual(record['path'], '/cow/text/append-user')

    def test_completed_retry_recovers_receipt_without_regenerating_a_summary(self):
        from branchwrite.golden_path import SummaryUnavailable
        self.golden.refresh(self.root, 'golden-v1', (self.observation,),
                            'golden-fork', 'ask-a', 2, now_ns=101)
        before = len(self.case.trace)
        with self.assertRaises(SummaryUnavailable) as caught:
            self.golden.refresh(self.root, 'golden-v1', (self.observation,),
                                'golden-fork', 'ask-a', 2, now_ns=101)
        self.assertTrue(caught.exception.result.receipt.snapshot)
        self.assertEqual(len(self.case.trace), before)

    def test_observations_keep_immutable_evidence_identity_and_do_not_claim_validation(self):
        self.assertEqual(self.observation.evidence_bytes, len(self.raw))
        self.assertEqual(self.observation.evidence_id, 'test-run-1')
        # The host supplies the statement; neither hashing nor a model proves it.
        self.assertEqual(self.observation.statement, 'Seven tests passed.')
        for bad in ('', 'x' * 8193):
            with self.assertRaises(ValueError):
                self.Observation.from_bytes('bad', 'run', b'bytes', bad, observed_ns=100)


class GoldenInputAuditTests(unittest.TestCase):
    def test_worker_audit_reads_actual_span_history_and_rejects_wrong_prefix(self):
        from context_time_travel.store import Store
        from validation.run_golden_path_probe import verify_worker_prefix
        with tempfile.TemporaryDirectory() as directory:
            store = Store(directory)
            root = store.create_input_root('audit', [dict(kind='text', tokens=[1, 2, 3])], {})
            child = store.append_inputs(root, [dict(kind='text', tokens=[4, 5])], {})
            wrong = store.create_input_root('audit', [dict(kind='text', tokens=[1, 2, 8, 4, 5])], {})
            self.assertEqual(verify_worker_prefix(store, root, child), 3)
            with self.assertRaises(ValueError):
                verify_worker_prefix(store, root, wrong)

    def test_image_identity_cannot_be_replaced_by_same_shape_and_padding_ids(self):
        from context_time_travel.store import Store
        from validation.run_golden_path_probe import verify_worker_prefix
        span = dict(kind='image', original_sha256='1' * 64, normalized_sha256='2' * 64,
            encoder_profile_id='3' * 64, embedding_sha256='4' * 64, embedding_bytes=28,
            rows=1, width=2, grid_width=1, grid_height=1, pad_token_id=99)
        with tempfile.TemporaryDirectory() as directory:
            store = Store(directory)
            root = store.create_input_root('audit', [span], {})
            swapped = store.create_input_root('audit', [dict(span, original_sha256='5' * 64)], {})
            with self.assertRaises(ValueError):
                verify_worker_prefix(store, root, swapped)


if __name__ == '__main__':
    unittest.main()
