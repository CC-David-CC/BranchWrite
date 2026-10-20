"""H03: actual model create/read -> isolated capture/check -> image-only observer.

The supplied protected assertions run on our existing capture's live page.
They never enter the writer/observer context. This is a bounded pilot, not the
complete BranchWrite interpreter. A failed model attempt is retained, not repaired.
"""
import argparse
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import tomllib


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def observer_prompt(*, example=False):
    prompt = ('Inspect only the attached screenshot. Report the visible heading, number of squares, '
            'their main color, and whether their arrangement is single, horizontal, vertical, other or none. '
            'Do not infer from filenames or task descriptions.')
    if example:
        prompt += ('\nCategory guide: none means zero squares; single means exactly one square. '
                   'Horizontal, vertical and other arrangements refer to two or more squares. '
                   'Independent example, not this screenshot: a page headed Demo with one red square '
                   'has heading Demo, square_count 1, color red, arrangement single. '
                   'Inspect the actual screenshot; do not copy the example.')
    return prompt


def visual_report_schema():
    return dict(type='object', properties=dict(
        heading=dict(type='string', maxLength=80), square_count=dict(type='integer', minimum=0, maximum=16),
        color=dict(type='string', enum=['blue', 'green', 'red', 'other', 'none']),
        arrangement=dict(type='string', enum=['single', 'horizontal', 'vertical', 'other', 'none'])),
        required=['heading', 'square_count', 'color', 'arrangement'], additionalProperties=False)


def parse_visual_report(text):
    if not isinstance(text, str) or len(text.encode('utf8')) > 8192:
        raise ValueError('visual report must be bounded text')
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError('duplicate visual report field')
            value[key] = item
        return value
    value = json.loads(text, object_pairs_hook=unique)
    if (type(value) is not dict or set(value) != {'heading', 'square_count', 'color', 'arrangement'}
            or type(value['heading']) is not str or len(value['heading']) > 80
            or type(value['square_count']) is not int or not 0 <= value['square_count'] <= 16
            or value['color'] not in ('blue', 'green', 'red', 'other', 'none')
            or value['arrangement'] not in ('single', 'horizontal', 'vertical', 'other', 'none')):
        raise ValueError('visual report violates its host output contract')
    return value


def checked_pack(path):
    pack = path.resolve(strict=True)
    manifest = pack / 'FILES.sha256'
    if sha(manifest.read_bytes()) != '12a60740aeb1eee5f6cc23071bb54583f94f5cb633f574e355d6f39e0c0631a3':
        raise ValueError('unreviewed basic-loop workload')
    expected = {}
    for row in manifest.read_text().splitlines():
        digest, name = row.split('  ', 1)
        item = pack / name
        if (name in expected or item.is_symlink() or not item.resolve(strict=True).is_relative_to(pack)
                or sha(item.read_bytes()) != digest):
            raise ValueError('workload changed or escaped the reviewed pack')
        expected[name] = digest
    if {p.relative_to(pack).as_posix() for p in pack.rglob('*') if p.is_file()} != set(expected) | {'FILES.sha256'}:
        raise ValueError('workload inventory changed')
    return pack, expected


def image_probe_type(base, vision_config):
    """Keep one image-service fixture for the original run and observer retry."""
    class ImageOwner(base):
        def _bootstrap(self, registry_path):
            path = super()._bootstrap(registry_path)
            body = path.read_text()
            marker = "sys.argv=['cow-http',*sys.argv[5:]]\n"
            if body.count(marker) != 1:
                raise ValueError('service bootstrap contract changed')
            path.write_text(body.replace(marker, "sys.argv=['cow-http','--vision-config'," +
                repr(str(vision_config.resolve(strict=True))) + ",*sys.argv[5:]]\n"), newline='\n')
            return path
    return ImageOwner


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('cow-runtime', 'dependency-root', 'profile', 'vision-config', 'pack', 'browser', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    runtime = args.cow_runtime.resolve(strict=True)
    sys.path[:0] = [str(p) for p in (root, runtime, runtime / 'tools',
        runtime / 'experimental/branching_context/src', runtime / 'experimental/branching_context/scripts',
        args.dependency_root)]
    from run_cli_grammar_probe import GrammarProbe, _atomic_json
    from branchwrite.cow_client import CowClient, OperationJournal
    from branchwrite.execution import Executor
    from tools.run_cow_coding_pilot import CodingPilot, FileTask, create_file_schema
    from validation.run_basic_loop_images import verify_capture_delivery
    from validation.run_cow_coding_campaign import native_executable_identity

    pack, inventory = checked_pack(args.pack)
    task = (pack / 'tasks/H03.md').read_text().split('\n', 1)[1].strip()
    output = args.output.absolute()
    output.mkdir(mode=0o700, exist_ok=False)

    ImageOwner = image_probe_type(GrammarProbe, args.vision_config)
    probe = ImageOwner(SimpleNamespace(runtime_root=runtime, profile=args.profile,
        store=output / 'store', run_dir=output, dependency_root=args.dependency_root, ram_gib=96, disk_gib=128))
    probe.record.update(status='RUNNING', target='H03', cases=[], numerical_max_error=None,
        scope=__doc__, requested_model_stages=0, automatic_repairs=0, chat_server='NOT_STARTED', q8='DEFERRED')
    error = None
    try:
        probe._imports()
        profile = json.loads(args.profile.read_bytes())
        probe.runtime_closure(profile, runtime)
        probe.record.update(execution_profile_id=profile['execution_profile_id'],
            model_contract_id=profile['model_contract_id'], profile_sha256=sha(args.profile.read_bytes()),
            native_executable=native_executable_identity(profile),
            branchwrite_source_sha256={str(p.relative_to(root)): sha(p.read_bytes()) for folder in
                ('branchwrite', 'tools', 'validation') for p in (root / folder).rglob('*.py')},
            pack_manifest_sha256=sha((pack / 'FILES.sha256').read_bytes()), writer_task_sha256=sha(task.encode()))
        registry = output / 'registry.json'
        _atomic_json(registry, dict(schema=1, states=dict(
            BW_CREATE_HTML=dict(format='json_schema', source=create_file_schema('index.html')),
            BW_IMAGE_REPORT=dict(format='json_schema', source=visual_report_schema()))))
        probe.tracker = probe.ProgressTracker(output, 'basic-loop-H03').start()
        probe.start_service(registry)
        url = probe.ready_url(probe.service.ready)
        pin = sha((str(output / 'store') + probe.record['profile_sha256']).encode())
        client = CowClient.cli(url, runtime / 'tools/cow_cli.py', state_dir=output / 'cli-state',
            journal=OperationJournal(output / 'journal'), api_key=probe.secret, endpoint_pin=pin)
        probe.phase('model-create-and-real-readback')
        pilot = CodingPilot(client, output / 'writer', eos_tokens=tuple(profile['execution']['eos_tokens']),
                            max_tokens=1024, settings=dict(temperature=0.))
        probe.record['requested_model_stages'] += 1
        created = pilot.run_create_read(FileTask('H03', pack / 'fixtures/starter/H03', 'index.html', task),
            output_format='json_schema', grammar_state='BW_CREATE_HTML')
        probe.record['writer'] = asdict(created)
        probe.publish()
        if created.status != 'FILE_CREATED_AND_READ':
            raise ValueError('H03 writer did not complete a legal create/read; retain first attempt')
        source = output / 'writer/tool/workspace'
        actual = (source / 'index.html').read_bytes()
        if sha(actual) != created.created_sha256 or actual != (output / 'writer/readback.bin').read_bytes():
            raise ValueError('H03 created source/readback mismatch')
        probe.phase('capture-and-protected-checks-same-page')
        command = [sys.executable, '-B', str(root / 'tools/capture_page.py'), '--source', str(source),
            '--entry', 'index.html', '--expected-sha256', sha(actual), '--browser', str(args.browser),
            '--output', str(output / 'capture'), '--check-module', str(pack / 'protected/checks.py'),
            '--check-sha256', inventory['protected/checks.py'], '--check-target', 'H03']
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, close_fds=True, start_new_session=True)
        import time
        stdout, stderr, timed_out, limited, _ = Executor._capture(process, time.monotonic() + 45, 2 * 1024**2)
        (output / 'capture.stdout').write_bytes(stdout)
        (output / 'capture.stderr').write_bytes(stderr)
        if timed_out or limited or process.returncode not in (0, 1):
            raise ValueError('capture CLI failed; retain raw outcome')
        capture = tomllib.loads(stdout.decode())
        image = (output / 'capture/capture.png').read_bytes()
        if (capture['source_sha256'] != sha(actual) or capture['served_sha256'] != sha(actual)
                or capture['image_sha256'] != sha(image) or not capture['isolation_namespace_empty']
                or not capture['chromium_sandbox'] or not capture['isolation_worker_exited']
                or capture['inspection_sha256'] != inventory['protected/checks.py']
                or (process.returncode == 0) != (capture['inspection_status'] == 'PASS')):
            raise ValueError('capture/check result does not bind the actual source/image')
        probe.record.update(capture=capture, capture_cli_exit=process.returncode, capture_cli_pid=process.pid,
                            capture_cli_absent=not Path('/proc/' + str(process.pid)).exists())
        probe.publish()
        probe.phase('independent-image-only-observer')
        namespace = client.create_namespace('Visual observation', 'h03-observer-namespace')['namespace_id']
        upload = client.upload_image(namespace, image)
        prepared = client.prepare('h03-observer', namespace, observer_prompt(), 'h03-observer-prepare', images=(upload,))
        _, spans = probe.store.input_lineage(prepared.receipt.snapshot)
        verify_capture_delivery(spans, sha(image))
        probe.record['requested_model_stages'] += 1
        observed = client.answer('h03-observer', prepared.receipt.branch.revision, 'h03-observer-answer', 128,
            settings=dict(temperature=0.), grammar_state='BW_IMAGE_REPORT')
        tokens = observed.answer.get('tokens', [])
        if not tokens or tokens[-1] not in profile['execution']['eos_tokens']:
            raise ValueError('image observer did not finish with a consumed EOS')
        report = parse_visual_report(observed.answer['text'])
        expected = dict(heading='Loop Lab', square_count=1, color='blue', arrangement='single')
        quality = ('UNQUALIFIED_TARGET_FAILED' if capture['inspection_status'] != 'PASS' else
                   'PASS' if report == expected else 'FAIL')
        probe.record.update(observer=dict(report=report, answer=dict(observed.answer),
            receipt=dict(observed.receipt.raw), upload=dict(upload.raw), prepared=dict(prepared.receipt.raw),
            image_spans=spans, quality=quality, expected_host_only=expected,
            question_sha256=sha(observer_prompt().encode())),
            source_unchanged=(source / 'index.html').read_bytes() == actual)
        if not probe.record['source_unchanged']:
            raise ValueError('capture/observation changed the created page')
        probe.record['status'] = ('H03_CREATE_RENDER_OBSERVE_PASS' if quality == 'PASS' else
                                  'H03_TASK_FAIL_OUTCOME_RETAINED')
        if quality != 'PASS':
            error = ValueError('H03 task/observation failed; no automatic retry')
    except BaseException as exc:
        error = exc
        probe.record['status'] = 'H03_FAIL'
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
