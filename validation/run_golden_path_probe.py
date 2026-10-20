"""Bounded real-Q4 GOLDEN PATH CLI demo; not a thinking or numerical campaign."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def verify_worker_prefix(store, source, worker):
    """Audit canonical inputs including provenance, not projected padding IDs."""
    from context_time_travel.input_spans import history_for_snapshot, history_digest, history_segment
    prefix = history_for_snapshot(store, source)
    result = history_for_snapshot(store, worker)
    if len(result) < len(prefix) or history_digest(history_segment(result, 0, len(prefix))) != history_digest(prefix):
        raise ValueError('worker did not inherit the exact saved canonical input history')
    return len(prefix)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('cow-runtime', 'dependency-root', 'profile', 'h02-result',
                 'cow-test-log', 'bw-test-log', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    runtime = args.cow_runtime.resolve(strict=True)
    sys.path[:0] = list(map(str, (root, runtime, runtime / 'tools', runtime / 'serve',
        runtime / 'experimental/branching_context/src',
        runtime / 'experimental/branching_context/scripts', args.dependency_root)))
    from run_cli_grammar_probe import GrammarProbe, _atomic_json
    from branchwrite.cow_client import CowClient, OperationJournal
    from branchwrite.golden_path import GoldenPath, Observation
    from validation.run_cow_coding_campaign import native_executable_identity

    h02_bytes = args.h02_result.read_bytes()
    h02 = json.loads(h02_bytes)
    if h02['status'] != 'H02_IMAGE_DELIVERY_AND_INTERPRETATION_PASS' or len(h02['cases']) != 3:
        raise ValueError('H02 result did not establish the stated bounded result')
    if not all(row['interpretation'] == 'PASS' for row in h02['cases']):
        raise ValueError('H02 interpretation failure')
    logs = []
    for path, count in ((args.cow_test_log, 32), (args.bw_test_log, 324)):
        raw = path.read_bytes()
        if f'Ran {count} tests'.encode() not in raw or raw.rstrip().splitlines()[-1] != b'OK':
            raise ValueError('required executed test log missing its successful terminal summary')
        logs.append(raw)
    output = args.output.absolute()
    output.mkdir(mode=0o700, exist_ok=False)
    probe = GrammarProbe(SimpleNamespace(runtime_root=runtime, profile=args.profile,
        store=output / 'store', run_dir=output, dependency_root=args.dependency_root,
        ram_gib=96, disk_gib=128))
    probe.record.update(status='RUNNING', scope=__doc__, chat_server='NOT_STARTED',
        numerical_qualification='NOT_RUN', numerical_max_error=None,
        thinking='Disabled; no thinking-budget experiment in this probe',
        limitations=['No automatic whole-project fact harvesting, summary adoption or semantic truth oracle.',
            'No numerical/restart/eviction qualification in this bounded probe.',
            'No thinking_length or unrestricted tool execution.'], generations=[])
    error = None
    try:
        probe._imports()
        profile = json.loads(args.profile.read_bytes())
        probe.runtime_closure(profile, runtime)
        probe.record.update(profile_sha256=sha(args.profile.read_bytes()),
            execution_profile_id=profile['execution_profile_id'], model_contract_id=profile['model_contract_id'],
            native_executable=native_executable_identity(profile),
            branchwrite_source_sha256={str(p.relative_to(root)): sha(p.read_bytes())
                for folder in ('branchwrite', 'tools', 'validation') for p in (root / folder).rglob('*.py')})
        registry = output / 'grammar-registry.json'
        _atomic_json(registry, dict(schema=1, states={
            'GOLDEN_SUMMARY': dict(format='json_schema', source={
                'type': 'object', 'properties': {'summary': {'type': 'string', 'minLength': 1, 'maxLength': 320}},
                'required': ['summary'], 'additionalProperties': False}),
            'GOLDEN_STEER': dict(format='gbnf', source='root ::= "CHECK_RESTART" | "CHECK_THINKING" | "CHECK_BROWSER_ISOLATION"')}))
        probe.tracker = probe.ProgressTracker(output, 'golden-path').start()
        probe.start_service(registry)
        url = probe.ready_url(probe.service.ready)
        pin = sha((probe.record['profile_sha256'] + str(output / 'store')).encode())
        probe.record['endpoint_binding'] = dict(pin=pin, scope='host launch provenance, not HTTP attestation')

        class AuditedClient(CowClient):
            def _generation_mutation(self, *values, **options):
                start = time.perf_counter()
                result = super()._generation_mutation(*values, **options)
                probe.record['generations'].append(dict(operation_id=result.operation_id,
                    wall_seconds=time.perf_counter() - start, answer=dict(result.answer),
                    receipt=dict(result.receipt.raw), source_binding=(None if result.source_binding is None
                        else result.source_binding.to_json())))
                probe.publish()
                return result

        client = AuditedClient.cli(url, runtime / 'tools/cow_cli.py', state_dir=output / 'cli-state',
            journal=OperationJournal(output / 'journal'), api_key=probe.secret, endpoint_pin=pin)
        namespace = client.create_namespace('BranchWrite GOLDEN PATH', 'golden-namespace')['namespace_id']
        golden = GoldenPath(client, namespace, eos_tokens=tuple(profile['execution']['eos_tokens']))
        probe.phase('stable-purpose-prefix')
        stable = golden.start('golden-purpose',
            'Help finish the private BranchWrite/COW prototype. Summarize only host observations '
            'in at most 45 words. Preserve limitations. A summary is a proposal, not a test result.',
            ('A verified command in the pinned environment: python -B -m unittest '
             'tools.test_cow_cli_structured_load -v. Host evidence remains authoritative.',), 'golden-purpose-op')
        now = time.time_ns()
        first_facts = (Observation.from_bytes('h02', 'branchwrite-h02-cli-gpu-v2', h02_bytes,
            'Bounded H02 actual image CLI delivery and interpretation passed three first attempts. '
            'No numerical oracle or thinking sweep ran.', observed_ns=now),)
        probe.phase('summary-version-one')
        first = golden.refresh(stable, 'golden-v1', first_facts, 'golden-v1-fork', 'golden-v1-summary', 192,
                               now_ns=now, settings={'temperature': 0.0}, grammar_state='GOLDEN_SUMMARY')
        json.loads(first.summary)  # Syntax is constrained; this is not a semantic truth oracle.
        second_facts = (
            Observation.from_bytes('structured-cow', 'cow-structured-green-run-v1', logs[0],
                'The explicit structured-message CLI fix passed all 32 affected COW tests.', observed_ns=now),
            Observation.from_bytes('structured-bw', 'branchwrite-structured-full-run-v1', logs[1],
                'The same fix passed all 324 BranchWrite tests. Thinking budgets remain unimplemented.', observed_ns=now))
        probe.phase('summary-version-two')
        second = golden.refresh(first, 'golden-v2', second_facts, 'golden-v2-fork', 'golden-v2-summary', 192,
                                now_ns=now + 1, settings={'temperature': 0.0}, grammar_state='GOLDEN_SUMMARY')
        json.loads(second.summary)
        if client.head(first.branch).tip != first.snapshot:
            raise ValueError('refresh moved the prior version')
        probe.phase('worker-from-specific-prior-summary')
        worker = golden.fork_worker(first, 'golden-worker', 'golden-worker-fork')
        response = client.append_user(worker.name, worker.revision, 'golden-worker-proposal',
            'Choose one proposed next investigation from the allowed choices. This is a proposal; '
            'do not execute any command.', 16, settings={'temperature': 0.0}, grammar_state='GOLDEN_STEER')
        if (response.answer.get('text') not in ('CHECK_RESTART', 'CHECK_THINKING', 'CHECK_BROWSER_ISOLATION')
                or not response.answer.get('tokens')
                or response.answer['tokens'][-1] not in golden.eos_tokens):
            raise ValueError('worker proposal was not a completed legal choice')
        for version in (stable, first, second):
            if client.head(version.branch).tip != version.snapshot:
                raise ValueError('worker changed a retained GOLDEN PATH branch')
        source_cells = verify_worker_prefix(probe.store, first.snapshot, response.receipt.snapshot)
        # These are derived views of canonical histories, not another transcript.
        histories = {v.branch: [dict(row) for row in client.history(v.branch).messages]
                     for v in (stable, first, second)}
        for version, facts in ((first, first_facts), (second, second_facts)):
            prompt = next(row['text'] for row in reversed(histories[version.branch]) if row['role'] == 'user')
            if sha(prompt.encode()) != version.manifest_sha256:
                raise ValueError('manifest reference differs from actual canonical prompt')
            manifest = json.loads(prompt.split('\n', 1)[1])
            if manifest['observations'] != [item.record() for item in sorted(facts, key=lambda item: item.key)]:
                raise ValueError('canonical observations differ from host evidence')
        probe.record.update(status='BOUNDED_GOLDEN_PATH_CLI_Q4_PASS', versions=list(map(asdict, (stable, first, second))),
            histories=histories, worker=dict(head=asdict(worker), answer=dict(response.answer)),
            source_prefix_cells=source_cells, worker_prefix_identity='PASS',
            prior_versions_unchanged='PASS', semantic_summary_truth='HOST_REVIEW_REQUIRED')
    except BaseException as exc:
        error = exc
        probe.record['status'] = 'GOLDEN_PATH_FAIL'
        probe.record.setdefault('failures', []).append(dict(type=type(exc).__name__, message=str(exc)))
    finally:
        if probe.service is not None:
            try:
                probe.stop_service()
            except BaseException as exc:
                error = error or exc
                probe.record['status'] = 'CLEANUP_FAIL'
                probe.record.setdefault('failures', []).append(dict(type=type(exc).__name__, message=str(exc)))
        probe.publish()
        if probe.tracker:
            probe.tracker.finish(probe.record['status'], None if error is None else type(error).__name__)
            probe.tracker.close()
    return 1 if error else 0


if __name__ == '__main__':
    raise SystemExit(main())
