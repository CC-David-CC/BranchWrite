"""Bounded client of PCC's learning API; PCC owns all durable phase state."""
import hashlib
import json
import re
import time


def drive(client, run_id, model_contract_id, *, operation_prefix, lesson_ids=(),
          maximum_transitions=16, maximum_seconds=300, poll_seconds=1):
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}', operation_prefix):
        raise ValueError('Operation prefix must be 1..64 letters, digits, underscores or hyphens, starting with a letter')
    if type(maximum_transitions) is not int or not 1 <= maximum_transitions <= 1000:
        raise ValueError('Maximum transitions must be 1..1000')
    if type(maximum_seconds) is not int or not 1 <= maximum_seconds <= 86400:
        raise ValueError('Maximum client wait must be 1..86400 seconds')
    if type(poll_seconds) not in (int, float) or not .01 <= poll_seconds <= 10:
        raise ValueError('Polling interval must be .01..10 seconds')
    lessons = list(lesson_ids)
    if len(lessons) != len(set(lessons)) or any(
            type(v) is not str or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', v) for v in lessons):
        raise ValueError('Explicit, unique admitted lesson IDs required')
    deadline = time.monotonic() + maximum_seconds
    operations = []
    while True:
        state = client.training_read('learning-runs', run_id)
        if state.get('model_contract_id') != model_contract_id:
            raise ValueError('Learning run belongs to another model contract')
        revision = state.get('revision')
        if type(revision) is not int or revision < 0:
            raise ValueError('Original learning revision is missing or invalid')
        phase = state.get('phase')
        def finish(status):
            return dict(schema=1, kind='bw.learning-drive-observation.v1', status=status,
                run_id=run_id, model_contract_id=model_contract_id, server_status=state,
                submitted_transitions=len(operations), operation_ids=operations,
                cancelled=False, promoted=False)
        if phase == 'round_complete':
            return finish('ROUND_COMPLETE')
        if phase == 'stopped':
            return finish('STOPPED')
        if phase == 'needs_operator':
            return finish('NEEDS_OPERATOR')
        if state.get('policy_available') is not True:
            return finish('POLICY_UNAVAILABLE')
        if phase == 'choosing_lessons' and not lessons:
            return finish('NEEDS_LESSONS')
        if len(operations) >= maximum_transitions:
            return finish('TRANSITION_LIMIT')
        if time.monotonic() >= deadline:
            return finish('WAIT_LIMIT')
        offers = state.get('available_actions')
        if type(offers) is not list or any(type(v) is not dict for v in offers):
            raise ValueError('Original advertised learning actions are invalid')
        available = {v.get('action'): v for v in offers}
        action = None
        extra = {}
        if phase in ('baseline_pending', 'parent_pending', 'candidate_pending', 'report_pending'):
            action = 'advance'
        elif phase == 'choosing_lessons':
            action = 'advance'
            extra['lesson_ids'] = lessons
        elif phase in ('training_pending', 'training'):
            job = state.get('training_job')
            if job is not None and (type(job) is not dict or type(job.get('state')) is not str):
                raise ValueError('Original training job status is malformed')
            if job is None or job.get('state') not in ('queued', 'running'):
                action = 'reconcile'
        elif phase in ('preservation_pending', 'baseline_running', 'parent_running',
                       'candidate_running', 'report_running'):
            if 'reconcile' in available:
                action = 'reconcile'
        else:
            raise ValueError('Unknown learning phase; inspect original status')
        if action is None:
            time.sleep(min(poll_seconds, max(0, deadline-time.monotonic())))
            continue
        if action not in available or set(available[action].get('required_fields', [])) != set(extra):
            return finish('NOT_ACTIONABLE')
        # Same revision and prefix always select the original operation ID.
        # Changed request bytes are rejected by the existing journal, not retried.
        binding = json.dumps([run_id, revision, action], separators=(',', ':')).encode()
        operation = operation_prefix + '-' + hashlib.sha256(binding).hexdigest()[:32]
        body = dict(run_id=run_id, expected_revision=revision, action=action, **extra)
        client.training_submit('learning-steps', body, operation)
        operations.append(operation)
