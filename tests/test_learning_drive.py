"""Thin-client controls and real CowClient journal, using injected wire responses.

Actual native CPU orchestration is qualified separately by S³'s integration suite.
"""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from branchwrite.cow_client import CowClient, OperationJournal, OperationIndeterminate, _Response
from branchwrite.learning_drive import drive


def state(phase, revision=0, **extra):
    actions = []
    if phase in ('baseline_pending', 'candidate_pending', 'report_pending', 'parent_pending'):
        actions = [dict(action='advance', required_fields=[])]
    if phase == 'choosing_lessons':
        actions = [dict(action='advance', required_fields=['lesson_ids'])]
    if phase in ('training', 'training_pending', 'preservation_pending'):
        actions = [dict(action='reconcile', required_fields=[])]
    return dict(schema=1, run_id='owned-run', model_contract_id='a'*64, phase=phase,
        revision=revision, available_actions=actions, policy_available=True, promoted=False, **extra)


class Wire:
    name = 'injected-learning-statuses'
    def __init__(self, states, *, lost=False):
        self.states = iter(states); self.current = None; self.posts = []; self.receipts = {}; self.lost=lost
    def request(self, method, path, body=None, **kwargs):
        if method == 'GET' and path.startswith('/cow/training/operations/'):
            return _Response(json_value=self.receipts[path.rsplit('/',1)[1]], transport=self.name)
        if method == 'GET':
            self.current = next(self.states, self.current)
            return _Response(json_value=self.current, transport=self.name)
        assert path == '/cow/training/learning-steps'
        value=json.loads(body);self.posts.append(value)
        digest=hashlib.sha256(json.dumps([path,value],sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
        receipt=dict(schema=1,operation_id=value['operation_id'],request_sha256=digest,
            run_id=value['run_id'],step_id=value['operation_id'])
        self.receipts[value['operation_id']]=receipt
        if self.lost:
            self.lost=False
            raise OperationIndeterminate('Injected lost response after acceptance')
        return _Response(json_value=receipt,transport=self.name)


class LearningDrive(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
    def run_drive(self, wire, **kwargs):
        client=CowClient(wire,journal=OperationJournal(self.root/'journal'),endpoint_url='http://127.0.0.1:1')
        return drive(client,'owned-run','a'*64,operation_prefix='owned-driver',**kwargs)
    def test_stops_at_owner_lesson_selection_without_post(self):
        wire=Wire([state('choosing_lessons')]);result=self.run_drive(wire)
        self.assertEqual(result['status'],'NEEDS_LESSONS');self.assertEqual(wire.posts,[])
    def test_one_round_follows_advertised_steps_and_never_starts_next_round(self):
        wire=Wire([state('baseline_pending'),state('choosing_lessons',2),
            state('training',3,training_job=dict(state='complete')),state('candidate_pending',4),
            state('report_pending',6),state('round_complete',8)])
        result=self.run_drive(wire,lesson_ids=['b'*64])
        self.assertEqual(result['status'],'ROUND_COMPLETE');self.assertEqual(len(wire.posts),5)
        self.assertEqual([r['action']for r in wire.posts],['advance','advance','reconcile','advance','advance'])
        self.assertEqual(wire.posts[1]['lesson_ids'],['b'*64])
        self.assertEqual(len(set(result['operation_ids'])),5)
    def test_running_job_waits_without_training_or_reconciliation_posts(self):
        wire=Wire([state('training',1,training_job=dict(state='running')),state('round_complete',2)])
        with patch('branchwrite.learning_drive.time.sleep'):
            result=self.run_drive(wire)
        self.assertEqual(result['status'],'ROUND_COMPLETE');self.assertEqual(wire.posts,[])
    def test_expired_client_wait_does_not_cancel_or_restart(self):
        wire=Wire([state('training',1,training_job=dict(state='running'))])
        with patch('branchwrite.learning_drive.time.monotonic',side_effect=[0,2]):
            result=self.run_drive(wire,maximum_seconds=1)
        self.assertEqual(result['status'],'WAIT_LIMIT');self.assertFalse(result['cancelled']);self.assertEqual(wire.posts,[])
    def test_limit_leaves_server_authoritative(self):
        wire=Wire([state('baseline_pending'),state('candidate_pending',2)])
        result=self.run_drive(wire,maximum_transitions=1)
        self.assertEqual(result['status'],'TRANSITION_LIMIT');self.assertEqual(result['server_status']['revision'],2)
        self.assertEqual(len(wire.posts),1)
    def test_operator_and_stopped_and_missing_policy_do_not_mutate(self):
        for phase in ('needs_operator','stopped','baseline_pending'):
            with self.subTest(phase=phase):
                value=state(phase);value['policy_available']=False
                wire=Wire([value]);result=self.run_drive(wire)
                self.assertIn(result['status'],('NEEDS_OPERATOR','STOPPED','POLICY_UNAVAILABLE'));self.assertEqual(wire.posts,[])
    def test_missing_offer_or_extra_required_fields_cannot_be_guessed(self):
        for actions in ([],[dict(action='advance',required_fields=['new_owner_input'])]):
            value=state('baseline_pending');value['available_actions']=actions
            wire=Wire([value]);self.assertEqual(self.run_drive(wire)['status'],'NOT_ACTIONABLE');self.assertEqual(wire.posts,[])
    def test_original_lost_acceptance_is_reconciled_without_second_post(self):
        wire=Wire([state('baseline_pending'),state('choosing_lessons',2)],lost=True)
        self.assertEqual(self.run_drive(wire)['status'],'NEEDS_LESSONS');self.assertEqual(len(wire.posts),1)
        # Same original revision, request, journal: observe original acceptance.
        wire.states=iter([state('baseline_pending'),state('choosing_lessons',2)])
        self.assertEqual(self.run_drive(wire)['status'],'NEEDS_LESSONS');self.assertEqual(len(wire.posts),1)
    def test_unknown_phase_or_model_cannot_trigger_a_transition(self):
        for value in (state('mystery_running'),dict(state('baseline_pending'),model_contract_id='c'*64)):
            wire=Wire([value])
            with self.assertRaises((ValueError,RuntimeError)):
                self.run_drive(wire)
            self.assertEqual(wire.posts,[])
    def test_changed_lessons_reuse_same_revision_intent_and_are_refused(self):
        wire=Wire([state('choosing_lessons'),state('round_complete',2)])
        self.run_drive(wire,lesson_ids=['b'*64])
        wire.states=iter([state('choosing_lessons')])
        with self.assertRaises(RuntimeError):self.run_drive(wire,lesson_ids=['c'*64])
        self.assertEqual(len(wire.posts),1)
    def test_invalid_bounds_and_duplicate_lessons_fail_before_network(self):
        for extra in (dict(maximum_transitions=0),dict(maximum_seconds=0),dict(lesson_ids=['x','x'])):
            wire=Wire([])
            with self.assertRaises(ValueError):self.run_drive(wire,**extra)
            self.assertEqual(wire.posts,[])


if __name__=='__main__':unittest.main()
