"""One explicit new observation of an already created/checked H03 screenshot.

No file action or writer generation is repeated. The original failed report and
its immutable evidence remain. This attempt adds one independent category
example; the schema, expected answers, model and execution profile stay fixed.
"""
import argparse
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import tomllib
import uuid

from validation.run_basic_loop_html import (checked_pack, image_probe_type, observer_prompt,
                                           parse_visual_report, sha, visual_report_schema)


def retained_capture(previous, inspector_sha256):
    result_path = previous / 'result.json'
    result = json.loads(result_path.read_bytes())
    if (result.get('target') != 'H03' or result.get('status') != 'H03_TASK_FAIL_OUTCOME_RETAINED'
            or result.get('writer', {}).get('status') != 'FILE_CREATED_AND_READ'
            or result.get('observer', {}).get('quality') != 'FAIL'):
        raise ValueError('observer retry requires the retained failed H03 report')
    capture = result['capture']
    if (capture['inspection_status'] != 'PASS' or capture['inspection_sha256'] != inspector_sha256
            or not capture['isolation_namespace_empty'] or not capture['isolation_worker_exited']
            or not capture['chromium_sandbox']):
        raise ValueError('prior page was not qualified by the selected protected checker')
    if tomllib.loads((previous / 'capture/capture.toml').read_text()) != capture:
        raise ValueError('prior capture receipt changed')
    source = (previous / 'writer/tool/workspace/index.html').read_bytes()
    image = (previous / 'capture/capture.png').read_bytes()
    if (source != (previous / 'writer/readback.bin').read_bytes()
            or sha(source) != capture['source_sha256'] or sha(source) != capture['served_sha256']
            or sha(source) != result['writer']['created_sha256'] or sha(image) != capture['image_sha256']):
        raise ValueError('retained source/image binding changed')
    return result, image, dict(result_sha256=sha(result_path.read_bytes()),
        source_sha256=sha(source), image_sha256=sha(image), inspector_sha256=inspector_sha256,
        original_report=result['observer']['report'], original_quality='FAIL')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('cow-runtime', 'dependency-root', 'profile', 'vision-config', 'pack', 'previous', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    runtime = args.cow_runtime.resolve(strict=True)
    sys.path[:0] = [str(p) for p in (root, runtime, runtime / 'tools',
        runtime / 'experimental/branching_context/src', runtime / 'experimental/branching_context/scripts',
        args.dependency_root)]
    from run_cli_grammar_probe import GrammarProbe, _atomic_json
    from branchwrite.cow_client import CowClient, OperationJournal
    from validation.run_basic_loop_images import verify_capture_delivery
    from validation.run_cow_coding_campaign import native_executable_identity
    _, inventory = checked_pack(args.pack)
    old, image, binding = retained_capture(args.previous.resolve(strict=True), inventory['protected/checks.py'])
    profile = json.loads(args.profile.read_bytes())
    if (profile['execution_profile_id'] != old['execution_profile_id']
            or profile['model_contract_id'] != old['model_contract_id']):
        raise ValueError('observer experiment must retain the original model/profile')
    output = args.output.absolute()
    output.mkdir(mode=0o700, exist_ok=False)
    ImageOwner = image_probe_type(GrammarProbe, args.vision_config)
    probe = ImageOwner(SimpleNamespace(runtime_root=runtime, profile=args.profile,
        store=output / 'store', run_dir=output, dependency_root=args.dependency_root, ram_gib=96, disk_gib=128))
    probe.record.update(status='RUNNING', target='H03_OBSERVER_RETRY', scope=__doc__,
        prior=binding, writer_generations=0, file_actions=0, numerical_max_error=None,
        question=observer_prompt(example=True), question_sha256=sha(observer_prompt(example=True).encode()),
        chat_server='NOT_STARTED', q8='DEFERRED')
    error = None
    try:
        probe._imports()
        probe.runtime_closure(profile, runtime)
        probe.record.update(execution_profile_id=profile['execution_profile_id'],
            model_contract_id=profile['model_contract_id'], native_executable=native_executable_identity(profile),
            branchwrite_source_sha256={str(p.relative_to(root)): sha(p.read_bytes()) for folder in
                ('branchwrite', 'tools', 'validation') for p in (root / folder).rglob('*.py')})
        registry = output / 'registry.json'
        # The same definition as the failed observer; no legal wrong answer is
        # removed. Only the explicit new question/example changes.
        old_registry = json.loads((args.previous / 'registry.json').read_bytes())
        if old_registry['states']['BW_IMAGE_REPORT'] != dict(format='json_schema', source=visual_report_schema()):
            raise ValueError('observer schema changed from the failed attempt')
        _atomic_json(registry, old_registry)
        probe.tracker = probe.ProgressTracker(output, 'H03-observer-retry').start()
        probe.start_service(registry)
        pin = sha((str(output) + profile['execution_profile_id']).encode())
        client = CowClient.cli(probe.ready_url(probe.service.ready), runtime / 'tools/cow_cli.py',
            state_dir=output / 'cli-state', journal=OperationJournal(output / 'journal'),
            api_key=probe.secret, endpoint_pin=pin)
        key = 'h03-observer-retry-' + uuid.uuid4().hex
        namespace = client.create_namespace('Visual observation', key + '-namespace')['namespace_id']
        upload = client.upload_image(namespace, image)
        probe.phase('new-observer-question-with-one-independent-example')
        prepared = client.prepare(key, namespace, observer_prompt(example=True), key + '-prepare', images=(upload,))
        _, spans = probe.store.input_lineage(prepared.receipt.snapshot)
        verify_capture_delivery(spans, sha(image))
        answer = client.answer(key, prepared.receipt.branch.revision, key + '-answer', 128,
            settings=dict(temperature=0.), grammar_state='BW_IMAGE_REPORT')
        tokens = answer.answer.get('tokens', [])
        if not tokens or tokens[-1] not in profile['execution']['eos_tokens']:
            raise ValueError('observer did not finish with a consumed EOS')
        report = parse_visual_report(answer.answer['text'])
        expected = old['observer']['expected_host_only']
        # Recheck retained inputs after the model call too. Never adopt a result
        # against a source that changed during this observation.
        _, _, after = retained_capture(args.previous, inventory['protected/checks.py'])
        if after != binding:
            raise ValueError('prior evidence changed during the observation')
        quality = 'PASS' if report == expected else 'FAIL'
        probe.record.update(report=report, expected_host_only=expected, quality=quality,
            answer=dict(answer.answer), receipt=dict(answer.receipt.raw), upload=dict(upload.raw),
            prepared=dict(prepared.receipt.raw), image_spans=spans,
            status='H03_OBSERVER_RETRY_PASS' if quality == 'PASS' else 'H03_OBSERVER_RETRY_FAIL')
        if quality != 'PASS':
            error = ValueError('observer example did not fix the report; retain outcome')
    except BaseException as exc:
        error = exc
        probe.record['status'] = 'H03_OBSERVER_RETRY_ERROR'
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
