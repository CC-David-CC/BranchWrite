"""H04/H05/H06: thinking edit -> actual tool -> new render -> image-only observation.

Bounded CLI/HTTP/GPU pilot, not the complete workflow interpreter or VC/G gate.
Protected checks run only in the isolated browser, never in model inputs.
"""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import tomllib
from types import SimpleNamespace

from validation.run_basic_loop_html import (checked_pack, image_probe_type, observer_prompt,
                                           parse_visual_report, visual_report_schema)
from branchwrite.cow_actions import (DEFAULT_THINKING_TOKENS, completed_thinking_text,
                                    parse_replacement, replacement_schema)
from branchwrite.execution import Executor, Grant


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def verified_predecessor(source, result_path, target):
    """Bind an ordered target to real bytes from its settled previous result."""
    raw = Path(result_path).read_bytes()
    prior = json.loads(raw)
    expected = {'H06': 'H05'}.get(target)
    after = prior.get('after', {})
    capture = after.get('capture', {})
    actual = (Path(source)/'index.html').read_bytes()
    if (expected is None or prior.get('target') != expected
            or prior.get('status') != expected+'_EDIT_RENDER_OBSERVE_PASS'
            or prior.get('observer_quality') != 'PASS'
            or prior.get('source_unchanged_after_observation') is not True
            or after.get('cli_exit') != 0 or after.get('cli_absent') is not True
            or capture.get('inspection_status') != 'PASS'
            or capture.get('source_sha256') != sha(actual)):
        raise ValueError('predecessor is unverified, unsettled or has changed bytes')
    return dict(target=expected, source=str(Path(source).resolve()), source_sha256=sha(actual),
                result_path=str(Path(result_path).resolve()), result_sha256=sha(raw))


def capture_revision(root, executor, output, label, args, pack, inventory):
    source = executor.workspace / 'index.html'
    actual = source.read_bytes()
    folder = output / label
    command = [sys.executable, '-B', str(root/'tools/capture_page.py'), '--source', str(executor.workspace),
        '--entry', 'index.html', '--expected-sha256', sha(actual), '--browser', str(args.browser),
        '--output', str(folder), '--check-module', str(pack/'protected/checks.py'),
        '--check-sha256', inventory['protected/checks.py'], '--check-target', args.target]
    process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, close_fds=True, start_new_session=True)
    stdout, stderr, timed_out, limited, _ = Executor._capture(process, time.monotonic()+45, 2*1024**2)
    (output/(label+'.stdout')).write_bytes(stdout)
    (output/(label+'.stderr')).write_bytes(stderr)
    if timed_out or limited or process.returncode not in (0, 1):
        raise ValueError('capture CLI failed; retain raw outcome')
    result = tomllib.loads(stdout.decode())
    image = (folder/'capture.png').read_bytes()
    if (result['source_sha256'] != sha(actual) or result['served_sha256'] != sha(actual)
            or result['image_sha256'] != sha(image) or not result['isolation_namespace_empty']
            or not result['chromium_sandbox'] or not result['isolation_worker_exited']
            or result['inspection_sha256'] != inventory['protected/checks.py']
            or (process.returncode == 0) != (result['inspection_status'] == 'PASS')
            or source.read_bytes() != actual):
        raise ValueError('capture/check does not bind this unchanged source and image')
    return dict(capture=result, cli_exit=process.returncode, cli_pid=process.pid,
                cli_absent=not (Path('/proc')/str(process.pid)).exists()), image


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('cow-runtime', 'dependency-root', 'profile', 'vision-config', 'pack', 'browser', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--target', choices=('H04', 'H05', 'H06'), required=True)
    parser.add_argument('--source', type=Path, help='Verified predecessor workspace for ordered progression')
    parser.add_argument('--predecessor-result', type=Path)
    args = parser.parse_args(argv)
    if args.target == 'H06' and (args.source is None or args.predecessor_result is None):
        parser.error('H06 requires source and predecessor-result; no fixture reset')
    if args.target != 'H06' and (args.source is not None or args.predecessor_result is not None):
        parser.error('predecessor progression is not defined for this target')
    root = Path(__file__).resolve().parents[1]
    runtime = args.cow_runtime.resolve(strict=True)
    sys.path[:0] = [str(p) for p in (root, runtime, runtime/'tools',
        runtime/'experimental/branching_context/src', runtime/'experimental/branching_context/scripts',
        args.dependency_root)]
    from run_cli_grammar_probe import GrammarProbe, _atomic_json
    from branchwrite.cow_client import CowClient, OperationJournal
    from validation.run_basic_loop_images import verify_capture_delivery
    from validation.run_cow_coding_campaign import native_executable_identity

    pack, inventory = checked_pack(args.pack)
    task = (pack/('tasks/'+args.target+'.md')).read_text().split('\n',1)[1].strip()
    output = args.output.absolute()
    output.mkdir(mode=0o700, exist_ok=False)
    owner = image_probe_type(GrammarProbe, args.vision_config)
    probe = owner(SimpleNamespace(runtime_root=runtime, profile=args.profile, store=output/'store',
        run_dir=output, dependency_root=args.dependency_root, ram_gib=96, disk_gib=2))
    probe.record.update(status='RUNNING', target=args.target, numerical_max_error=None,
        numerical_oracle='NOT_RUN', scope=__doc__, cases=[], thinking_budget=DEFAULT_THINKING_TOKENS,
        requested_model_stages=0, automatic_repairs=0, chat_server='NOT_STARTED', q8='DEFERRED_BY_OWNER')
    error = None
    try:
        probe._imports()
        profile = json.loads(args.profile.read_bytes())
        if profile['execution']['text_template_kwargs'] != {'enable_thinking': True}:
            raise ValueError('thinking rendering profile required')
        probe.runtime_closure(profile, runtime)
        probe.record.update(execution_profile_id=profile['execution_profile_id'],
            model_contract_id=profile['model_contract_id'], profile_sha256=sha(args.profile.read_bytes()),
            native_executable=native_executable_identity(profile),
            branchwrite_source_sha256={str(p.relative_to(root)): sha(p.read_bytes()) for folder in
                ('branchwrite','tools','validation') for p in (root/folder).rglob('*.py')},
            pack_manifest_sha256=sha((pack/'FILES.sha256').read_bytes()))
        registry = output/'registry.json'
        def thinking(schema):
            return dict(format='thinking', source=dict(schema=1, max_tokens=DEFAULT_THINKING_TOKENS,
                        final=dict(format='json_schema', source=schema)))
        _atomic_json(registry, dict(schema=1, states=dict(
            BW_EDIT=thinking(replacement_schema('index.html')), BW_OBSERVE=thinking(visual_report_schema()))))
        probe.tracker = probe.ProgressTracker(output, 'basic-loop-'+args.target).start()
        probe.start_service(registry)
        client = CowClient.cli(probe.ready_url(probe.service.ready), runtime/'tools/cow_cli.py',
            state_dir=output/'cli-state', journal=OperationJournal(output/'journal'), api_key=probe.secret,
            endpoint_pin=sha((str(output/'store')+probe.record['profile_sha256']).encode()))
        source = args.source if args.source is not None else pack/('fixtures/starter/'+args.target)
        if args.source is not None:
            probe.record['predecessor'] = verified_predecessor(source, args.predecessor_result, args.target)
        executor = Executor.create(source, output/'tool')
        grant = Grant(('index.html',), False, read_paths=('index.html',))
        original = executor.read_file('read-before', grant, 'index.html').stdout.read_bytes()
        probe.phase('capture-before-edit')
        before, before_image = capture_revision(root, executor, output, 'before', args, pack, inventory)
        probe.record['before'] = before
        probe.publish()

        def observe(image, label):
            probe.phase(label+'-image-only-observer')
            namespace = client.create_namespace('Visual observation', label+'-namespace')['namespace_id']
            upload = client.upload_image(namespace, image)
            question = observer_prompt(example=True)
            prepared = client.prepare(label, namespace, question, label+'-prepare', images=(upload,))
            _, spans = probe.store.input_lineage(prepared.receipt.snapshot)
            verify_capture_delivery(spans, sha(image))
            started = time.monotonic()
            probe.record['requested_model_stages'] += 1
            answer = client.answer(label, prepared.receipt.branch.revision, label+'-answer', 2048,
                settings=dict(temperature=0.), grammar_state='BW_OBSERVE')
            row = dict(answer=dict(answer.answer), receipt=dict(answer.receipt.raw),
                prepared=dict(prepared.receipt.raw), upload=dict(upload.raw), image_spans=spans,
                question_sha256=sha(question.encode()), elapsed_seconds=time.monotonic()-started)
            probe.record[label] = row
            probe.publish()
            text = completed_thinking_text(answer, profile['execution']['eos_tokens'])
            row['report'] = parse_visual_report(text)
            probe.publish()
            return row['report']

        prior_report = observe(before_image, 'prior') if args.target == 'H05' else None
        if prior_report is not None:
            expected_prior = dict(heading='Loop Lab', square_count=2, color='blue', arrangement='vertical')
            probe.record.update(prior_expected_host_only=expected_prior,
                                prior_observer_quality='PASS' if prior_report==expected_prior else 'FAIL')
            probe.publish()
            if prior_report != expected_prior:
                raise ValueError('initial image observation failed; retain outcome before editing')
        prompt = ('Propose one exact text replacement in the host-authorized index.html file. '
            'The host will validate the source hash and apply only your exact before/after strings. '
            'Return one JSON object with tool "replace" and arguments path, before, after. '
            'Preserve unrelated bytes. Do not use a shell or choose another file.\nTask: '+task+
            '\nActual file readback (UTF-8):\n'+original.decode('utf8'))
        if prior_report is not None:
            prompt += '\nIndependent screenshot observation: '+json.dumps(prior_report)
        (output/'edit-prompt.txt').write_text(prompt, newline='\n')
        namespace = client.create_namespace('Edit '+args.target, 'edit-namespace')['namespace_id']
        prepared = client.prepare('edit', namespace, prompt, 'edit-prepare')
        probe.phase('model-propose-edit')
        probe.record['requested_model_stages'] += 1
        started = time.monotonic()
        answer = client.answer('edit', prepared.receipt.branch.revision, 'edit-answer', 2048,
            settings=dict(temperature=0.), grammar_state='BW_EDIT')
        probe.record['edit'] = dict(answer=dict(answer.answer), receipt=dict(answer.receipt.raw),
            prepared=dict(prepared.receipt.raw), elapsed_seconds=time.monotonic()-started,
            prompt_sha256=sha(prompt.encode()), before_source_sha256=sha(original))
        probe.publish()
        text = completed_thinking_text(answer, profile['execution']['eos_tokens'])
        before_text, after_text = parse_replacement(text, 'index.html')
        probe.phase('grant-checked-exact-edit-and-readback')
        applied = executor.replace('apply-edit', grant, 'index.html', sha(original), before_text, after_text)
        actual = executor.read_file('read-after', grant, 'index.html').stdout.read_bytes()
        if applied.disposition != 'applied' or actual != original.replace(before_text, after_text, 1):
            raise ValueError('tool edit/readback does not match the approved proposal')
        probe.record['edit'].update(tool_result=asdict(applied), after_source_sha256=sha(actual),
            readback_bytes=len(actual), preimage_occurrences=original.count(before_text))
        # Path objects in tool artifacts are evidence references, rendered as strings.
        probe.record['edit']['tool_result'] = json.loads(json.dumps(probe.record['edit']['tool_result'], default=str))
        probe.publish()
        probe.phase('capture-edited-revision')
        after, image = capture_revision(root, executor, output, 'after', args, pack, inventory)
        probe.record['after'] = after
        if after['capture']['source_sha256'] == before['capture']['source_sha256'] or sha(image) == sha(before_image):
            raise ValueError('edit must produce a new source and screenshot')
        report = observe(image, 'observed')
        expected = dict(heading='Loop Lab', square_count=1 if args.target=='H04' else 2,
            color='green' if args.target=='H04' else 'blue',
            arrangement='single' if args.target=='H04' else 'horizontal')
        probe.record.update(expected_host_only=expected, observer_quality='PASS' if report==expected else 'FAIL',
            immutable_input_unchanged=(source/'index.html').read_bytes()==original,
            source_unchanged_after_observation=(executor.workspace/'index.html').read_bytes()==actual)
        if (after['capture']['inspection_status'] != 'PASS' or report != expected
                or not probe.record['immutable_input_unchanged'] or not probe.record['source_unchanged_after_observation']):
            raise ValueError('protected edit target or independent observation failed; retain outcome')
        if args.target == 'H06':
            actions = json.loads(after['capture']['inspection_actions_json'])
            if actions != [['click','increment'],['click','increment']]:
                raise ValueError('H06 requires two real checked counter interactions')
            probe.record['verified_browser_actions'] = actions
        probe.record['status'] = args.target+'_EDIT_RENDER_OBSERVE_PASS'
    except BaseException as exc:
        error = exc
        probe.record['status'] = args.target+'_FAIL'
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
