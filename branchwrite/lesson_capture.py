"""Private archival BW boundaries, never independent correctness or training approval.

The existing RuntimeLog read lease excludes workflow writers throughout capture.
Only local file tools, retired terminal commands and locally validated, complete
COW receipts are supported. No executor, native work or network request is run.
"""
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat

from .records import RuntimeLog, Artifact, decode, encode, MAX_BYTES
from .kernel import FrameKernel
from .coding_cli import read_launch, _bytes
from .execution import Executor, Grant, ToolRejected, _relative_path
from .tool_registry import ToolRegistry

MAX_WORLD_BYTES = 64 * 1024**2
MAX_CAPTURE_BYTES = 256 * 1024**2
MAX_ENTRIES = 20000
_HEX = re.compile('[a-f0-9]{64}\\Z')
_LOCAL = {'read_file', 'replace', 'replace_text_file', 'create_file', 'create_text_file', 'set_mode', 'finish'}
_TERMINAL = {'run_shell', 'run_check'}


class CaptureRefused(ValueError):
    """Evidence is unavailable/unsupported; this is not a model score."""


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def _sha(raw): return hashlib.sha256(raw).hexdigest()


def _json(raw):
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value: raise CaptureRefused('duplicate archive field')
            value[key] = item
        return value
    try: return json.loads(raw, object_pairs_hook=pairs, parse_constant=lambda _: (_ for _ in ()).throw(CaptureRefused('nonfinite archive value')))
    except (ValueError, UnicodeError, RecursionError) as exc: raise CaptureRefused('invalid bounded archive JSON') from exc


def _real_path(path, *, directory=True):
    path = Path(os.path.abspath(path))
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        info = current.lstat()
        if stat.S_ISLNK(info.st_mode): raise CaptureRefused('linked path is unsupported')
    info = path.lstat()
    if directory and (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()):
        raise CaptureRefused('owned real directory required')
    return path


def _key(info):
    return tuple(getattr(info, k) for k in ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns', 'st_mode', 'st_nlink', 'st_uid'))


def _read(path, limit=MAX_BYTES):
    _real_path(Path(path).parent)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                or before.st_uid != os.getuid() or before.st_size > limit):
            raise CaptureRefused('bounded owned non-aliased regular file required')
        raw = bytearray()
        while block := os.read(fd, min(65536, limit + 1 - len(raw))):
            raw.extend(block)
            if len(raw) > limit: raise CaptureRefused('capture byte limit exceeded')
        after = os.fstat(fd)
        if _key(before) != _key(after) or _key(after) != _key(Path(path).lstat()) or len(raw) != before.st_size:
            raise CaptureRefused('capture source changed during read')
        return bytes(raw)
    finally: os.close(fd)


def _write(path, raw):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw); stream.flush(); os.fchmod(stream.fileno(), 0o400); os.fsync(stream.fileno())


def _sync(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try: os.fsync(fd)
    finally: os.close(fd)


def _implementation():
    """Pin the installed BW validator/helper closure, not a claimed version label."""
    root = Path(__file__).resolve().parent
    return {p.name: _sha(_read(p)) for p in sorted(root.glob('*.py'))}


def _copy_failure(previous, target):
    target.mkdir(mode=0o700)
    total = 0
    for path in sorted(previous.directory.rglob('*')):
        relative = path.relative_to(previous.directory); destination = target/relative
        if path.is_dir():
            _real_path(path); destination.mkdir(mode=0o700)
        else:
            raw = _read(path); total += len(raw)
            if total > MAX_CAPTURE_BYTES: raise CaptureRefused('failure archive exceeds bound')
            _write(destination, raw)
    read_capture(target, expected_capture_id=previous.capture_id)
    return total


def _capture_files(executor):
    """Reuse the executor's bounded no-follow private reader, preserving modes."""
    files, directories, total = [], [], 0
    root_info = executor.workspace.lstat()
    if (root_info.st_dev, root_info.st_ino) != executor._workspace_identity:
        raise CaptureRefused('workspace identity changed')
    for directory, dirs, names, fd in os.fwalk(executor.workspace, follow_symlinks=False):
        parent = Path(directory).relative_to(executor.workspace)
        for name in dirs:
            info = os.stat(name, dir_fd=fd, follow_symlinks=False)
            if name == '.git' or not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o7000:
                raise CaptureRefused('unsupported workspace directory/link')
            directories.append(dict(path=(parent/name).as_posix(), mode=stat.S_IMODE(info.st_mode)))
        for name in names:
            path = (parent/name).as_posix(); _relative_path(path)
            before = os.stat(name, dir_fd=fd, follow_symlinks=False)
            if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_uid != os.getuid()
                    or before.st_mode & 0o7000): raise CaptureRefused('unsupported workspace file/alias/mode')
            raw = executor._read_private_bytes(path)
            after = os.stat(name, dir_fd=fd, follow_symlinks=False)
            if _key(before) != _key(after): raise CaptureRefused('workspace changed during capture')
            total += len(raw)
            if total > MAX_WORLD_BYTES: raise CaptureRefused('world byte limit exceeded')
            files.append((dict(path=path, mode=stat.S_IMODE(after.st_mode), bytes=len(raw), sha256=_sha(raw)), raw))
        if len(files) + len(directories) > MAX_ENTRIES: raise CaptureRefused('world entry limit exceeded')
    return sorted(files, key=lambda item: item[0]['path']), sorted(directories, key=lambda item: item['path'])


class _NoNetwork:
    name = 'archival-reader-no-network'
    def request(self, *args, **kwargs): raise CaptureRefused('archival reader cannot dispatch requests')


def _native(log, frames, launch, journal):
    """Use existing exact local receipt readers, never a status flag alone."""
    from .cow_client import CowClient, OperationJournal, OperationIntent, FrameKey, COWSourceBinding
    from .model_dispatch import ModelAdapter
    cow = launch['config']['cow']
    client = CowClient(_NoNetwork(), journal=OperationJournal(journal), endpoint_url=cow['endpoint_url'], endpoint_pin=cow['endpoint_pin'])
    adapter = ModelAdapter(client, run_id=launch['config']['run_id'], model_contract_id=cow['model_contract_id'],
        execution_profile_id=cow['execution_profile_id'], eos_tokens=tuple(cow['eos_tokens']))
    records = {}
    for path in sorted(Path(journal).iterdir()):
        if not path.is_file() or not re.fullmatch('[a-f0-9]{64}\\.json', path.name): raise CaptureRefused('unexpected native journal entry')
        initial = _json(_read(path)); op = initial.get('operation_id')
        record = client.journal.read(op)
        if record != initial or client.journal._path(op).name != path.name or record.get('state') != 'complete':
            raise CaptureRefused('native journal has no complete original receipt')
        if record.get('endpoint_url') != client.endpoint_url or record.get('endpoint_pin') != client.endpoint_pin:
            raise CaptureRefused('native journal endpoint differs')
        body_raw = client.journal.decode_body(record); body = _json(body_raw)
        if body.get('operation_id') != op or record.get('method') != 'POST': raise CaptureRefused('native journal request binding differs')
        route = record.get('path')
        if route in ('/cow/namespace', '/cow/grammars', '/cow/fork'):
            intent = OperationIntent(op, 'POST', route, body_raw, record.get('branch'), record.get('revision'),
                FrameKey.from_json(record['frame_key']) if record.get('frame_key') else None, client.endpoint_pin,
                COWSourceBinding.from_json(record['source_binding']) if record.get('source_binding') else None)
            client._validate_nonstream(intent, record['receipt'])
        elif route in ('/cow/text/context', '/cow/text/prepare', '/cow/text/answer', '/cow/text/ask', '/cow/text/append-user', '/cow/text/resume'):
            value = client.read_completed_generation(op)
            if (value.receipt.raw.get('model_contract_id') != cow['model_contract_id']
                    or value.receipt.raw.get('execution_profile_id') != cow['execution_profile_id']
                    or value.answer.get('stopped') is False):
                raise CaptureRefused('partial native output or model/profile mismatch')
        else: raise CaptureRefused('unsupported native journal operation')
        records[op] = record
    summaries = []
    for frame in frames:
        if frame['contract'] != ('COWNativeReceipt', 'record'): continue
        if frame['state'] != 'Closed' or frame['dispatch'] is None: raise CaptureRefused('native frame is not settled')
        request = decode(log.read_artifact(Artifact(*frame['inputs'])))
        if request.get('kind') != 'bw.model-native-request': raise CaptureRefused('unsupported native frame intent')
        op = request['frame_key']['operation_id']
        if (op not in records or frame['dispatch'] != (op, frame['inputs'])
                or request['frame_key'].get('child_id') != frame['id']
                or request['frame_key'].get('run_id') != launch['config']['run_id']
                or request.get('model_frame') != frame['parent']):
            raise CaptureRefused('missing exact native frame/journal owner')
        adapter.check_journal(request)
        result = decode(log.read_artifact(Artifact(*frame['result'])))[2]
        if result.get('operation_id') != op or result.get('request_sha256') != frame['inputs'][0]: raise CaptureRefused('native ledger result binding differs')
        payload = _json(log.read_artifact(Artifact(*result['response'])))
        adapter.validate_response(request, payload)
        local = client.read_completed_generation(op)
        expected = dict(operation_id=op, receipt=dict(local.receipt.raw), answer=dict(local.answer),
            source_binding=None if local.source_binding is None else local.source_binding.to_json())
        if payload != expected: raise CaptureRefused('native journal and ledger outputs disagree')
        summaries.append(dict(frame=frame['id'], operation_id=op, request_sha256=frame['inputs'][0], response_sha256=result['response'][0]))
    return summaries


def _evidence(log, launch, kind, inventory, journal, *, live=False):
    kernel = FrameKernel(log); frames = kernel.frames(); roots = [f for f in frames if f['parent'] is None]
    if len(roots) != 1 or roots[0]['id'] != 'program' or roots[0]['contract'] != ('ProgramResult', 'record'):
        raise CaptureRefused('one actual coding program root required')
    root = roots[0]; inputs = decode(log.read_artifact(Artifact(*root['inputs'])))
    expected = ('Text', hashlib.sha256(_bytes(launch['config'])).hexdigest())
    if inputs.get('bindings', {}).get('host-config-sha256') != expected: raise CaptureRefused('launch differs from admitted host configuration')
    world = inputs.get('bindings', {}).get('world')
    if type(world) is not tuple or len(world) != 2 or world[0] != 'World' or not _HEX.fullmatch(str(world[1])):
        raise CaptureRefused('missing canonical world identity')
    from .language import parse, render
    if log.read_artifact(Artifact(*root['definition'])) != render(parse(launch['program'])).encode():
        raise CaptureRefused('launch differs from actual admitted program')
    if any(f['dispatch'] is not None and f['state'] != 'Closed' for f in frames):
        raise CaptureRefused('dispatched operation has no settled ledger result')
    if any(f['contract'] == ('ModelOutput', 'record') and f['state'] != 'Closed' for f in frames):
        raise CaptureRefused('partial logical model output remains open')
    from .project_baseline import BINDING, load, parse_reference
    ref = inputs.get('bindings', {}).get(BINDING)
    if type(ref) is not tuple or len(ref) != 2 or ref[0] != 'Text': raise CaptureRefused('complete original project baseline required')
    baseline = load(log, parse_reference(ref[1]))
    verified = None if root['state'] != 'Closed' else decode(log.read_artifact(Artifact(*root['result'])))[2].get('verified')
    if verified is not None and type(verified) is not bool: raise CaptureRefused('invalid recorded workflow verdict')
    checks, tools, finish = [], [], []
    commands = {row['command'] for row in launch['config'].get('verification', {}).get('commands', [])}
    for frame in frames:
        if frame['contract'] != ('ToolOutcome', 'record'): continue
        if frame['state'] != 'Closed':
            # An undispatched proposal has no effect and is not an outcome.
            if frame['dispatch'] is None: continue
            raise CaptureRefused('unsettled tool effect')
        plan = decode(log.read_artifact(Artifact(*frame['inputs'])))
        value = decode(log.read_artifact(Artifact(*frame['result'])))[2]
        if (type(plan) is not tuple or len(plan) != 8 or plan[0] != 'bw.tool-plan.v2'
                or value.get('plan_sha256') != frame['inputs'][0] or value.get('tool') != plan[3]
                or plan[2] != world[1]
                or frame['dispatch'] is None or value.get('operation_id') != frame['dispatch'][0]):
            raise CaptureRefused('tool outcome is not its actual admitted plan/result')
        tool = plan[3]
        if tool not in _LOCAL | _TERMINAL: raise CaptureRefused('unsupported external/tool effect')
        for stream in ('stdout', 'stderr'): log.read_artifact(Artifact(*value[stream]))
        if tool in _TERMINAL:
            details = value.get('details', {}); witness = details.get('isolation', {})
            if (value.get('disposition') != 'exited' or type(value.get('exit_code')) is not int
                    or not 0 <= value['exit_code'] < 126 or witness.get('kind') != 'bubblewrap-terminal-v1'
                    or witness.get('worker_exited') is not True or witness.get('namespace_members_after') != []
                    or not re.fullmatch('pid:\\[[0-9]+\\]', str(witness.get('pid_ns')))):
                raise CaptureRefused('terminal command lacks bounded retired-namespace execution evidence')
            if live:
                from .browser_isolation import await_namespace_retirement
                if await_namespace_retirement(witness['pid_ns']): raise CaptureRefused('recorded terminal namespace is still present')
            eligible = tool == 'run_check' and launch['config'].get('verification', {}).get('selected_checks') is True or tool == 'run_shell' and plan[4].get('command') in commands
            if eligible: checks.append(dict(frame=frame['id'], tool=tool, arguments=plan[4],
                exit_code=value['exit_code'], current=details.get('workspace_after_sha256') == inventory,
                result_sha256=frame['result'][0], namespace=witness))
        elif tool == 'finish':
            if value.get('requested_finish') is not True or value.get('disposition') != 'completion_requested': raise CaptureRefused('invalid explicit finish evidence')
            finish.append(frame['id'])
        elif (value.get('disposition') != {'read_file':'read', 'replace':'applied', 'replace_text_file':'applied',
                'create_file':'created', 'create_text_file':'created', 'set_mode':'mode_changed'}[tool]
                or value.get('exit_code') != 0):
            raise CaptureRefused('file operation does not have its completed supported outcome')
        tools.append(dict(frame=frame['id'], tool=tool, world=plan[2], plan_sha256=frame['inputs'][0], result_sha256=frame['result'][0]))
    current = [c for c in checks if c['current']]
    if kind == 'failure' and verified is True: raise CaptureRefused('passing workflow is not a failure capture')
    if kind == 'correction' and (verified is not True or not finish or not any(c['exit_code'] == 0 for c in current)):
        raise CaptureRefused('correction requires current passing checks and recorded explicit completion')
    world_binding = 'current-selected-check-inventory-v1'
    if not current:
        # Failure capture is archival, not a requirement that the student knew
        # how to check its attempt. Without check evidence, the initial supported
        # world is the exact baseline plus read/finish observations only. Do not
        # invent post-write state from a current inventory or a verified flag.
        if checks: raise CaptureRefused('selected check inventories are stale for captured files')
        if inventory != baseline['inventory'] or any(t['tool'] not in ('read_file', 'finish') for t in tools):
            raise CaptureRefused('unchecked changed/file-effect world is not yet supported; no historical state was reconstructed')
        world_binding = 'unchanged-baseline-no-check-v1'
    native = _native(log, frames, launch, journal)
    return dict(program_sha256=root['definition'][0], inputs_sha256=root['inputs'][0], world_id=world[1], root_state=root['state'],
        recorded_workflow_verified=verified, baseline_inventory=baseline['inventory'], baseline_reference=ref[1],
        task_id=_sha(encode(('bw.lesson-task.v1', launch['config']['bindings']['task'], baseline['inventory'], launch['config']['cow']['model_contract_id']))),
        tools=tools, checks=checks, world_binding=world_binding, explicit_finish_frames=finish, native=native)


def _inventory(files, directories):
    """The existing ToolRegistry inventory encoding over archived exact bytes/modes."""
    items = [('directory', row['path'], row['mode']) for row in directories]
    items += [('file', row['path'], row['sha256'], row['mode']) for row in files]
    names = []
    for item in items:
        _relative_path(item[1]); names.append(item[1])
        if type(item[-1]) is not int or not 0 <= item[-1] <= 0o777:
            raise CaptureRefused('invalid captured basic mode')
    if len(set(names)) != len(names) or len(names) > MAX_ENTRIES: raise CaptureRefused('duplicate/oversized inventory')
    directory_names = {row['path'] for row in directories}
    for name in names:
        if any(p.as_posix() not in directory_names for p in Path(name).parents if str(p) != '.'):
            raise CaptureRefused('captured parent directory is absent')
    digest = hashlib.sha256(b'bw.workspace-inventory.v1\0')
    for item in sorted(items): digest.update(encode(item))
    return digest.hexdigest()


def _copy_store(log, target, paths):
    entries = []
    for path in sorted(paths):
        raw = _read(path); relative = path.relative_to(log.root)
        if relative.parts[0] == 'artifacts' and (not _HEX.fullmatch(path.name) or _sha(raw) != path.name):
            raise CaptureRefused('invalid immutable ledger artifact')
        destination = target/relative; destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        _write(destination, raw); entries.append(dict(path=relative.as_posix(), sha256=_sha(raw), bytes=len(raw)))
    return entries


@dataclass(frozen=True)
class LessonCapture:
    directory: Path
    _manifest: bytes
    @property
    def manifest(self): return _json(self._manifest)
    @property
    def capture_id(self): return self.manifest['capture_id']
    @property
    def failure_capture_id(self): return self.manifest['failure_capture_id']
    @property
    def independently_verified(self): return False
    @property
    def training_approved(self): return False
    def file_bytes(self, path):
        _relative_path(path)
        rows = [row for row in self.manifest['files'] if row['path'] == path]
        if len(rows) != 1: raise CaptureRefused('file is absent from exact captured inventory')
        row = rows[0]; raw = _read(self.directory/'objects'/row['sha256'])
        if len(raw) != row['bytes'] or _sha(raw) != row['sha256']: raise CaptureRefused('captured file changed')
        return raw


def _capture(state, output, kind, failure=None):
    state = _real_path(state); parent = _real_path(Path(output).absolute().parent)
    output = parent/Path(output).name
    if output.exists() or output.is_symlink(): raise CaptureRefused('capture output must be new')
    launch = read_launch(state); source = _real_path(launch['config']['source'])
    if any(not _HEX.fullmatch(str(launch['config']['cow'].get(key))) for key in ('model_contract_id', 'execution_profile_id')):
        raise CaptureRefused('exact SHA-256 model and execution identities required')
    if any(output == p or output.is_relative_to(p) or p.is_relative_to(output) for p in (state, source)):
        raise CaptureRefused('capture output overlaps workflow/source')
    if kind == 'correction':
        previous = read_capture(failure)
        if previous.manifest['kind'] != 'failure': raise CaptureRefused('an original failure capture is required')
        if output.is_relative_to(previous.directory) or previous.directory.is_relative_to(output):
            raise CaptureRefused('correction output overlaps original failure archive')
    else: previous = None
    if any(key in launch['config'] for key in ('remotes', 'browser', 'cad', 'blender', 'exploration')):
        raise CaptureRefused('capture currently supports one local filesystem/terminal world')
    output.mkdir(mode=0o700); (output/'objects').mkdir(mode=0o700); (output/'ledger').mkdir(mode=0o700); (output/'cow-operations').mkdir(mode=0o700)
    # A failed capture deliberately retains its incomplete private directory;
    # absence of capture.json means unavailable, never a successful receipt.
    with RuntimeLog(state/'ledger', read_only=True) as log:
        config = launch['config']; world = _real_path(state/'world'); workspace = _real_path(world/'workspace')
        executor = Executor(source, world, workspace); registry = ToolRegistry(executor, Grant((), False))
        with executor._lock:
            inventory = registry._inventory(); files, directories = _capture_files(executor)
            if _inventory([row for row, _ in files], directories) != inventory:
                raise CaptureRefused('captured bytes/modes differ from actual inventory')
            ledger_paths = [log.root/'events.bwl', log.root/'writer.lock', *sorted(log.artifacts.iterdir())]
            if len(ledger_paths) > MAX_ENTRIES: raise CaptureRefused('ledger entry limit exceeded')
            total = sum(len(raw) for _, raw in files)
            total += sum(p.lstat().st_size for p in ledger_paths)
            journal = state/'cow-operations'; original_journal = {}
            if journal.exists():
                _real_path(journal)
                for path in sorted(journal.iterdir()):
                    raw = _read(path); total += len(raw); original_journal[path.name] = raw
                    if len(original_journal) > MAX_ENTRIES: raise CaptureRefused('journal entry limit exceeded')
                    _write(output/'cow-operations'/path.name, raw)
            if total > MAX_CAPTURE_BYTES: raise CaptureRefused('archive byte limit exceeded')
            evidence = _evidence(log, launch, kind, inventory, output/'cow-operations', live=True)
            if evidence['world_id'] != registry.world: raise CaptureRefused('recorded and current workspace identities differ')
            if previous and evidence['task_id'] != previous.manifest['evidence']['task_id']:
                raise CaptureRefused('correction differs from original task/baseline/model')
            if previous:
                if previous.manifest['original_state'] == str(state):
                    old = _read(previous.directory/'ledger/events.bwl')
                    if not _read(log.root/'events.bwl').startswith(old):
                        raise CaptureRefused('same-run correction is not a continuation of captured failure ledger')
                total += _copy_failure(previous, output/'failure')
                if total > MAX_CAPTURE_BYTES: raise CaptureRefused('combined correction/failure archive exceeds bound')
            for row, raw in files:
                destination = output/'objects'/row['sha256']
                if not destination.exists(): _write(destination, raw)
            ledger = _copy_store(log, output/'ledger', ledger_paths)
            if registry._inventory() != inventory or _capture_files(executor) != (files, directories):
                raise CaptureRefused('workspace changed during archival inspection')
            if read_launch(state) != launch: raise CaptureRefused('launch changed during inspection')
            if any(_read(log.root/row['path']) != _read(output/'ledger'/row['path']) for row in ledger):
                raise CaptureRefused('ledger changed during capture')
            current_journal = {} if not journal.exists() else {p.name: _read(p) for p in sorted(journal.iterdir())}
            if current_journal != original_journal: raise CaptureRefused('native journal changed during capture')
            manifest = dict(schema=1, method='bw-lesson-capture-v1', kind=kind, original_state=str(state), launch=launch,
                implementation_sha256=_implementation(),
                model_contract_id=config['cow']['model_contract_id'], execution_profile_id=config['cow']['execution_profile_id'],
                files=[row for row, _ in files], directories=directories, inventory=inventory, evidence=evidence,
                ledger=ledger, journals=[dict(path=name, sha256=_sha(raw), bytes=len(raw)) for name, raw in original_journal.items()],
                failure_capture_id=None if previous is None else previous.capture_id,
                scope='private archival workflow boundary; host checks only, not independent correctness',
                independently_verified=False, training_approved=False)
            manifest['capture_id'] = _sha(_canonical(manifest))
            if len(_canonical(manifest)) > MAX_BYTES: raise CaptureRefused('capture manifest exceeds metadata bound')
            _write(output/'capture.json', _canonical(manifest)+b'\n')
            for directory in (output/'objects', output/'ledger/artifacts', output/'ledger', output/'cow-operations', output):
                if directory.exists(): _sync(directory)
            _sync(parent)
    return read_capture(output)


def capture_failure(state, output):
    return _capture_checked(state, output, 'failure')


def capture_assessment(state, output):
    """Archive a settled workflow attempt, without asserting failure or correction.

    A consumer must check the recorded tools/verification and independently
    grade the artifact. This grants no training approval and does not invent a
    preceding failure. Unsupported or unsettled effects remain unavailable.
    """
    return _capture_checked(state, output, 'assessment')


def capture_correction(state, output, failure):
    return _capture_checked(state, output, 'correction', failure)


def _capture_checked(state, output, kind, failure=None):
    from .records import WriterBusy
    from .cow_client import CowClientError
    try: return _capture(state, output, kind, failure)
    except (CaptureRefused, WriterBusy): raise
    except (OSError, KeyError, TypeError, ValueError, CowClientError) as exc:
        raise CaptureRefused('workflow capture unavailable: '+type(exc).__name__) from exc


def read_capture(directory, *, expected_capture_id=None):
    """Validate copied bytes and replay original receipt evidence without dispatch."""
    try:
        directory = _real_path(directory); raw = _read(directory/'capture.json'); value = _json(raw)
        fields = {'schema','method','kind','original_state','launch','model_contract_id','execution_profile_id',
            'files','directories','inventory','evidence','ledger','journals','failure_capture_id','scope',
            'independently_verified','training_approved','capture_id','implementation_sha256'}
        if (type(value) is not dict or set(value) != fields or value.get('schema') != 1 or value.get('method') != 'bw-lesson-capture-v1'
                or value.get('kind') not in ('failure', 'correction', 'assessment')
                or value.get('independently_verified') is not False or value.get('training_approved') is not False
                or value.get('capture_id') != _sha(_canonical({k:v for k,v in value.items() if k != 'capture_id'}))):
            raise CaptureRefused('invalid archival capture identity/scope')
        if ((value['kind'] in ('failure', 'assessment') and value['failure_capture_id'] is not None)
                or (value['kind'] == 'correction' and not _HEX.fullmatch(str(value['failure_capture_id'])))
                or value['model_contract_id'] != value['launch']['config']['cow']['model_contract_id']
                or value['execution_profile_id'] != value['launch']['config']['cow']['execution_profile_id']):
            raise CaptureRefused('capture model/link binding differs')
        if expected_capture_id is not None and value['capture_id'] != expected_capture_id:
            raise CaptureRefused('capture differs from owner-pinned identity')
        if value['implementation_sha256'] != _implementation():
            raise CaptureRefused('installed capture validator/helper source differs')
        if _inventory(value['files'], value['directories']) != value['inventory']:
            raise CaptureRefused('archived inventory does not describe captured files/modes')
        expected = {'capture.json'}; total = 0
        for category, prefix in [('ledger', 'ledger/'), ('journals', 'cow-operations/')]:
            for row in value[category]:
                name = row['path']; _relative_path(name); path = directory/(prefix+name)
                body = _read(path); total += len(body)
                if len(body) != row['bytes'] or _sha(body) != row['sha256']: raise CaptureRefused('archived receipt bytes changed')
                expected.add(prefix+name)
        result = LessonCapture(directory, _canonical(value))
        file_names = set()
        for row in value['files']:
            _relative_path(row['path'])
            if row['path'] in file_names or not _HEX.fullmatch(row['sha256']): raise CaptureRefused('duplicate/invalid captured file')
            file_names.add(row['path']); total += len(result.file_bytes(row['path'])); expected.add('objects/'+row['sha256'])
        if total > MAX_CAPTURE_BYTES or len(expected) > MAX_ENTRIES*3: raise CaptureRefused('archive limits exceeded')
        expected_directories = {'objects', 'ledger', 'ledger/artifacts', 'cow-operations'}
        if value['kind'] == 'correction':
            previous = read_capture(directory/'failure', expected_capture_id=value['failure_capture_id'])
            if previous.manifest['kind'] != 'failure' or previous.manifest['evidence']['task_id'] != value['evidence']['task_id']:
                raise CaptureRefused('correction links another failure/task/baseline/model')
            if previous.manifest['original_state'] == value['original_state'] and not _read(directory/'ledger/events.bwl').startswith(_read(previous.directory/'ledger/events.bwl')):
                raise CaptureRefused('same-run archived correction lacks failure ledger prefix')
            expected_directories.add('failure')
            for path in previous.directory.rglob('*'):
                relative = path.relative_to(directory).as_posix()
                if path.is_dir(): expected_directories.add(relative)
                else: expected.add(relative); total += len(_read(path))
            if total > MAX_CAPTURE_BYTES: raise CaptureRefused('combined archive exceeds bound')
        actual = {p.relative_to(directory).as_posix() for p in directory.rglob('*') if p.is_file() or p.is_symlink()}
        if actual != expected: raise CaptureRefused('unexpected or missing archival files')
        directory_names = {p.relative_to(directory).as_posix() for p in directory.rglob('*') if p.is_dir()}
        if directory_names != expected_directories:
            raise CaptureRefused('unexpected or missing archival directories')
        with RuntimeLog(directory/'ledger', read_only=True) as log:
            observed = _evidence(log, value['launch'], value['kind'], value['inventory'], directory/'cow-operations')
        if observed != value['evidence']: raise CaptureRefused('archive summary does not match actual ledger/receipt evidence')
        return result
    except CaptureRefused: raise
    except (OSError, KeyError, TypeError, IndexError, ValueError, ToolRejected) as exc:
        raise CaptureRefused('capture unavailable or changed: '+type(exc).__name__) from exc
