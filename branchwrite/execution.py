"""Bounded registered tests and grant-checked file creation, reading and editing.

This module is deliberately a small host boundary, not an arbitrary shell tool.
Tests run in bubblewrap. Optional browser capture uses a host-selected Chromium
with its renderer sandbox enabled; trusted-fixture scope is explicit below.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import math
import os
from pathlib import Path, PurePosixPath
import selectors
import signal
import stat
import subprocess
import threading
import time
import uuid
import shutil


_BWRAP = Path("/usr/bin/bwrap")
_PRLIMIT = Path("/usr/bin/prlimit")
_PYTHON = Path("/usr/bin/python3")
_MAX_FILE_BYTES = 4 * 1024 * 1024
_MAX_SOURCE_BYTES = 64 * 1024 * 1024
_MAX_SOURCE_ENTRIES = 20_000
_MAX_SOURCE_DEPTH = 64
_MAX_REPLACEMENT_BYTES = 1024 * 1024
_MAX_CAPTURE_BYTES = 1024 * 1024
_MAX_TIMEOUT_SECONDS = 120.0

# Run inside the unchanged read-only /work sandbox. Unittest's explicit top
# directory requires tests/__init__.py; ordinary flat test directories do not.
# Import the trusted stdlib runner before adding the project import root.
_UNITTEST_DRIVER = """import sys, unittest
from pathlib import Path
sys.path.insert(0, '/work')
args = ['unittest', 'discover', '-s', 'tests', '-v']
if Path('/work/tests/__init__.py').is_file():
    args += ['-t', '.']
program = unittest.main(module=None, argv=args, exit=False)
if program.result.testsRun == 0:
    print('No test cases found; an empty suite is not a successful verification.', file=sys.stderr)
    sys.exit(1)
sys.exit(0 if program.result.wasSuccessful() else 1)
"""


class ToolRejected(ValueError):
    """The registered operation does not fit its grant or execution boundary."""


class _MissingParent(ToolRejected):
    """A missing ancestor, distinct from a symlink or invalid directory."""


@dataclass(frozen=True)
class Grant:
    edit_paths: tuple[str, ...]
    allow_tests: bool
    create_paths: tuple[str, ...] = ()
    read_paths: tuple[str, ...] = ()
    capture_paths: tuple[str, ...] = ()
    interact_paths: tuple[str, ...] = ()
    asset_paths: tuple[str, ...] = ()
    command_names: tuple[str, ...] = ()
    allow_shell: bool = False
    mode_paths: tuple[str, ...] = ()
    mode_mask: int = 0
    output_paths: tuple[str, ...] = ()
    project_files: bool = False
    remote_targets: tuple[str, ...] = ()

    def permits_file(self, permission, path):
        relative = _relative_path(path)
        if self.project_files and permission in ("read_paths", "edit_paths", "create_paths"):
            return ".git" not in PurePosixPath(relative).parts and len(relative.encode("utf8")) <= 4096
        return relative in getattr(self, permission)

    def has_file_scope(self, permission):
        return bool(getattr(self, permission)) or (self.project_files and permission in ("read_paths", "edit_paths", "create_paths"))

    def __post_init__(self):
        if type(self.project_files) is not bool:
            raise ToolRejected("project file access must be an exact host boolean")
        if type(self.allow_shell) is not bool:
            raise ToolRejected("allow_shell must be an exact boolean")
        if type(self.allow_tests) is not bool:
            raise ToolRejected("allow_tests must be an exact boolean")
        for field in ("edit_paths", "create_paths", "read_paths", "capture_paths", "interact_paths", "asset_paths", "mode_paths", "output_paths"):
            values = getattr(self, field)
            if isinstance(values, (str, bytes)):
                raise ToolRejected(f"{field} must be a sequence of relative paths")
            try:
                paths = tuple(_relative_path(value) for value in values)
            except TypeError as exc:
                raise ToolRejected(f"{field} must be an iterable of relative paths") from exc
            if len(set(paths)) != len(paths):
                raise ToolRejected(f"{field} contains duplicates")
            object.__setattr__(self, field, paths)
        if (type(self.mode_mask) is not int or not 0<=self.mode_mask<=0o777
                or bool(self.mode_paths)!=bool(self.mode_mask)
                or any(path not in self.read_paths for path in self.mode_paths)):
            raise ToolRejected("mode changes require explicit readable paths and a basic-permission mask")
        if self.output_paths:
            from .command_outputs import validate_paths
            validate_paths(self.output_paths,self.read_paths)
            if not self.allow_shell and not self.command_names:
                raise ToolRejected("command outputs require a command capability")
        import re
        if (type(self.command_names) is not tuple or len(self.command_names)>32
                or any(type(v) is not str or re.fullmatch('[A-Za-z][A-Za-z0-9_-]{0,31}',v) is None for v in self.command_names)
                or len(set(self.command_names))!=len(self.command_names)):
            raise ToolRejected('bounded immutable command-name grants required')
        if (type(self.remote_targets) is not tuple or len(self.remote_targets)>32 or len(set(self.remote_targets))!=len(self.remote_targets)
                or any(type(v) is not str or re.fullmatch('[A-Za-z][A-Za-z0-9_-]{0,127}',v) is None for v in self.remote_targets)):
            raise ToolRejected('bounded immutable remote target grants required')
        from .browser_assets import BrowserAsset
        if len(self.asset_paths)>64:raise ToolRejected('asset allowlist exceeds64 paths')
        for path in self.asset_paths:
            if path not in self.read_paths:raise ToolRejected('assets require explicit read grants')
            try:BrowserAsset(path,b'')
            except ValueError as exc:raise ToolRejected('invalid asset path: '+str(exc)) from exc
        if any(path not in self.capture_paths or path not in self.read_paths for path in self.interact_paths):
            raise ToolRejected("interaction paths require explicit capture and read grants")


@dataclass(frozen=True)
class ArtifactRef:
    """Immutable reference to output stored outside the exposed source tree."""

    path: Path
    sha256: str
    size_bytes: int

    def read_bytes(self) -> bytes:
        data = self.path.read_bytes()
        if len(data) != self.size_bytes or hashlib.sha256(data).hexdigest() != self.sha256:
            raise OSError("captured artifact changed after publication")
        return data


@dataclass(frozen=True)
class ToolResult:
    operation_id: str
    disposition: str
    exit_code: int | None
    elapsed_seconds: float
    stdout: ArtifactRef
    stderr: ArtifactRef


@dataclass(frozen=True)
class PageCaptureResult:
    operation_id: str
    source_path: str
    source: ArtifactRef
    image: ArtifactRef
    viewport: tuple[int, int]
    browser_version: str
    chromium_sandbox: bool
    url: str
    http_status: int
    served_sha256: str
    elapsed_seconds: float
    isolation: dict | None = None
    inspection: dict | None = None
    actions: tuple = ()
    text: str = ""
    asset_manifest: tuple = ()
    served_assets: tuple = ()
    assets: tuple = ()
    document_path: str = "index.html"
    runtime_errors: tuple[str, ...] = ()
    viewport_name: str | None = None



class BrowserExecutionError(ToolRejected):
    """A failed candidate page held in memory after proven browser retirement.

    Direct callers get an error without artifact publication. Only the workflow
    registry publishes this exact observation; it never reruns the browser.
    """
    def __init__(self,capture,*,executor,operation_id,source_path,source_bytes,assets,elapsed_seconds,viewport_name=None):
        from .browser_capture import RenderedPage
        witness=capture.isolation if isinstance(capture,RenderedPage) else None
        errors=capture.runtime_errors if isinstance(capture,RenderedPage) else None
        if (not isinstance(capture,RenderedPage)
                or type(errors) is not tuple or not 1<=len(errors)<=16
                or any(type(error) is not str or not 0<len(error)<=1024 for error in errors)
                or type(witness) is not dict
                or witness.get('kind')!='bubblewrap-browser-v1'
                or witness.get('chromium_sandbox') is not True
                or witness.get('worker_exited') is not True
                or witness.get('namespace_members_after')!=[]
                or type(source_bytes) is not bytes
                or capture.http_status!=200 or capture.served_sha256!=hashlib.sha256(source_bytes).hexdigest()
                or tuple(a.manifest for a in assets)!=capture.asset_manifest):
            raise ValueError('complete settled browser error receipt required')
        selected=executor._browser.for_viewport(viewport_name)
        self.viewport=(selected.width,selected.height)
        self.viewport_name=selected.name_for_size(*self.viewport)
        from PIL import Image
        import io
        with Image.open(io.BytesIO(capture.png)) as image:
            if image.size!=self.viewport:raise ValueError('settled browser error viewport differs')
        self.capture=capture
        self.executor=executor
        self.operation_id=operation_id
        self.source_path=source_path
        self.source_bytes=source_bytes
        self.assets=assets
        self.elapsed_seconds=elapsed_seconds
        super().__init__('page execution failed: '+errors[0][:256])


def _relative_path(value: str) -> str:
    if not isinstance(value, str) or not value or "\x00" in value or "\\" in value:
        raise ToolRejected("path must be a nonempty POSIX relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise ToolRejected("path escapes or is not relative to the workspace")
    normalized = path.as_posix()
    if normalized != value:
        raise ToolRejected("path must use canonical POSIX spelling")
    return normalized


def _operation_id(value: str) -> str:
    if (not isinstance(value, str) or not value or len(value) > 128
            or any(ord(char) < 0x20 or ord(char) == 0x7f for char in value)):
        raise ToolRejected("operation_id must be a bounded printable string")
    return value


def _copy_directory(source_fd: int, destination: Path, budget: list[int], depth: int = 0, *, project_input=False) -> None:
    """Copy an already-open directory without following links or special files."""
    if depth > _MAX_SOURCE_DEPTH:
        raise ToolRejected("source directory nesting exceeds the registered depth limit")
    directory_before = os.fstat(source_fd)
    with os.scandir(source_fd) as entries:
        for entry in entries:
            if entry.name == ".git":
                if project_input:continue  # Never inspect/follow shared Git administration.
                raise ToolRejected("source may not include Git administration data")
            budget[0] += 1
            if budget[0] > _MAX_SOURCE_ENTRIES:
                raise ToolRejected("source contains too many filesystem entries")
            info = entry.stat(follow_symlinks=False)
            if stat.S_ISLNK(info.st_mode):
                raise ToolRejected(f"source contains a symlink: {entry.name}")
            target = destination / entry.name
            if stat.S_ISDIR(info.st_mode):
                target.mkdir(mode=0o755)
                child_fd = os.open(entry.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                   dir_fd=source_fd)
                try:
                    opened = os.fstat(child_fd)
                    if (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino):
                        raise ToolRejected("source directory changed during workspace copy")
                    _copy_directory(child_fd, target, budget, depth + 1, project_input=project_input)
                    os.chmod(target, stat.S_IMODE(opened.st_mode) & 0o777)
                finally:
                    os.close(child_fd)
            elif stat.S_ISREG(info.st_mode):
                if info.st_size > _MAX_FILE_BYTES:
                    raise ToolRejected(f"source file exceeds the registered file limit: {entry.name}")
                budget[1] += info.st_size
                if budget[1] > _MAX_SOURCE_BYTES:
                    raise ToolRejected("source exceeds the registered total byte limit")
                source_file = os.open(entry.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=source_fd)
                try:
                    opened = os.fstat(source_file)
                    if (not stat.S_ISREG(opened.st_mode)
                            or (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino)):
                        raise ToolRejected("source file changed during workspace copy")
                    mode = stat.S_IMODE(opened.st_mode) & 0o777
                    output_fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                    try:
                        with os.fdopen(os.dup(source_file), "rb") as reader, os.fdopen(output_fd, "wb") as writer:
                            output_fd = -1
                            copied = 0
                            while block := reader.read(min(1024 * 1024, _MAX_FILE_BYTES + 1 - copied)):
                                copied += len(block)
                                if copied > _MAX_FILE_BYTES:
                                    raise ToolRejected("source file grew past the registered file limit")
                                writer.write(block)
                            writer.flush()
                            os.fchmod(writer.fileno(), mode)
                            os.fsync(writer.fileno())
                        after = os.fstat(source_file)
                        if (copied != opened.st_size
                                or (after.st_size, after.st_mtime_ns) != (opened.st_size, opened.st_mtime_ns)):
                            raise ToolRejected("source file changed during workspace copy")
                    finally:
                        if output_fd >= 0:
                            os.close(output_fd)
                finally:
                    os.close(source_file)
            else:
                raise ToolRejected(f"source contains a non-regular entry: {entry.name}")
    directory_after = os.fstat(source_fd)
    if ((directory_before.st_dev, directory_before.st_ino, directory_before.st_mtime_ns)
            != (directory_after.st_dev, directory_after.st_ino, directory_after.st_mtime_ns)):
        raise ToolRejected("source directory changed during workspace copy")


class Executor:
    """Owns a copied workspace, granted file tools and isolated execution."""

    def __init__(self, source: Path, run_dir: Path, workspace: Path, *, browser=None, commands=(), shell=None):
        if browser is not None:
            from branchwrite.browser_capture import BrowserConfig
            if not isinstance(browser, BrowserConfig):
                raise ToolRejected("browser configuration must be host-owned BrowserConfig")
        from .terminal import command_table
        self._commands = command_table(commands)
        from .terminal import ShellConfig
        if shell is not None and not isinstance(shell,ShellConfig):raise ToolRejected("host ShellConfig required")
        self._shell = shell
        self._browser = browser
        self.source = source
        self.run_dir = run_dir
        self.workspace = workspace
        self.artifacts = run_dir / "artifacts"
        self._lock = threading.RLock()
        info = workspace.lstat()
        if not stat.S_ISDIR(info.st_mode):
            raise ToolRejected("workspace must be an owned directory")
        self._workspace_identity = (info.st_dev, info.st_ino)

    @classmethod
    def create(cls, source, run_dir, *, browser=None, commands=(), shell=None, project_input=False):
        from .terminal import command_table
        commands = command_table(commands)
        from .terminal import ShellConfig
        if shell is not None and not isinstance(shell,ShellConfig):raise ToolRejected("host ShellConfig required")
        if type(project_input) is not bool:raise ToolRejected('explicit project input policy required')
        source_input = Path(source).expanduser().absolute()
        try:
            source_info = source_input.lstat()
        except OSError as exc:
            raise ToolRejected("source directory is unavailable") from exc
        if stat.S_ISLNK(source_info.st_mode) or not stat.S_ISDIR(source_info.st_mode):
            raise ToolRejected("source must be a real directory, not a link")
        source_path = source_input.resolve(strict=True)
        source_info = source_path.lstat()
        run_path = Path(run_dir).expanduser().absolute()
        run_parent = run_path.parent.resolve(strict=True)
        run_path = run_parent / run_path.name
        try:
            run_path.relative_to(source_path)
        except ValueError:
            pass
        else:
            raise ToolRejected("run directory must be outside the input source")
        if source_path == run_path or source_path.is_relative_to(run_path):
            raise ToolRejected("source and run directory overlap")
        if run_path.exists() or run_path.is_symlink():
            raise ToolRejected("run directory already exists")

        created_by_this_call = False
        created_identity = None
        try:
            run_path.mkdir(mode=0o700)
            created_by_this_call = True
            created_info = run_path.lstat()
            created_identity = (created_info.st_dev, created_info.st_ino)
            workspace = run_path / "workspace"
            workspace.mkdir(mode=0o700)
            artifact_dir = run_path / "artifacts"
            artifact_dir.mkdir(mode=0o700)
            source_fd = os.open(source_path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                opened = os.fstat(source_fd)
                if (opened.st_dev, opened.st_ino) != (source_info.st_dev, source_info.st_ino):
                    raise ToolRejected("source directory changed during workspace creation")
                _copy_directory(source_fd, workspace, [0, 0], project_input=project_input)
            finally:
                os.close(source_fd)
        except BaseException:
            if created_by_this_call and created_identity is not None:
                try:
                    current_info = run_path.lstat()
                    if (stat.S_ISDIR(current_info.st_mode)
                            and (current_info.st_dev, current_info.st_ino) == created_identity):
                        shutil.rmtree(run_path)
                except FileNotFoundError:
                    pass
            raise
        return cls(source_path, run_path, workspace, browser=browser, commands=commands, shell=shell)

    def _artifact(self, payload: bytes) -> ArtifactRef:
        name = uuid.uuid4().hex + ".bin"
        path = self.artifacts / name
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(path, 0o400)
        descriptor = os.open(self.artifacts, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        return ArtifactRef(path, hashlib.sha256(payload).hexdigest(), len(payload))

    def _result(self, operation_id, disposition, exit_code, started, stdout, stderr):
        return ToolResult(operation_id, disposition, exit_code,
                          max(0.0, time.monotonic() - started),
                          self._artifact(stdout), self._artifact(stderr))

    @contextmanager
    def _parent_directory(self, relative, *, create_missing=False):
        """Pin parents without following links; reads never create directories.

        Only create_file, after checking its exact leaf grant and depth, may
        create the necessary missing parents. Host actions are serialized;
        same-UID hostile processes still require the registered OS sandbox.
        On failure remove only newly created, still-identical empty directories.
        A published file or unresolved side effect is never undone or retried.
        """
        descriptor = None
        created = []
        try:
            try:
                descriptor = os.open(self.workspace, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
                info = os.fstat(descriptor)
                if (info.st_dev, info.st_ino) != self._workspace_identity:
                    raise ToolRejected("owned workspace directory was replaced")
                for part in PurePosixPath(relative).parts[:-1]:
                    try:
                        child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                        dir_fd=descriptor)
                    except FileNotFoundError as exc:
                        if not create_missing:
                            raise _MissingParent("workspace parent is missing") from exc
                        os.mkdir(part, 0o700, dir_fd=descriptor)
                        made = os.stat(part, dir_fd=descriptor, follow_symlinks=False)
                        identity = (made.st_dev, made.st_ino)
                        created.append((os.dup(descriptor), part, identity))
                        os.fsync(descriptor)
                        child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                        dir_fd=descriptor)
                        opened = os.fstat(child)
                        if (opened.st_dev, opened.st_ino) != identity:
                            os.close(child)
                            raise ToolRejected("new workspace parent was replaced")
                    os.close(descriptor)
                    descriptor = child
            except OSError as exc:
                raise ToolRejected("workspace parent is unavailable or is a link") from exc
            yield descriptor, PurePosixPath(relative).name
        except BaseException:
            for parent, name, identity in reversed(created):
                try:
                    info = os.stat(name, dir_fd=parent, follow_symlinks=False)
                    if stat.S_ISDIR(info.st_mode) and (info.st_dev, info.st_ino) == identity:
                        os.rmdir(name, dir_fd=parent)
                        os.fsync(parent)
                except OSError:
                    # Nonempty/replaced/unavailable means uncertain effects;
                    # leave it for the existing operation reconciliation path.
                    pass
            raise
        finally:
            if descriptor is not None:
                os.close(descriptor)
            for parent, _, _ in created:
                os.close(parent)

    def create_file(self, operation_id, grant, path, payload):
        """Publish bounded bytes without ever replacing an existing name.

        The exact granted leaf also permits its missing private parent directories;
        it does not grant sibling paths or directory replacement. Existing parent
        modes are preserved. A returned result acknowledges a completed operation.
        If artifact publication fails after the file is linked, it may already exist;
        callers must reconcile by reading, not retry with an overwrite.
        """
        operation_id = _operation_id(operation_id)
        if not isinstance(grant, Grant):
            raise ToolRejected("a host Grant is required")
        relative = _relative_path(path)
        if not grant.permits_file("create_paths", relative):
            raise ToolRejected("creation path is not permitted by the host grant")
        if type(payload) is not bytes or len(payload) > _MAX_FILE_BYTES:
            raise ToolRejected("creation requires bytes within the registered file limit")
        if len(PurePosixPath(relative).parts) - 1 > _MAX_SOURCE_DEPTH:
            raise ToolRejected("creation parent depth exceeds the source tree limit")
        with self._lock, self._parent_directory(relative, create_missing=True) as (parent, name):
            started = time.monotonic()
            temporary = ".bw-create-" + uuid.uuid4().hex + ".tmp"
            descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                 0o600, dir_fd=parent)
            try:
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(payload)
                    stream.flush()
                    os.fsync(stream.fileno())
                try:
                    # Unlike replace/rename, link fails atomically on collision.
                    os.link(temporary, name, src_dir_fd=parent, dst_dir_fd=parent,
                            follow_symlinks=False)
                except FileExistsError as exc:
                    raise ToolRejected("creation target already exists") from exc
            finally:
                os.unlink(temporary, dir_fd=parent)
            os.fsync(parent)
            return self._result(operation_id, "created", 0, started, b"file created\n", b"")

    def read_file(self, operation_id, grant, path):
        """Read actual bounded file bytes and publish a hashed output artifact."""
        operation_id = _operation_id(operation_id)
        if not isinstance(grant, Grant):
            raise ToolRejected("a host Grant is required")
        relative = _relative_path(path)
        if not grant.permits_file("read_paths", relative):
            raise ToolRejected("read path is not permitted by the host grant")
        with self._lock:
            started = time.monotonic()
            payload = self._read_private_bytes(relative)
            return self._result(operation_id, "read", 0, started, payload, b"")

    def _read_private_bytes(self, relative):
        """Caller holds the executor lock; return a stable no-follow read."""
        with self._parent_directory(relative) as (parent, name):
            try:
                descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                                     dir_fd=parent)
            except OSError as exc:
                raise ToolRejected("read target is unavailable or is a link") from exc
            try:
                before = os.fstat(descriptor)
                if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                        or before.st_size > _MAX_FILE_BYTES):
                    raise ToolRejected("read target is not a bounded private regular file")
                payload = bytearray()
                while block := os.read(descriptor, min(65536, _MAX_FILE_BYTES + 1 - len(payload))):
                    payload.extend(block)
                    if len(payload) > _MAX_FILE_BYTES:
                        raise ToolRejected("read target grew beyond the registered file limit")
                after = os.fstat(descriptor)
                fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns", "st_nlink")
                if (len(payload) != before.st_size
                        or any(getattr(before, field) != getattr(after, field) for field in fields)):
                    raise ToolRejected("read target changed while reading")
            finally:
                os.close(descriptor)
            return bytes(payload)

    def _browser_assets(self,grant):
        """Read only explicit host-authorized resources, through private no-follow IO."""
        from .browser_assets import BrowserAsset,validate_assets
        if not isinstance(grant,Grant):raise ToolRejected('host Grant required')
        try:
            return validate_assets(tuple(BrowserAsset(path,self._read_private_bytes(path))
                                         for path in grant.asset_paths))
        except ValueError as exc:
            raise ToolRejected('invalid captured resource bundle: '+str(exc)) from exc

    def capture_page(self, operation_id, grant, path, expected_sha256, *, viewport=None):
        return self._capture_page(operation_id, grant, path, expected_sha256,viewport=viewport)

    def interact_page(self, operation_id, grant, path, expected_sha256, actions, *, viewport=None):
        from .browser_capture import page_action_recipe
        try:
            actions = page_action_recipe(actions)
        except (ValueError, TypeError) as exc:
            raise ToolRejected('invalid browser action recipe: ' + str(exc)) from exc
        return self._capture_page(operation_id, grant, path, expected_sha256, actions=actions,viewport=viewport)

    def _capture_page(self, operation_id, grant, path, expected_sha256, *, actions=None,viewport=None):
        """Render exactly the authorized source revision; publish actual pixels.

        The capture worker runs in its own filesystem/network/PID namespaces
        with no host home, credentials, service sockets or GPU devices mounted.
        Chromium's renderer sandbox is also mandatory. Only an explicitly captured
        document/resource bundle is admitted; interaction requires its own grant and bounded recipe.
        Capture permission is distinct from permission to read/edit/test files.
        """
        operation_id = _operation_id(operation_id)
        relative = _relative_path(path)
        paths = 'capture_paths' if actions is None else 'interact_paths'
        if not isinstance(grant, Grant) or relative not in getattr(grant, paths):
            raise ToolRejected("browser operation is not permitted by the host grant")
        if self._browser is None:
            raise ToolRejected("no host browser is configured")
        if self._browser.actions or (actions is not None and self._browser.inspection is not None):
            raise ToolRejected("host tool browser cannot contain hidden actions or inspection")
        from dataclasses import replace
        try:selected=self._browser.for_viewport(viewport)
        except ValueError as exc:raise ToolRejected(str(exc)) from exc
        name=selected.name_for_size(selected.width,selected.height)
        browser=selected if actions is None else replace(selected,actions=actions)
        if (type(expected_sha256) is not str or len(expected_sha256) != 64
                or any(char not in "0123456789abcdef" for char in expected_sha256)):
            raise ToolRejected("capture requires an exact lowercase source SHA-256")
        with self._lock:
            started = time.monotonic()
            payload = self._read_private_bytes(relative)
            if hashlib.sha256(payload).hexdigest() != expected_sha256:
                raise ToolRejected("capture source revision is stale")
            from branchwrite.browser_capture import render_snapshot
            try:
                assets=self._browser_assets(grant)
                rendered = render_snapshot(payload, browser,assets=assets,document_path=relative)
            except Exception as exc:
                raise ToolRejected("browser capture failed: " + str(exc)[:512]) from exc
            elapsed=time.monotonic()-started
            if rendered.runtime_errors:
                raise BrowserExecutionError(rendered,executor=self,operation_id=operation_id,
                    source_path=relative,source_bytes=payload,assets=assets,elapsed_seconds=elapsed,viewport_name=name)
            return self._publish_page_capture(operation_id,relative,payload,assets,rendered,elapsed,size=(browser.width,browser.height),viewport_name=name)

    def _publish_page_capture(self,operation_id,relative,payload,assets,rendered,elapsed_seconds,*,size,viewport_name=None):
        """Publish one already observed byte bundle; no browser execution here."""
        return PageCaptureResult(operation_id,relative,self._artifact(payload),
            self._artifact(rendered.png),size,
            rendered.browser_version,True,rendered.url,rendered.http_status,
            rendered.served_sha256,elapsed_seconds,rendered.isolation,
            rendered.inspection,rendered.actions,rendered.text,rendered.asset_manifest,
            rendered.served_assets,tuple(self._artifact(a.body) for a in assets),
            rendered.document_path,rendered.runtime_errors,viewport_name)

    def _publish_browser_error(self,error,operation_id,path,*,viewport=None):
        """The registry may retain only this Executor's original failed capture."""
        if (not isinstance(error,BrowserExecutionError) or error.executor is not self
                or error.operation_id!=operation_id or error.source_path!=path):
            raise ValueError('browser error belongs to another operation or world')
        selected=self._browser.for_viewport(viewport)
        if error.viewport!=(selected.width,selected.height) or error.viewport_name!=selected.name_for_size(selected.width,selected.height):
            raise ValueError('browser error viewport differs from original observation')
        with self._lock:
            return self._publish_page_capture(operation_id,path,error.source_bytes,
                error.assets,error.capture,error.elapsed_seconds,size=error.viewport,viewport_name=error.viewport_name)


    @staticmethod
    def _replacement_bytes(original, before, after):
        """Pure edit admission, shared by planning and the final write boundary.

        A nonmatching/ambiguous edit is safe to reject before external execution.
        This does not classify exceptions after write entry as safe to retry.
        """
        if not isinstance(before, bytes) or not before or not isinstance(after, bytes):
            raise ToolRejected("replacement requires nonempty byte preimage and byte replacement")
        if len(before) > _MAX_REPLACEMENT_BYTES or len(after) > _MAX_REPLACEMENT_BYTES:
            raise ToolRejected("replacement exceeds the registered byte limit")
        if original.count(before) != 1:
            raise ToolRejected("exact preimage must occur once in the target")
        updated = original.replace(before, after, 1)
        if len(updated) > _MAX_FILE_BYTES:
            raise ToolRejected("replacement would exceed the registered file limit")
        return updated

    def set_mode(self, operation_id, grant, path, expected_sha, mode):
        """Change only granted permission bits on one observed private file.

        This is a descriptor-based metadata operation,not a shell escape.
        The exact mask is host authority. File bytes are read and checked on
        the same descriptor before and after fchmod,even if read access is removed.
        """
        import json
        operation_id=_operation_id(operation_id)
        relative=_relative_path(path)
        if not isinstance(grant,Grant) or relative not in grant.mode_paths:
            raise ToolRejected("mode path is not permitted")
        if (type(mode) is not str or len(mode)!=4 or mode[0]!='0'
                or any(c not in '01234567' for c in mode)):
            raise ToolRejected("mode requires four octal digits without special bits")
        if (type(expected_sha) is not str or len(expected_sha)!=64
                or any(c not in '0123456789abcdef' for c in expected_sha)):
            raise ToolRejected("mode requires an exact observed SHA256")
        desired=int(mode,8)
        with self._lock,self._parent_directory(relative) as (parent,name):
            started=time.monotonic()
            try:fd=os.open(name,os.O_RDONLY|os.O_NONBLOCK|os.O_NOFOLLOW,dir_fd=parent)
            except OSError as exc:raise ToolRejected("mode target is unavailable or a link") from exc
            try:
                before=os.fstat(fd);old=stat.S_IMODE(before.st_mode)
                if (not stat.S_ISREG(before.st_mode) or before.st_nlink!=1
                        or before.st_size>_MAX_FILE_BYTES or old&~0o777):
                    raise ToolRejected("mode target must be a bounded private basic-mode regular file")
                if (desired^old)&~grant.mode_mask:
                    raise ToolRejected("mode change exceeds the host bit mask")
                def read_body():
                    os.lseek(fd,0,os.SEEK_SET);data=bytearray()
                    while chunk:=os.read(fd,min(65536,_MAX_FILE_BYTES+1-len(data))):
                        data.extend(chunk)
                        if len(data)>_MAX_FILE_BYTES:raise ToolRejected("mode target exceeds file bound")
                    return bytes(data)
                body=read_body()
                entry=os.stat(name,dir_fd=parent,follow_symlinks=False)
                if ((entry.st_dev,entry.st_ino)!=(before.st_dev,before.st_ino)
                        or len(body)!=before.st_size or hashlib.sha256(body).hexdigest()!=expected_sha):
                    raise ToolRejected("mode target preimage is stale")
                stable=os.fstat(fd)
                fields=('st_dev','st_ino','st_size','st_mtime_ns','st_ctime_ns','st_nlink','st_mode')
                if any(getattr(before,k)!=getattr(stable,k) for k in fields):
                    raise ToolRejected("mode target changed before mutation")
                os.fchmod(fd,desired);os.fsync(fd);os.fsync(parent)
                after=os.fstat(fd);entry=os.stat(name,dir_fd=parent,follow_symlinks=False)
                if (stat.S_IMODE(after.st_mode)!=desired or after.st_nlink!=1
                        or (entry.st_dev,entry.st_ino)!=(before.st_dev,before.st_ino)
                        or read_body()!=body):
                    raise OSError("mode change postcondition is indeterminate")
                payload=json.dumps(dict(path=relative,before_mode=format(old,'04o'),
                    after_mode=mode,content_sha256=expected_sha),sort_keys=True).encode()
                return self._result(operation_id,"mode_changed",0,started,payload,b"")
            finally:os.close(fd)

    def replace(self, operation_id, grant, path, expected_sha, before, after):
        if not isinstance(before, bytes):
            raise ToolRejected("replacement requires a nonempty byte preimage")
        return self._replace_bytes(operation_id, grant, path, expected_sha, before, after)

    def replace_file(self, operation_id, grant, path, expected_sha, payload):
        """Replace one observed whole file; preserve its existing mode.

        The line-based tool resolves to ordinary bytes before this boundary.
        An empty original file remains a valid full-file replacement target.
        """
        if type(payload) is not bytes or len(payload) > _MAX_FILE_BYTES:
            raise ToolRejected("full replacement requires bytes within the file limit")
        return self._replace_bytes(operation_id, grant, path, expected_sha, None, payload)

    def _replace_bytes(self, operation_id, grant, path, expected_sha, before, after):
        operation_id = _operation_id(operation_id)
        if not isinstance(grant, Grant):
            raise ToolRejected("a host Grant is required")
        relative = _relative_path(path)
        if not grant.permits_file("edit_paths", relative):
            raise ToolRejected("path is not permitted by the host grant")
        if (not isinstance(expected_sha, str) or len(expected_sha) != 64
                or any(char not in "0123456789abcdef" for char in expected_sha.lower())):
            raise ToolRejected("expected_sha must be a SHA-256 digest")
        with self._lock:
            target = self._workspace_file(relative)
            info = target.stat(follow_symlinks=False)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > _MAX_FILE_BYTES:
                raise ToolRejected("target is not a private regular workspace file")
            original = target.read_bytes()
            if hashlib.sha256(original).hexdigest() != expected_sha.lower():
                raise ToolRejected("target preimage digest is stale")
            updated = after if before is None else self._replacement_bytes(original, before, after)
            started = time.monotonic()
            temporary = target.with_name("." + target.name + "." + uuid.uuid4().hex + ".tmp")
            mode = stat.S_IMODE(info.st_mode) & 0o777
            fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         mode or 0o600)
            try:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(updated)
                    stream.flush()
                    # Creation modes are filtered by umask. Restore the original
                    # file's exact basic permissions on this owned descriptor.
                    os.fchmod(stream.fileno(), mode)
                    os.fsync(stream.fileno())
                os.replace(temporary, target)
                dir_fd = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    os.fsync(dir_fd)
                finally:
                    os.close(dir_fd)
            except BaseException:
                try:
                    temporary.unlink()
                except FileNotFoundError:
                    pass
                raise
            return self._result(operation_id, "applied", 0, started,
                                b"replacement applied\n", b"")

    def _workspace_file(self, relative: str) -> Path:
        current = self.workspace
        parts = PurePosixPath(relative).parts
        for part in parts[:-1]:
            current = current / part
            info = current.lstat()
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
                raise ToolRejected("workspace path traverses a non-directory or symlink")
        target = current / parts[-1]
        info = target.lstat()
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
            raise ToolRejected("workspace target must be a regular non-symlink file")
        return target

    @staticmethod
    def _sandbox_command(workspace: Path, timeout: float) -> list[str]:
        for executable in (_BWRAP, _PRLIMIT, _PYTHON):
            if not executable.is_file() or not os.access(executable, os.X_OK):
                raise ToolRejected(f"required sandbox executable is unavailable: {executable}")
        # prlimit applies per process; it is not an aggregate process-tree memory cap.
        # Bubblewrap also gives tests a fresh 64 MiB /tmp, with no host home/network mount.
        cpu_limit = max(1, math.ceil(timeout))
        memory_limit = 2 * 1024 * 1024 * 1024
        file_limit = 16 * 1024 * 1024
        return [str(_PRLIMIT), f"--cpu={cpu_limit}", f"--as={memory_limit}",
            f"--fsize={file_limit}", "--core=0", "--",
            str(_BWRAP), "--die-with-parent", "--new-session", "--unshare-all", "--unshare-user",
            "--disable-userns", "--cap-drop", "ALL", "--clearenv",
            "--ro-bind", "/usr", "/usr", "--ro-bind", "/lib", "/lib",
            "--ro-bind", "/lib64", "/lib64",
            "--symlink", "usr/bin", "/bin",
            "--dir", "/work", "--ro-bind", str(workspace), "/work",
            "--proc", "/proc", "--dev", "/dev", "--size", "67108864", "--tmpfs", "/tmp",
            "--chmod", "1777", "/tmp", "--chdir", "/work", "--",
            str(_PYTHON), "-I", "-B", "-c", _UNITTEST_DRIVER]

    @staticmethod
    def _signal_group(process, sig):
        try:
            os.killpg(process.pid, sig)
        except ProcessLookupError:
            pass

    @staticmethod
    def _capture(process, deadline: float, limit: int):
        selector = selectors.DefaultSelector()
        streams = {process.stdout: bytearray(), process.stderr: bytearray()}
        for stream in streams:
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ)
        started = time.monotonic()
        termination_started = None
        limited = False
        timed_out = False
        while selector.get_map() or process.poll() is None:
            now = time.monotonic()
            if now >= deadline and termination_started is None:
                timed_out = True
                termination_started = now
                Executor._signal_group(process, signal.SIGTERM)
            if limited and termination_started is None:
                termination_started = now
                Executor._signal_group(process, signal.SIGTERM)
            if termination_started is not None and now - termination_started >= 0.25:
                Executor._signal_group(process, signal.SIGKILL)
            events = selector.select(0.025 if termination_started is None else 0.01)
            for key, _ in events:
                stream = key.fileobj
                try:
                    data = os.read(stream.fileno(), 65536)
                except BlockingIOError:
                    continue
                if not data:
                    selector.unregister(stream)
                    stream.close()
                    continue
                captured = streams[stream]
                remaining = max(0, limit - len(captured))
                captured.extend(data[:remaining])
                if len(data) > remaining:
                    limited = True
            if termination_started is not None and now - termination_started > 2.0:
                for stream in tuple(streams):
                    try:
                        selector.unregister(stream)
                        stream.close()
                    except (KeyError, OSError):
                        pass
                break
        selector.close()
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            Executor._signal_group(process, signal.SIGKILL)
            process.kill()
            process.wait(timeout=2)
        return (bytes(streams[process.stdout]), bytes(streams[process.stderr]),
                timed_out, limited, time.monotonic() - started)

    def check_shell_boundary(self):
        """Probe the real shell sandbox with no project code or input files.

        This is host admission evidence,never a task ToolOutcome or a successful
        test claim. It cannot satisfy the workflow's completion verifier.
        """
        from .terminal import NamedCommand,_execute_argv
        import secrets
        if self._shell is None:raise ToolRejected('shell sandbox is not configured')
        with self._lock:
            self._shell.check_host()
            probe=NamedCommand('shell-boundary',self._shell._command.argv,5.0)
            argv=probe.argv+('-c',"printf '%s\\n' BW_SHELL_BOUNDARY_READY_V1")
            try:
                result=_execute_argv(self,'bw-shell-boundary-'+secrets.token_hex(16),
                    Grant((),False,allow_shell=True),probe,argv)
            except (OSError,ValueError) as exc:
                raise ToolRejected('registered shell sandbox is unavailable before inference: '+str(exc)[-512:]) from exc
            witness=result.details.get('isolation',{})
            if (result.disposition!='exited' or result.exit_code!=0
                    or result.stdout.read_bytes()!=b'BW_SHELL_BOUNDARY_READY_V1\n'
                    or result.stderr.read_bytes() or witness.get('worker_exited') is not True
                    or witness.get('namespace_members_after')!=[]):
                raise ToolRejected('registered shell sandbox is unavailable before inference; check host namespace permissions')
            return dict(witness)

    def check_test_boundary(self):
        """Probe the actual test sandbox before admitting model or tool work.

        This trusted, isolated command imports no project code. In particular,
        an outer CLI namespace may prohibit the nested namespace required by
        run_tests. Do not spend inference trying to repair that host failure.
        This is admission evidence, not a substitute for executing the tests.
        """
        with self._lock:
            command = self._sandbox_command(self.workspace, 5.0)
            index = command.index(str(_PYTHON))
            command[index:] = [str(_PYTHON), "-I", "-B", "-c",
                "import unittest; print('BW_TEST_BOUNDARY_READY_V1')"]
            try:
                process = subprocess.Popen(command, cwd=self.workspace,
                    env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"},
                    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, close_fds=True, start_new_session=True)
            except OSError as exc:
                raise ToolRejected("registered test sandbox is unavailable before inference") from exc
            stdout, stderr, timed_out, limited, _ = self._capture(
                process, time.monotonic() + 5.0, 16384)
            if (process.returncode != 0 or timed_out or limited
                    or stdout != b"BW_TEST_BOUNDARY_READY_V1\n" or stderr):
                raise ToolRejected("registered test sandbox is unavailable before inference; "
                    "check host namespace permissions and CLI sandbox nesting")

    def run_tests(self, operation_id, grant, timeout=30.0):
        if not isinstance(grant, Grant) or grant.allow_tests is not True:
            raise ToolRejected("registered tests are not permitted by the host grant")
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
            raise ToolRejected("timeout must be a finite positive number")
        timeout = float(timeout)
        if not math.isfinite(timeout) or not 0 < timeout <= _MAX_TIMEOUT_SECONDS:
            raise ToolRejected("timeout is outside the registered bound")
        operation_id = _operation_id(operation_id)
        with self._lock:
            command = self._sandbox_command(self.workspace, timeout)
            started = time.monotonic()
            deadline = started + timeout
            env = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"}
            try:
                process = subprocess.Popen(command, cwd=self.workspace, env=env,
                    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    close_fds=True, start_new_session=True)
            except OSError as exc:
                raise ToolRejected("registered sandbox could not be started") from exc
            stdout, stderr, timed_out, limited, _ = self._capture(
                process, deadline, _MAX_CAPTURE_BYTES)
            if timed_out:
                disposition = "timeout"
            elif limited:
                disposition = "output_limit"
            else:
                disposition = "exited"
            return self._result(operation_id, disposition, process.returncode,
                                started, stdout, stderr)

    def run_command(self, operation_id, grant, name):
        from .terminal import execute_command
        if not isinstance(grant, Grant):raise ToolRejected("host grant required")
        with self._lock:
            return execute_command(self, operation_id, grant, name)

    def run_shell(self, operation_id, grant, command):
        from .terminal import execute_shell
        if not isinstance(grant,Grant):raise ToolRejected("host grant required")
        with self._lock:
            return execute_shell(self,operation_id,grant,command)
