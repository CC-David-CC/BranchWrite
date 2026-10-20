"""Host-owned Git checkpoints and guarded publication; never a model transcript.

Git stores file versions, paired with references to COW and the workflow ledger.
The private Git repository avoids touching the user's index, HEAD or branches.
A multi-file publication is explicitly recoverable, not atomic: durable intent,
preimage checks, per-file replacement, then a durable completion receipt.
"""
from contextlib import contextmanager
from hashlib import sha256
import fcntl
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile
import uuid
from .execution import Executor, _relative_path, _MissingParent
from .project_scope import expand_directories

_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,127}\Z")
_OID = re.compile(r"[0-9a-f]{40}\Z")
_CONTEXT = {"branch", "tip", "root", "revision", "model_contract_id", "execution_profile_id"}


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try: os.fsync(fd)
    finally: os.close(fd)


def _save(path, value):
    fd, name = tempfile.mkstemp(prefix=".publish-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(_json(value)); stream.flush(); os.fsync(stream.fileno())
        os.replace(name, path); _sync_directory(path.parent)
    finally:
        if os.path.exists(name): os.unlink(name)


def _load(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077 or info.st_nlink != 1:
            raise ValueError("publication record must be a private owned regular file")
        raw = stream.read(32 * 1024 * 1024 + 1)
        if len(raw) > 32 * 1024 * 1024: raise ValueError("publication record exceeds bound")
        return json.loads(raw)


class WorkspaceVersions:
    def __init__(self, project, state):
        self.project = Path(project).absolute()
        info = self.project.lstat()
        if not stat.S_ISDIR(info.st_mode) or self.project.is_symlink():
            raise ValueError("project must be a real directory")
        self.project = self.project.resolve(strict=True)
        self.project_identity = (info.st_dev, info.st_ino)
        self.state = Path(state).absolute()
        if self.state.resolve().is_relative_to(self.project) or self.project.is_relative_to(self.state.resolve()):
            raise ValueError("version storage must be outside the project")
        self.state.mkdir(mode=0o700, parents=True, exist_ok=True)
        info = self.state.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError("version storage must be a private owned directory")
        self.git = self.state / "versions.git"
        with self._locked():
            binding = self.state / "project.json"
            expected = dict(schema=1, project=str(self.project), device=self.project_identity[0], inode=self.project_identity[1])
            if binding.exists():
                if _load(binding) != expected: raise ValueError("version storage belongs to a different project")
            else: _save(binding, expected)
            if not self.git.exists():
                self._git("init", "--bare", "--object-format=sha1", str(self.git), initializing=True)
                _sync_directory(self.state)
            elif not self.git.is_dir() or self.git.is_symlink():
                raise ValueError("invalid version repository")

    @contextmanager
    def _locked(self):
        fd = os.open(self.state / "owner.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "rb+") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1:
                raise ValueError("invalid version lock")
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            yield

    def _git(self, *args, data=None, index=None, initializing=False, check=True):
        env = {k:v for k,v in os.environ.items() if not k.startswith("GIT_")}
        env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_SYSTEM="/dev/null",
                   GIT_AUTHOR_NAME="BranchWrite", GIT_AUTHOR_EMAIL="branchwrite@local.invalid",
                   GIT_COMMITTER_NAME="BranchWrite", GIT_COMMITTER_EMAIL="branchwrite@local.invalid")
        if index is not None: env["GIT_INDEX_FILE"] = str(index)
        command = ["git", "-c", "core.hooksPath=/dev/null", "-c", "gc.auto=0", "-c", "core.fsync=all"]
        if not initializing: command += ["--git-dir=" + str(self.git)]
        result = subprocess.run([*command, *args], input=data, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if check and result.returncode:
            raise ValueError("Git version operation failed: " + result.stderr.decode("utf-8", errors="replace")[:4096])
        return result.stdout if check else result

    @staticmethod
    def _name(name):
        if type(name) is not str or not _NAME.fullmatch(name): raise ValueError("invalid version/operation name")
        return name

    @staticmethod
    def _context(context):
        # Empty context is valid before the first inference. Model state itself
        # remains solely in COW; never duplicate token/controller payloads here.
        if context is None: return None
        if type(context) is not dict or not _CONTEXT <= set(context) or set(context) - _CONTEXT - {"mode"}:
            raise ValueError("complete COW context identity required")
        if any(type(context[k]) is not str or not context[k] for k in _CONTEXT - {"revision"}):
            raise ValueError("invalid COW context identity")
        if type(context["revision"]) is not int or context["revision"] < 0:
            raise ValueError("invalid context revision")
        for key in ("tip", "root"):
            if not re.fullmatch(r"[0-9a-f]{64}", context[key]): raise ValueError("invalid snapshot identity")
        if context.get("mode", "append_user") not in ("ask", "append_user"):raise ValueError("invalid context boundary mode")
        return dict(context)

    def _reader(self, project=None):
        path = self.project if project is None else Path(project).resolve(strict=True)
        if path == self.project:
            info = path.lstat()
            if (info.st_dev, info.st_ino) != self.project_identity: raise ValueError("project directory changed")
        return Executor(path, self.state, path)

    def _entry(self, reader, path, *, contents=False):
        _relative_path(path)
        if ".git" in Path(path).parts: raise ValueError("Git administration is not a project file")
        try:
            with reader._parent_directory(path) as (parent, leaf):
                fd = os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
                with os.fdopen(fd, "rb") as stream:
                    before = os.fstat(stream.fileno())
                    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
                        raise ValueError("project contains a link or special file")
                    raw = stream.read(4 * 1024 * 1024 + 1)
                    after = os.fstat(stream.fileno())
                    if len(raw) > 4 * 1024 * 1024: raise ValueError("project file exceeds bound")
                    if (before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                        raise ValueError("project file changed during capture")
                    result = dict(sha256=sha256(raw).hexdigest(), mode=stat.S_IMODE(before.st_mode), size=len(raw))
                    return (result, raw) if contents else result
        except (FileNotFoundError, _MissingParent):
            return (None, None) if contents else None
        except OSError as exc:
            raise ValueError("project file is unavailable or is a link: " + path) from exc

    def capture(self, name, *, context, parent=None, source=None, workflow=None, plan=None, base=None):
        self._name(name); context = self._context(context)
        with self._locked():
            if parent is not None: self.read(parent)
            reader = self._reader(source)
            paths = expand_directories(reader.workspace, ["."])
            files = {}
            for path in paths:
                entry, raw = self._entry(reader, path, contents=True)
                if entry is None: raise ValueError("project file disappeared during capture")
                blob = self._git("hash-object", "-w", "--stdin", "--no-filters", data=raw).decode().strip()
                files[path] = dict(entry, blob=blob)
            if paths != expand_directories(reader.workspace, ["."]): raise ValueError("project inventory changed")
            for path, entry in files.items():
                if self._entry(reader, path) != {k:entry[k] for k in ("sha256", "mode", "size")}:
                    raise ValueError("project changed during capture")
            manifest = dict(schema=1, kind="bw.file-checkpoint", name=name, context=context, parent=parent,
                            files=files, workflow=workflow, plan=plan, base=base)
            ref = "refs/branchwrite/" + name
            old = self._git("rev-parse", "--verify", ref, check=False)
            if old.returncode == 0:
                commit = old.stdout.decode().strip()
                if self.read(commit) != manifest: raise ValueError("checkpoint name already exists with different state")
                return dict(commit=commit, ref=ref, context=context)
            index = self.state / ("index-" + uuid.uuid4().hex)
            try:
                self._git("read-tree", "--empty", index=index)
                records = b"".join((f'{"100755" if entry["mode"] & 0o111 else "100644"} {entry["blob"]}\t{path}').encode() + b"\0" for path, entry in files.items())
                self._git("update-index", "-z", "--index-info", data=records, index=index)
                tree = self._git("write-tree", index=index).decode().strip()
                args = ("-p", parent) if parent else ()
                commit = self._git("commit-tree", tree, *args, data=_json(manifest) + b"\n").decode().strip()
                self._git("update-ref", ref, commit, "0" * 40)
                return dict(commit=commit, ref=ref, context=context)
            finally:
                index.unlink(missing_ok=True)

    def named(self, name):
        self._name(name)
        result=self._git("rev-parse","--verify","refs/branchwrite/"+name,check=False)
        return None if result.returncode else result.stdout.decode().strip()

    def read(self, commit):
        if type(commit) is not str or not _OID.fullmatch(commit): raise ValueError("exact Git commit required")
        raw = self._git("cat-file", "commit", commit)
        manifest = json.loads(raw.split(b"\n\n", 1)[1])
        if manifest.get("schema") != 1 or manifest.get("kind") != "bw.file-checkpoint":
            raise ValueError("not a BranchWrite file checkpoint")
        self._context(manifest["context"])
        for path, entry in manifest["files"].items():
            _relative_path(path)
            if ".git" in Path(path).parts or not _OID.fullmatch(entry["blob"]): raise ValueError("invalid checkpoint file")
            if not re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]): raise ValueError("invalid file hash")
            if type(entry["mode"]) is not int or not 0 <= entry["mode"] <= 0o777: raise ValueError("invalid file mode")
        return manifest

    def explore(self, name, *, context_commit, files_commit, destination):
        self._name(name)
        destination = Path(destination).absolute()
        if destination.resolve().is_relative_to(self.project) or self.project.is_relative_to(destination.resolve()):
            raise ValueError("isolated exploration must be outside the current project")
        with self._locked():
            context = self.read(context_commit)["context"]; self.read(files_commit)
            receipt = self.state / ("explore-" + name + ".json")
            result = dict(schema=1, name=name, path=str(destination), context=context,
                          context_commit=context_commit, file_commit=files_commit,
                          requires_file_observation=context_commit != files_commit)
            intent = self.state / ("explore-intent-" + name + ".json")
            if receipt.exists():
                if _load(receipt) != result: raise ValueError("exploration name belongs to different work")
                if not destination.is_dir(): raise ValueError("saved worktree is missing")
                return result
            if intent.exists():
                if _load(intent) != result: raise ValueError("exploration intent differs")
            else:
                if destination.exists() or destination.is_symlink(): raise ValueError("exploration destination already exists")
                _save(intent, result)
            if destination.exists():
                # Recover only this exact registered creation, never arbitrary files.
                registered=self._git("worktree", "list", "--porcelain", "-z")
                marker=b"worktree "+str(destination).encode()+b"\0HEAD "+files_commit.encode()+b"\0"
                if destination.is_symlink() or marker not in registered:
                    raise ValueError("unsettled exploration destination differs")
            else:
                self._git("worktree", "add", "--detach", str(destination), files_commit)
            # Git retains only the executable bit; restore the captured ordinary
            # permissions before this new worktree becomes a usable source.
            reader=self._reader(destination)
            for path, expected in self.read(files_commit)["files"].items():
                actual=self._entry(reader,path)
                if actual is None or actual["sha256"]!=expected["sha256"] or actual["size"]!=expected["size"]:
                    raise ValueError("worktree file bytes differ during creation")
                with reader._parent_directory(path) as (parent, leaf):
                    fd=os.open(leaf,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=parent)
                    try:os.fchmod(fd,expected["mode"]);os.fsync(fd)
                    finally:os.close(fd)
            _save(receipt, result)
            return result

    @staticmethod
    def _preimage(entry):
        return None if entry is None else {k:entry[k] for k in ("sha256", "mode", "size")}

    def publish(self, operation, before_commit, after_commit, *, observer=None, target=None):
        self._name(operation)
        with self._locked():
            before = self.read(before_commit)["files"]; after = self.read(after_commit)["files"]
            changed = sorted(path for path in before.keys() | after.keys() if before.get(path) != after.get(path))
            intent = dict(schema=1, operation=operation, before=before_commit, after=after_commit, paths=changed, target=str(self.project if target is None else Path(target).resolve(strict=True)))
            path = self.state / ("publish-" + operation + ".json")
            recovering = path.exists()
            if recovering:
                record = _load(path)
                if record.get("intent") != intent: raise ValueError("publication ID belongs to different intent")
                if record.get("status") == "committed": return record
                if record.get("status") != "pending": raise ValueError("invalid publication state")
            selected = self.project if target is None else Path(target).resolve(strict=True)
            if selected != self.project:
                registered = self._git("worktree", "list", "--porcelain", "-z")
                if (b"worktree " + str(selected).encode() + b"\0") not in registered:
                    raise ValueError("publication target is not an owned worktree")
            reader = self._reader(selected)
            # Preflight the entire delta before the first mutation. On recovery,
            # only this already-durable intent admits either before or after.
            for item in changed:
                current = self._entry(reader, item)
                expected = self._preimage(before.get(item)); target = self._preimage(after.get(item))
                if current != expected and not (recovering and current == target):
                    raise ValueError("file changed/conflicts with publication: " + item)
            if not recovering:
                record = dict(intent=intent, status="pending")
                _save(path, record)
                if observer: observer("intent_durable", None)
            for item in changed:
                current = self._entry(reader, item)
                expected = self._preimage(before.get(item)); target = self._preimage(after.get(item))
                if current == target: continue
                if current != expected: raise ValueError("file changed during publication: " + item)
                raw = None
                if target is not None:
                    raw = self._git("cat-file", "blob", after[item]["blob"])
                    if len(raw) != target["size"] or sha256(raw).hexdigest() != target["sha256"]:
                        raise ValueError("checkpoint bytes failed integrity check")
                with reader._parent_directory(item, create_missing=target is not None) as (parent, leaf):
                    # File replacement is atomic; the whole set is deliberately
                    # not advertised as atomic. A crash leaves a recoverable intent.
                    if target is None:
                        os.unlink(leaf, dir_fd=parent)
                    else:
                        name = ".bw-publish-" + uuid.uuid4().hex
                        fd = os.open(name, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600, dir_fd=parent)
                        try:
                            with os.fdopen(fd, "wb") as stream:
                                stream.write(raw); stream.flush(); os.fchmod(stream.fileno(), target["mode"]); os.fsync(stream.fileno())
                            if self._entry(reader, item) != expected:
                                raise ValueError("file changed while preparing publication: " + item)
                            if expected is None:
                                # An intervening new file wins; never replace it.
                                os.link(name, leaf, src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)
                            else:
                                os.replace(name, leaf, src_dir_fd=parent, dst_dir_fd=parent)
                        finally:
                            try: os.unlink(name, dir_fd=parent)
                            except FileNotFoundError: pass
                    os.fsync(parent)
                if observer: observer("file_durable", item)
            record = dict(intent=intent, status="committed")
            _save(path, record)
            if observer: observer("receipt_durable", None)
            return record
