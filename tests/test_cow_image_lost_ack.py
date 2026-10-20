"""Actual CLI/socket/store failure boundary; CPU model is not GPU evidence."""
import os
import json
from pathlib import Path
import unittest

from branchwrite.cow_client import CowClient, CliTransport, OperationIndeterminate, OperationJournal, RequestRejected
from validation.cow_fault_proxy import LostAckProxy


class ImageLostAckTests(unittest.TestCase):
    def setUp(self):
        from serve.test_cow_vision_http import CowVisionHTTPTests
        self.case = CowVisionHTTPTests()
        self.addCleanup(self.case.doCleanups)
        self.case.setUp()
        self.proxy = LostAckProxy('http://127.0.0.1:' + str(self.case.server.server_port), 'lost-answer')
        self.addCleanup(self.proxy.close)
        cli = os.environ['COW_CLI_SCRIPT']
        root = Path(self.case.flow.temp.name)
        self.client = CowClient.cli(self.proxy.url, cli, state_dir=root / 'cli-state',
            journal=OperationJournal(root / 'bw-journal'), api_key='secret', endpoint_pin='lost-ack-cpu')

    def test_committed_image_answer_lost_reply_is_indeterminate_then_recovers_without_work(self):
        flow = self.case.flow
        image = self.client.upload_image(flow.namespace, self.case.raw)
        prepared = self.client.prepare('lost-image', flow.namespace, 'Inspect.', 'lost-prepare', images=(image,))
        with self.assertRaises(OperationIndeterminate):
            self.client.answer('lost-image', prepared.receipt.branch.revision, 'lost-answer', 2)
        self.assertTrue(self.proxy.dropped.wait(2))
        dropped = self.proxy.dropped_completion
        self.assertIsNotNone(dropped['receipt'])
        self.assertEqual(self.client.journal.read('lost-answer')['state'], 'pending')
        source_binding = self.client.journal.read('lost-answer')['source_binding']
        self.assertEqual(source_binding['snapshot'], prepared.receipt.snapshot)
        self.assertEqual(self.client.head('lost-image').tip, dropped['receipt']['snapshot'])
        before = dict(flow.models[-1].backend.stats)
        # An unresolved ordinary retry must not dispatch anything.
        with self.assertRaises(OperationIndeterminate):
            self.client.answer('lost-image', prepared.receipt.branch.revision, 'lost-answer', 2)
        recovered = self.client.recover('lost-answer')
        self.assertTrue(recovered.durable)
        self.assertEqual(recovered.receipt.snapshot, dropped['receipt']['snapshot'])
        replay = self.client.replay_original('lost-answer')
        self.assertEqual(replay.receipt.snapshot, recovered.receipt.snapshot)
        self.assertEqual(dict(flow.models[-1].backend.stats), before)
        self.assertEqual(sum(row['operation_id'] == 'lost-answer' for row in self.proxy.requests), 1)
        self.assertEqual(self.client.journal.read('lost-answer')['state'], 'complete')

    def test_explicit_http_rejection_still_has_a_successful_protocol_control(self):
        before = dict(self.case.flow.models[-1].backend.stats)
        with self.assertRaises(RequestRejected):
            self.client.load_context('denied', 'f' * 32,
                [dict(role='system', content='Valid text, missing namespace.')], 'denied-load')
        self.assertEqual(dict(self.case.flow.models[-1].backend.stats), before)

    def test_unknown_legacy_cli_exit_two_cannot_prove_rejection(self):
        path = Path(self.case.flow.temp.name) / 'legacy_cli.py'
        path.write_text('import sys\nprint("ambiguous failure", file=sys.stderr)\nraise SystemExit(2)\n')
        transport = CliTransport(self.proxy.url, path, state_dir=Path(self.case.flow.temp.name) / 'legacy-state')
        with self.assertRaises(OperationIndeterminate):
            transport._run('ask', ['--operation-id', 'legacy-op'], mutation=True, streamed=True)
        self.assertEqual(self.proxy.requests, [])

    def test_malformed_or_other_operation_error_frames_remain_indeterminate(self):
        path = Path(self.case.flow.temp.name) / 'bad_machine_error.py'
        transport = CliTransport(self.proxy.url, path, state_dir=Path(self.case.flow.temp.name) / 'bad-frame-state')
        valid = dict(schema=1, error=dict(outcome='rejected', operation_id='bound-op', message='denied'))
        frames = [dict(schema=1, error=dict(outcome='rejected', message='missing operation field')),
                  dict(valid, error=dict(valid['error'], operation_id='other-operation')),
                  dict(valid, error=dict(valid['error'], unknown_field=True)), dict(valid, schema=True)]
        for frame in frames:
            with self.subTest(frame=frame):
                path.write_text('print(' + repr(json.dumps(frame)) + ')\nraise SystemExit(2)\n')
                with self.assertRaises(OperationIndeterminate):
                    transport._run('ask', ['--operation-id', 'bound-op'], mutation=True, streamed=True)
        self.assertEqual(self.proxy.requests, [])

    def test_wrong_legal_image_answer_stays_a_quality_failure_even_when_recovery_can_be_checked(self):
        from validation.run_image_lost_ack_probe import image_answer_outcome
        correct = image_answer_outcome(dict(text='LEFT', tokens=[10, 299]), [299])
        self.assertEqual(correct['interpretation'], 'PASS')
        wrong = image_answer_outcome(dict(text='NOT_VISIBLE', tokens=[11, 299]), [299])
        self.assertEqual(wrong['interpretation'], 'FAIL')
        self.assertEqual(wrong['expected_host_only'], 'LEFT')
        for incomplete in (dict(text='LEFT', tokens=[]), dict(text='LEFT', tokens=[10]),
                           dict(text='UNKNOWN', tokens=[299])):
            with self.assertRaises(ValueError):
                image_answer_outcome(incomplete, [299])


if __name__ == '__main__':
    unittest.main()
