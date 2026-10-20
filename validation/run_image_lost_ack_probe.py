"""VC06 bounded image lost-ACK test: actual CLI/HTTP/GPU publication, no fake model."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
from types import SimpleNamespace


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def image_answer_outcome(answer, eos_tokens):
    """Keep model quality separate from publication/recovery mechanics.

    Owner accepts the current short-question miss as a documented Q4 model
    edge, not a correct image answer. Always retain that FAIL verdict. The
    protected H02 check is unchanged; no mask removes the wrong legal choices.
    """
    tokens = answer.get('tokens')
    if (answer.get('text') not in ('LEFT', 'RIGHT', 'NOT_VISIBLE')
            or not isinstance(tokens, list) or not tokens or tokens[-1] not in eos_tokens):
        raise ValueError('actual image answer did not complete with a legal label and consumed EOS')
    return dict(expected_host_only='LEFT', actual=answer['text'],
                interpretation='PASS' if answer['text'] == 'LEFT' else 'FAIL', completed=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('cow-runtime', 'dependency-root', 'profile', 'vision-config', 'image', 'question-file', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--expected-image-sha256', required=True)
    parser.add_argument('--expected-question-sha256', required=True)
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    runtime = args.cow_runtime.resolve(strict=True)
    sys.path[:0] = list(map(str, (root, runtime, runtime / 'tools', runtime / 'serve',
        runtime / 'experimental/branching_context/src', runtime / 'experimental/branching_context/scripts',
        args.dependency_root)))
    from run_cli_grammar_probe import GrammarProbe, _atomic_json
    from branchwrite.cow_client import CowClient, OperationJournal, OperationIndeterminate, RequestRejected
    from validation.cow_fault_proxy import LostAckProxy
    from validation.run_cow_coding_campaign import native_executable_identity
    from validation.run_basic_loop_images import verify_capture_delivery
    from context_time_travel.input_spans import history_for_snapshot

    image = args.image.read_bytes()
    if sha(image) != args.expected_image_sha256:
        raise ValueError('actual captured PNG differs from reviewed H02 evidence')
    question = args.question_file.read_text().split('\n', 1)[1].strip()
    if sha(question.encode()) != args.expected_question_sha256:
        raise ValueError('question differs from the executed H02 fixture')
    output = args.output.absolute()
    output.mkdir(mode=0o700, exist_ok=False)

    class ImageOwner(GrammarProbe):
        def _bootstrap(self, registry_path):
            path = super()._bootstrap(registry_path)
            body = path.read_text()
            marker = "sys.argv=['cow-http',*sys.argv[5:]]\n"
            if body.count(marker) != 1:
                raise ValueError('existing bootstrap contract changed')
            body = body.replace(marker, "sys.argv=['cow-http','--vision-config',"
                + repr(str(args.vision_config.resolve(strict=True))) + ",*sys.argv[5:]]\n")
            path.write_text(body, encoding='utf-8', newline='\n')
            return path

    probe = ImageOwner(SimpleNamespace(runtime_root=runtime, profile=args.profile,
        store=output / 'store', run_dir=output, dependency_root=args.dependency_root,
        ram_gib=96, disk_gib=128))
    # Exercise the real launcher edge deterministically. Keep random entropy;
    # never record the credential or let argparse treat it as an option name.
    probe.secret = '-' + probe.secret
    probe.record.update(status='RUNNING', scope=__doc__, chat_server='NOT_STARTED',
        numerical_qualification='NOT_RUN', numerical_max_error=None, leading_dash_credential_exercised=True,
        image_sha256=sha(image), image_bytes=len(image), question=question, question_sha256=sha(question.encode()),
        limitations=['One greedy image answer with one completion deliberately withheld.',
            'Client subprocess recovery; server/native restart, power-loss and broader faults not tested here.',
            'No fresh numerical oracle or thinking-budget qualification.'])
    error = None
    proxy = None
    try:
        probe._imports()
        profile = json.loads(args.profile.read_bytes())
        probe.runtime_closure(profile, runtime)
        probe.record.update(profile_sha256=sha(args.profile.read_bytes()),
            execution_profile_id=profile['execution_profile_id'], model_contract_id=profile['model_contract_id'],
            native_executable=native_executable_identity(profile),
            vision_config_sha256=sha(args.vision_config.read_bytes()),
            branchwrite_source_sha256={str(p.relative_to(root)): sha(p.read_bytes())
                for folder in ('branchwrite', 'tools', 'validation') for p in (root / folder).rglob('*.py')})
        registry = output / 'grammar-registry.json'
        _atomic_json(registry, dict(schema=1, states={'LABEL': dict(format='gbnf',
            source='root ::= "LEFT" | "RIGHT" | "NOT_VISIBLE"')}))
        probe.tracker = probe.ProgressTracker(output, 'image-lost-ack').start()
        probe.start_service(registry)
        proxy = LostAckProxy(probe.ready_url(probe.service.ready), 'lost-image-answer')
        pin = sha((probe.record['profile_sha256'] + str(output / 'store') + proxy.url).encode())
        probe.record['endpoint_binding'] = dict(pin=pin, scope='host-owned fault-proxy launch provenance, not HTTP attestation')
        journal = output / 'journal'
        cli_state = output / 'cli-state'
        client = CowClient.cli(proxy.url, runtime / 'tools/cow_cli.py', state_dir=cli_state,
            journal=OperationJournal(journal), api_key=probe.secret, endpoint_pin=pin)
        namespace = client.create_namespace('Image lost acknowledgment', 'lost-image-namespace')['namespace_id']
        upload = client.upload_image(namespace, image)
        prepared = client.prepare('image', namespace, question, 'lost-image-prepare', images=(upload,))
        _, spans = probe.store.input_lineage(prepared.receipt.snapshot)
        verify_capture_delivery(spans, sha(image))
        payload = prepared.receipt.raw['payload_sha256']
        parent_bytes = (output / 'store/checkpoints' / (payload + '.state')).read_bytes()
        probe.record.update(prepared=dict(prepared.receipt.raw), upload=dict(upload.raw), image_spans=spans,
            parent_checkpoint=dict(bytes=len(parent_bytes), sha256=sha(parent_bytes)))
        probe.phase('lose-completion-after-real-durable-publication')
        try:
            client.answer('image', prepared.receipt.branch.revision, 'lost-image-answer', 16,
                          settings={'temperature': 0.0}, grammar_state='LABEL')
        except OperationIndeterminate as exc:
            probe.record['client_lost_reply'] = dict(type=type(exc).__name__, message=str(exc))
        else:
            raise ValueError('client claimed success without receiving a completion')
        if not proxy.dropped.wait(5):
            raise ValueError('proxy did not observe and withhold the actual complete receipt')
        complete = proxy.dropped_completion
        probe.record['withheld_completion'] = complete
        probe.publish()  # Keep the actual output even if the subsequent quality/control audit fails.
        answer = complete['answer']
        receipt = complete['receipt']
        probe.record['image_answer_outcome'] = image_answer_outcome(answer, profile['execution']['eos_tokens'])
        pending = client.journal.read('lost-image-answer')
        if pending['state'] != 'pending' or pending['source_binding']['snapshot'] != prepared.receipt.snapshot:
            raise ValueError('lost reply did not retain the exact pending source intent')
        if client.head('image').tip != receipt['snapshot']:
            raise ValueError('withheld completion does not describe the durably committed branch')
        history = history_for_snapshot(probe.store, receipt['snapshot'])
        source = history_for_snapshot(probe.store, prepared.receipt.snapshot)
        if answer['counter_deltas']['forward_tokens'] != len(history) - len(source):
            raise ValueError('answer performed unexpected saved-prefix work')
        native_before = probe._trace_bytes()
        probe.phase('retry-unresolved-operation-without-resend')
        try:
            client.answer('image', prepared.receipt.branch.revision, 'lost-image-answer', 16,
                          settings={'temperature': 0.0}, grammar_state='LABEL')
        except OperationIndeterminate:
            pass
        else:
            raise ValueError('unresolved ordinary retry should require explicit reconciliation')
        # A different Python process opens the same pending intent and resolves
        # the original operation through the actual CLI. Secret stays in env.
        recovery_source = '''import json,os,sys
from pathlib import Path
from branchwrite.cow_client import CowClient,OperationJournal
url,cli,state,journal,pin,operation=sys.argv[1:]
client=CowClient.cli(url,cli,state_dir=state,journal=OperationJournal(journal),api_key=os.environ['COW_API_KEY'],endpoint_pin=pin)
observed=client.recover(operation)
replay=client.replay_original(operation)
print(json.dumps(dict(pid=os.getpid(),durable=observed.durable,scope=observed.scope,receipt=dict(observed.receipt.raw),replay_receipt=dict(replay.receipt.raw),source_binding=replay.source_binding.to_json(),transport=replay.transport)))
'''
        script = output / 'recover_client.py'
        script.write_text(recovery_source, encoding='utf-8', newline='\n')
        command = [sys.executable, '-B', str(script), proxy.url, str(runtime / 'tools/cow_cli.py'),
                   str(cli_state), str(journal), pin, 'lost-image-answer']
        probe.phase('new-python-client-recovers-original-operation')
        child = subprocess.Popen(command, env={**os.environ, 'COW_API_KEY': probe.secret},
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        try:
            child_output, child_error = child.communicate(timeout=60)
        except subprocess.TimeoutExpired:
            # This group contains only our new client and its CLI children;
            # the service/native worker have their existing lifecycle owner.
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.communicate()
            raise
        (output / 'recover-client.stdout').write_bytes(child_output)
        (output / 'recover-client.stderr').write_bytes(child_error)
        recovered = json.loads(child_output) if child.returncode == 0 else None
        if (child.returncode != 0 or not recovered['durable']
                or recovered['receipt']['snapshot'] != receipt['snapshot']
                or recovered['replay_receipt'] != recovered['receipt']
                or recovered['source_binding'] != pending['source_binding'] or recovered['pid'] != child.pid):
            raise ValueError('new client failed to reconcile the exact original operation')
        replay = client.answer('image', prepared.receipt.branch.revision, 'lost-image-answer', 16,
                              settings={'temperature': 0.0}, grammar_state='LABEL')
        if replay.receipt.snapshot != receipt['snapshot'] or replay.transport != 'client-journal':
            raise ValueError('completed retry did not return the original saved receipt')
        probe.phase('explicit-http-rejection-control')
        try:
            client.load_context('denied', 'f' * 32, [dict(role='system', content='Valid context.')], 'denied-image-load')
        except RequestRejected:
            pass
        else:
            raise ValueError('missing namespace must reject explicitly')
        native_after = probe._trace_bytes()
        if native_before != native_after:
            raise ValueError('reconciliation/retry/rejection issued unexpected native work')
        if sum(row['operation_id'] == 'lost-image-answer' for row in proxy.requests) != 1:
            raise ValueError('lost answer was dispatched more than once')
        if sha((output / 'store/checkpoints' / (payload + '.state')).read_bytes()) != sha(parent_bytes):
            raise ValueError('answer/recovery mutated the saved prefix bytes')
        if probe.store.head('image').tip != receipt['snapshot']:
            raise ValueError('reconciliation moved the committed branch')
        probe.record.update(status='VC06_BOUNDED_IMAGE_LOST_ACK_CLI_Q4_PASS',
            withheld_completion=complete, recovered_client=recovered, recovery_process_exit=child.returncode,
            recovery_process_absent=not Path('/proc/' + str(recovered['pid'])).exists(),
            recovery_script_sha256=sha(script.read_bytes()), proxy_requests=proxy.requests,
            native_recovery_work=dict(before_bytes=len(native_before), after_bytes=len(native_after),
                before_sha256=sha(native_before), after_sha256=sha(native_after), identical=True, forward_tokens=0),
            original_post_count=1, parent_bytes_unchanged=True,
            source_cells=len(source), answer_forward_tokens=answer['counter_deltas']['forward_tokens'])
    except BaseException as exc:
        error = exc
        probe.record['status'] = 'IMAGE_LOST_ACK_FAIL'
        probe.record.setdefault('failures', []).append(dict(type=type(exc).__name__, message=str(exc)))
    finally:
        if proxy is not None:
            try:
                proxy.close()
            except BaseException as exc:
                error = error or exc
                probe.record['status'] = 'PROXY_CLEANUP_FAIL'
            probe.record['proxy_requests'] = proxy.requests
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
