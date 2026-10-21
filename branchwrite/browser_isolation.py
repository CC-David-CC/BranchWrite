"""Linux process/filesystem/network boundary for the existing capture tool.

Only captured input bytes enter the child. No candidate path, caller environment,
credential, service socket, host home, or GPU device is mounted. Chromium retains
its own renderer sandbox. A missing boundary is an error, never an unsafe fallback.
"""
import json
import math
import hashlib
import os
from pathlib import Path
import subprocess
import stat
import sys
import time


def _validate_browser_launcher(path):
    """A dedicated policy launcher must be an unmodified root-owned bwrap.

    This is not a privileged helper: no setuid bit or host capability is added.
    Its separate executable identity lets the operator grant nested namespaces
    without weakening the distribution's policy for every bwrap consumer.
    """
    info=path.lstat()
    if not stat.S_ISREG(info.st_mode):
        raise ValueError('browser launcher must be a real file')
    for item in (path,*path.parents):
        metadata=item.lstat()
        if (metadata.st_uid!=0 or metadata.st_mode&0o022
                or item!=path and not stat.S_ISDIR(metadata.st_mode)):
            raise ValueError('browser launcher and parents must be root-owned and not writable by other users')
    if info.st_mode&0o6000 or not os.access(path,os.X_OK):
        raise ValueError('browser launcher must be executable without setuid or setgid')
    if hashlib.sha256(path.read_bytes()).digest()!=hashlib.sha256(Path('/usr/bin/bwrap').read_bytes()).digest():
        raise ValueError('browser launcher differs from packaged bwrap; refresh the dedicated installation')
    return path


def _browser_launcher():
    dedicated=Path('/usr/local/libexec/branchwrite-browser-bwrap')
    if dedicated.exists() or dedicated.is_symlink():
        return _validate_browser_launcher(dedicated)
    return Path('/usr/bin/bwrap')


def isolation_command(config, *, document_path="index.html"):
    launcher = _browser_launcher()
    browser = config.executable.resolve(strict=True)
    python = Path(sys.executable)
    package = Path(__file__).resolve().parent
    for executable in (launcher, Path('/usr/bin/prlimit'), python, browser):
        if not executable.is_file() or not os.access(executable, os.X_OK):
            raise ValueError('browser isolation prerequisite unavailable: ' + str(executable))
    command = ['/usr/bin/prlimit', '--core=0', '--fsize=33554432',
        '--cpu=' + str(math.ceil(config.timeout) + 2), '--', str(launcher),
        '--die-with-parent', '--new-session', '--unshare-all', '--unshare-user',
        '--cap-drop', 'ALL', '--clearenv']
    # Runtime files are read-only. The configured venv contains the client-side
    # Playwright/Pillow dependencies; it is not a bind of the caller's home.
    # Installer-owned Python keeps its standard library outside the venv.
    # Both runtime roots must exist inside the namespace before Python starts.
    for path in dict.fromkeys((Path('/usr'), Path('/lib'), Path('/lib64'),
            Path(sys.base_prefix), Path(sys.prefix), browser.parent)):
        command.extend(('--ro-bind', str(path), str(path)))
    for path in (Path('/etc/fonts'), Path('/etc/ld.so.cache')):
        if path.exists():
            command.extend(('--ro-bind', str(path), str(path)))
    if config.inspection is not None:
        check = config.inspection
        if (check.path.is_symlink() or not check.path.is_file()
                or hashlib.sha256(check.path.read_bytes()).hexdigest() != check.sha256):
            raise ValueError('inspection source is unavailable or changed')
        command.extend(('--dir', '/inspection', '--ro-bind', str(check.path), '/inspection/checks.py'))
    command.extend(('--dir', '/app', '--ro-bind', str(package), '/app/branchwrite',
        '--proc', '/proc', '--dev', '/dev', '--size', '134217728', '--tmpfs', '/tmp',
        '--chmod', '1777', '/tmp', '--dir', '/run', '--chdir', '/tmp'))
    for name, value in dict(PATH='/usr/bin:/bin', LANG='C.UTF-8', LC_ALL='C.UTF-8',
            TZ='UTC', HOME='/tmp/home', XDG_CACHE_HOME='/tmp/cache',
            PYTHONDONTWRITEBYTECODE='1').items():
        command.extend(('--setenv', name, value))
    command.extend(('--', str(python), '-I', '-B', '/app/branchwrite/browser_worker.py',
        '--browser', str(browser), '--width', str(config.width), '--height', str(config.height),
        '--timeout', str(config.timeout), '--document-path',document_path))
    if config.inspection is not None:
        command.extend(('--inspection-sha256', config.inspection.sha256,
                        '--inspection-target', config.inspection.target))
    return command


def namespace_members(namespace):
    """Observe only the recorded worker namespace; never kill unrelated jobs."""
    members = []
    for path in Path('/proc').iterdir():
        if path.name.isdecimal():
            try:
                if os.readlink(path / 'ns/pid') == namespace:
                    members.append(int(path.name))
            except (FileNotFoundError, PermissionError, ProcessLookupError):
                pass
    return members


def await_namespace_retirement(namespace,*,timeout=0.5):
    """Allow bounded kernel teardown, but require real absence before success."""
    deadline=time.monotonic()+timeout
    while True:
        members=namespace_members(namespace)
        if not members:return []
        remaining=deadline-time.monotonic()
        if remaining<=0:return members
        time.sleep(min(.01,remaining))


def render_isolated(payload, config, *, assets=(), document_path="index.html"):
    from .browser_capture import RenderedPage
    from .browser_assets import validate_assets
    assets=validate_assets(assets)
    from .execution import Executor
    if not hasattr(os, 'memfd_create'):
        raise ValueError('isolated browser capture requires Linux memfd support')
    descriptor = os.memfd_create('bw-browser-input', os.MFD_CLOEXEC)
    process = None
    try:
        with os.fdopen(descriptor, 'w+b') as source:
            source.write(json.dumps(dict(actions=[a.wire for a in config.actions],source_bytes=len(payload),assets=[a.manifest for a in assets]),separators=(',', ':')).encode() + b'\n')
            source.write(payload)
            for asset in assets:source.write(asset.body)
            source.seek(0)
            process = subprocess.Popen(isolation_command(config,document_path=document_path), stdin=source,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True,
                start_new_session=True, env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'})
        out, err, timed_out, limited, _ = Executor._capture(
            process, time.monotonic() + config.timeout, 9 * 1024 * 1024)
    finally:
        if process is not None and process.poll() is None:
            import signal
            Executor._signal_group(process, signal.SIGKILL)
            process.wait(timeout=3)
    if timed_out or limited or process.returncode != 0:
        # The executor bounds the public error to 512 characters. Put the
        # actual rejection first, rather than truncating it behind a traceback.
        lines = [line.strip() for line in err.decode('utf8', 'replace').splitlines() if line.strip()]
        # Playwright appends cleanup logs after Chromium's real rejection.
        # Report the observed sandbox failure without recommending a bypass
        # or guessing which host policy caused it.
        if any('No usable sandbox!' in line for line in lines):
            detail = 'Chromium sandbox unavailable; configure a supported sandboxed browser on this client'
        elif any('SUID sandbox helper binary' in line for line in lines):
            detail = 'Chromium sandbox helper unavailable in isolated worker; use a supported sandboxed browser installation'
        else:
            detail = lines[-1][:480] if lines else 'worker exit ' + str(process.returncode)
        reason = 'deadline expired' if timed_out else 'output limit' if limited else detail
        raise ValueError('isolated browser failed: ' + reason)
    header, separator, png = out.partition(b'\n')
    if not separator or len(header) > 524288:
        raise ValueError('invalid isolated browser response framing')
    value = json.loads(header)
    if set(value) != {'browser_version', 'url', 'http_status', 'served_sha256', 'isolation', 'inspection', 'actions', 'text', 'asset_manifest', 'served_assets', 'document_path', 'runtime_errors'}:
        raise ValueError('invalid isolated browser response fields')
    if (value['actions'] != [a.wire for a in config.actions]
            or type(value['text']) is not str or len(value['text']) > 8192
            or (not config.actions and value['text'] != '')):
        raise ValueError('browser action receipt differs from requested sequence')
    manifest=[a.manifest for a in assets]
    if (value['document_path']!=document_path or value['asset_manifest']!=manifest or type(value['served_assets']) is not list
            or len(value['served_assets'])>256
            or any(row not in manifest for row in value['served_assets'])):
        raise ValueError('browser asset receipt differs from captured bundle')
    errors=value['runtime_errors']
    if (type(errors) is not list or len(errors)>16
            or any(type(error) is not str or not 0<len(error)<=1024 for error in errors)):
        raise ValueError('invalid browser runtime error receipt')
    inspection = value['inspection']
    if config.inspection is None:
        if inspection is not None:
            raise ValueError('unexpected page inspection result')
    elif (not isinstance(inspection, dict) or set(inspection) !=
            {'schema', 'target', 'inspector_sha256', 'status', 'error', 'actions'}
            or inspection['schema'] != 1 or inspection['target'] != config.inspection.target
            or inspection['inspector_sha256'] != config.inspection.sha256
            or inspection['status'] not in ('PASS', 'FAIL')
            or type(inspection['actions']) is not list or len(inspection['actions']) > 32
            or any(type(action) is not list or len(action) != 2
                   or any(type(value) is not str or len(value) > 256 for value in action)
                   for action in inspection['actions'])):
        raise ValueError('page inspection result does not match the host request')
    witness = value['isolation']
    if (witness.get('kind') != 'bubblewrap-browser-v1' or witness.get('schema') != 1
            or witness.get('chromium_sandbox') is not True
            or any(witness.get(name) == os.readlink('/proc/self/ns/' + suffix)
                   for name, suffix in (('net_ns', 'net'), ('pid_ns', 'pid'), ('mount_ns', 'mnt')))):
        raise ValueError('isolated browser namespace witness did not match the required boundary')
    retirement_started=time.monotonic()
    members = await_namespace_retirement(witness['pid_ns'])
    if members:
        raise ValueError('browser namespace still has live processes after capture: '+str(members))
    witness.update(worker_exited=True, launcher_pid=process.pid, namespace_members_after=members,
                   retirement_wait_seconds=time.monotonic()-retirement_started)
    return RenderedPage(png, value['browser_version'], value['url'], value['http_status'],
                        value['served_sha256'], witness, inspection, tuple(value['actions']), value['text'],
                        tuple(value['asset_manifest']),tuple(value['served_assets']),value['document_path'],
                        tuple(errors))
