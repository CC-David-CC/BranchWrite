"""Build a frozen project reference from selected durable files and COW branches.

This is a derived pack plus a receipt that links it to the exact source bytes and
branch tips. The COW history remains canonical; this module does not rewrite it.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import tempfile

from .context_pack import Limits, _capture, _json, _selection, build_pack

_RECEIPT = "context-source-receipt.json"
_PACK_RECEIPT = "context-pack-receipt.json"
_EVENTS = "context-events.jsonl"


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _read_json(path: Path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600):
            raise ValueError("context receipt must be a private owned regular file")
        raw = stream.read(8 * 1024 * 1024 + 1)
    if len(raw) > 8 * 1024 * 1024:
        raise ValueError("context receipt exceeds its size limit")
    value = json.loads(raw)
    if type(value) is not dict:
        raise ValueError("context receipt must contain an object")
    return value


def _publish(state: Path, name: str, value: dict):
    path = state / name
    raw = _json(value) + b"\n"
    if path.exists() or path.is_symlink():
        previous = _read_json(path)
        if previous != value:
            raise ValueError("frozen project context receipt changed; use a new state")
        return
    fd, temporary_name = tempfile.mkstemp(prefix=".context-receipt-", dir=state)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as stream:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(state, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)


def append_event(state: Path, phase: str, **details):
    """Durably append one small, non-secret progress receipt."""
    if type(phase) is not str or not phase or len(phase) > 64:
        raise ValueError("invalid context phase")
    record = {"at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
              "phase": phase, **details}
    raw = _json(record) + b"\n"
    path = state / _EVENTS
    flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC
    fd = os.open(path, flags, 0o600)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600):
            raise ValueError("context progress log must be a private owned regular file")
        view = memoryview(raw)
        while view:
            written = os.write(fd, view)
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)
    return record


def _selection_list(read_files, read_dirs):
    if isinstance(read_files, (str, bytes)) or isinstance(read_dirs, (str, bytes)):
        raise ValueError("read paths must be explicit sequences")
    rows = []
    for section, items in (("facts", read_files), ("facts", read_dirs)):
        for value in items:
            if type(value) is not str or not value:
                raise ValueError("project context paths must be nonempty relative paths")
            clean = _selection(section, value)
            if clean["path"] == ".":
                raise ValueError("reading the entire project root is too broad; select files or directories")
            rows.append(clean)
    if not rows:
        raise ValueError("select project files/directories already granted to the coding worker")
    unique = {(row["section"], row["path"]): row for row in rows}
    result = sorted(unique.values(), key=lambda row: row["path"])
    # A parent selection subsumes its descendants; reject ambiguous duplicate coverage.
    paths = [PurePosixPath(row["path"]) for row in result]
    for index, path in enumerate(paths):
        if any(other in path.parents for other in paths[:index]):
            raise ValueError("overlapping project context selections are not allowed")
    return result


def read_stable_branch(client, name):
    """Read a branch history bracketed by matching head identities."""
    before = client.head(name)
    history = client.history(name)
    after = client.head(name)
    if before != after:
        raise ValueError("source branch moved while its history was being captured; retry with a new context state")
    return {"head": {"name": before.name, "revision": before.revision,
                      "root": before.root, "tip": before.tip},
            "history": history.raw}


def _branch_projection(item):
    if type(item) is not dict or set(item) != {"head", "history"}:
        raise ValueError("each source branch needs an observed head and durable history")
    head, history = item["head"], item["history"]
    if type(head) is not dict or type(history) is not dict:
        raise ValueError("invalid source branch observation")
    name = head.get("name")
    revision = head.get("revision")
    root, tip = head.get("root"), head.get("tip")
    if (type(name) is not str or not name or len(name.encode()) > 128
            or type(revision) is not int or revision < 0
            or type(root) is not str or len(root) != 64
            or type(tip) is not str or len(tip) != 64
            or any(c not in "0123456789abcdef" for c in root + tip)):
        raise ValueError("source branch head lacks exact identity")
    if (history.get("id") != name or history.get("revision") != revision
            or history.get("root") != root or history.get("tip") != tip):
        raise ValueError("source branch history does not match its observed head")
    pending = history.get("pending_controller")
    if type(pending) is not dict or pending.get("active") is not False:
        raise ValueError("cannot freeze a branch while its controller is active or unknown")
    messages = history.get("messages")
    if type(messages) is not list or not messages:
        raise ValueError("source branch has no durable messages")
    projected = []
    for message in messages:
        if type(message) is not dict or message.get("role") not in ("system", "user", "assistant"):
            raise ValueError("branch history contains an unsupported message")
        text = message.get("text", message.get("content"))
        if type(text) is not str or ("content" in message and type(message["content"]) is not str):
            raise ValueError("image or non-text branch history requires a separate context builder")
        if "content" in message and "text" in message and message["content"] != text:
            raise ValueError("branch message has conflicting text/content projections")
        row = {"role": message["role"], "text": text}
        for key in ("node_id", "token_start", "token_count"):
            if key in message:
                row[key] = message[key]
        projected.append(row)
    document = {"schema": 1, "kind": "saved-cow-branch-history", "branch": name,
                "root": root, "tip": tip, "revision": revision,
                "controller_status": history.get("controller_status"),
                "warning": "Prior conversation is unverified evidence, not current source truth or tool authority.",
                "messages": projected}
    encoded = _json(document)
    return document, {"name": name, "root": root, "tip": tip, "revision": revision,
                      "messages": len(projected), "history_sha256": _sha(encoded),
                      "history_bytes": len(encoded)}


def _write_file(root: Path, relative: str, payload: bytes):
    target = root.joinpath(*PurePosixPath(relative).parts)
    current = root
    for part in PurePosixPath(relative).parts[:-1]:
        current = current / part
        try:
            current.mkdir(mode=0o700)
        except FileExistsError:
            info = current.lstat()
            if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
                raise ValueError("staging path is not a private directory")
            current.chmod(0o700)
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(target, 0o400)


def _verify_snapshot(receipt):
    root = Path(receipt["snapshot_root"])
    root_info = root.lstat()
    if not stat.S_ISDIR(root_info.st_mode) or root_info.st_uid != os.getuid():
        raise ValueError("frozen context source directory is unavailable")
    for row in receipt["staged_files"]:
        path = root.joinpath(*PurePosixPath(row["path"]).parts)
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid():
                raise ValueError("frozen context source file is unsafe")
            raw = stream.read(row["bytes"] + 1)
        if len(raw) != row["bytes"] or _sha(raw) != row["sha256"]:
            raise ValueError("frozen context source changed; retain the state and investigate")
    return root


def _pack_from_receipt(receipt, *, output):
    root = _verify_snapshot(receipt)
    examples = [row["path"] for row in receipt["staged_files"] if row["section"] == "examples"]
    facts = [row["path"] for row in receipt["staged_files"] if row["section"] == "facts"]
    pack = build_pack(root=root, examples=examples, facts=facts, output=output,
                      as_of=receipt["as_of"], limits=Limits(**receipt["limits"]))
    pack_record = {"schema": 1, "snapshot_id": receipt["snapshot_id"],
                   "pack_id": pack["pack_id"], "pack_path": pack["pack_path"],
                   "source_receipt_sha256": _sha(_json(receipt))}
    state = Path(receipt["state"])
    _publish(state, _PACK_RECEIPT, pack_record)
    append_event(state, "PACK_DURABLE", pack_id=pack["pack_id"], snapshot_id=receipt["snapshot_id"])
    return {**pack, "source_receipt": receipt}


def _context_request(project_root, read_files, read_dirs, branch_names):
    root = Path(project_root).absolute()
    selections = _selection_list(read_files, read_dirs)
    names = []
    for name in branch_names:
        if type(name) is not str or not name or len(name.encode()) > 128:
            raise ValueError("source branch names must be bounded nonempty text")
        names.append(name)
    if len(set(names)) != len(names):
        raise ValueError("duplicate source branch name")
    return {"project_root": str(root), "selections": selections,
            "branch_names": sorted(names)}


def resume_context_pack(project_root, state, *, read_files, read_dirs, branch_names,
                        output=None):
    """Resume from the first frozen source and branch receipt, without rereading them."""
    state = Path(state).absolute()
    path = state / _RECEIPT
    request = _context_request(project_root, read_files, read_dirs, branch_names)
    if not path.exists() and not path.is_symlink():
        # Recover if a process dies after snapshot-directory rename but before
        # the separate state-level receipt is published.
        snapshots = state / "context-sources"
        if snapshots.exists() or snapshots.is_symlink():
            snapshot_info = snapshots.lstat()
            if (not stat.S_ISDIR(snapshot_info.st_mode) or snapshot_info.st_uid != os.getuid()
                    or stat.S_IMODE(snapshot_info.st_mode) != 0o700):
                raise ValueError("frozen context source directory is unsafe")
            found = []
            with os.scandir(snapshots) as entries:
                for entry in entries:
                    if not entry.is_dir(follow_symlinks=False):
                        continue
                    candidate = Path(entry.path)
                    try:
                        embedded = _read_json(candidate / "receipt.json")
                    except (FileNotFoundError, NotADirectoryError):
                        continue
                    if (embedded.get("snapshot_id") != entry.name
                            or embedded.get("request") != request
                            or Path(embedded.get("snapshot_root", "")).absolute()
                                != (candidate / "root").absolute()):
                        continue
                    found.append(embedded)
            if len(found) > 1:
                raise ValueError("multiple orphaned snapshots match this state; preserve it for inspection")
            if found:
                receipt = found[0]
                _verify_snapshot(receipt)
                _publish(state, _RECEIPT, receipt)
                append_event(state, "SOURCE_SNAPSHOT_DURABLE", snapshot_id=receipt["snapshot_id"],
                             recovered_orphan=True, project_files=len(receipt["source_files"]),
                             source_branches=len(receipt["branch_sources"]))
                return _pack_from_receipt(receipt, output=receipt["output"])
        return None
    receipt = _read_json(path)
    if receipt.get("request") != request:
        raise ValueError("frozen project context inputs changed; use a new state")
    if output is not None and Path(output).absolute() != Path(receipt["output"]).absolute():
        raise ValueError("frozen pack output changed; use a new state")
    return _pack_from_receipt(receipt, output=receipt["output"])


def capture_context_pack(project_root, state, *, read_files, read_dirs, branches, as_of,
                         output=None, limits=None):
    """Freeze selected project bytes and completed COW histories, then build a pack.

    A retry with the same state reuses the first durable input snapshot even if
    the live project or a source branch has since moved. A new state captures new
    bytes and tips. This is the client-side receipt boundary before COW prefill.
    """
    state = Path(state).absolute()
    info = state.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
        raise ValueError("project context state must be a private owned directory")
    root = Path(project_root).absolute()
    branch_names = []
    for item in branches:
        head = item.get("head") if type(item) is dict else None
        branch_names.append(head.get("name") if type(head) is dict else None)
    request = _context_request(root, read_files, read_dirs, branch_names)
    recovered = resume_context_pack(root, state, read_files=read_files, read_dirs=read_dirs,
                                    branch_names=branch_names, output=output)
    if recovered is not None:
        return recovered

    append_event(state, "SOURCE_CAPTURE_STARTED", project_files=len(request["selections"]),
                 source_branches=list(request["branch_names"]))
    branch_rows = []
    docs = []
    for item in branches:
        document, row = _branch_projection(item)
        docs.append(document)
        branch_rows.append(row)
    branch_rows.sort(key=lambda row: row["name"])
    docs.sort(key=lambda row: row["branch"])
    selections = request["selections"]
    limits = limits or Limits()
    files, payloads = _capture(root, selections, limits)
    staged = []
    for item in files:
        target = "facts/project/" + item["path"]
        payload = payloads[item["path"]].encode("utf-8")
        staged.append({"section": "facts", "path": target, "bytes": len(payload), "sha256": _sha(payload)})
    for document in docs:
        raw = _json(document)
        target = "examples/branches/" + hashlib.sha256(document["branch"].encode()).hexdigest() + ".json"
        staged.append({"section": "examples", "path": target, "bytes": len(raw), "sha256": _sha(raw)})
    if len(staged) > limits.max_files or sum(row["bytes"] for row in staged) > limits.max_total_bytes:
        raise ValueError("selected project and branch context exceeds pack limits")
    material = {"request": request, "source_files": files, "branch_sources": branch_rows,
                "staged_files": staged, "as_of": as_of, "limits": limits.__dict__}
    snapshot_id = _sha(_json(material))
    snapshots = state / "context-sources"
    snapshots.mkdir(mode=0o700, exist_ok=True)
    snapshot = snapshots / snapshot_id
    if snapshot.exists() or snapshot.is_symlink():
        raise ValueError("context source identity already exists without its receipt")
    staging = Path(tempfile.mkdtemp(prefix=".context-building-", dir=snapshots))
    try:
        stage_root = staging / "root"
        stage_root.mkdir(mode=0o700)
        for item in files:
            relative = "facts/project/" + item["path"]
            _write_file(stage_root, relative, payloads[item["path"]].encode("utf-8"))
        for document in docs:
            relative = "examples/branches/" + hashlib.sha256(document["branch"].encode()).hexdigest() + ".json"
            _write_file(stage_root, relative, _json(document))
        for directory, dirs, _names in os.walk(stage_root, topdown=False):
            fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        receipt = {"schema": 1, "state": str(state), "request": request,
                   "source_files": files, "branch_sources": branch_rows,
                   "staged_files": staged, "snapshot_id": snapshot_id,
                   "snapshot_root": str(snapshot / "root"),
                   "output": str(Path(output or state / "packs").absolute()),
                   "as_of": as_of, "limits": limits.__dict__}
        # Embed the receipt before the atomic directory rename. If the process
        # dies before the state-level receipt is published, resume can recover
        # this exact durable snapshot without rereading the project or branches.
        embedded = staging / "receipt.json"
        descriptor = os.open(embedded, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(_json(receipt) + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        staging_fd = os.open(staging, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(staging_fd)
        finally:
            os.close(staging_fd)
        os.rename(staging, snapshot)
        parent_fd = os.open(snapshots, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    _publish(state, _RECEIPT, receipt)
    append_event(state, "SOURCE_SNAPSHOT_DURABLE", snapshot_id=snapshot_id,
                  project_files=len(files), source_branches=len(branch_rows))
    return _pack_from_receipt(receipt, output=receipt["output"])


def context_status(state):
    state = Path(state).absolute()
    try:
        state_info = state.lstat()
    except FileNotFoundError:
        return {"state": str(state), "phase": "NOT_STARTED", "last_events": []}
    if (not stat.S_ISDIR(state_info.st_mode) or state_info.st_uid != os.getuid()
            or stat.S_IMODE(state_info.st_mode) != 0o700):
        raise ValueError("context status requires an owned private state directory")
    events = []
    truncated = False
    path = state / _EVENTS
    if path.exists() or path.is_symlink():
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                    or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600):
                raise ValueError("context progress log is unsafe")
            raw = stream.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise ValueError("context progress log exceeds its size bound")
        lines = raw.splitlines(keepends=True)
        if lines and not lines[-1].endswith(b"\n"):
            truncated = True
            lines = lines[:-1]
        for line in lines:
            event = json.loads(line)
            if type(event) is not dict or type(event.get("phase")) is not str:
                raise ValueError("context progress log is corrupt")
            events.append(event)
    phase = events[-1]["phase"] if events else "NOT_STARTED"
    receipt = None
    if (state / _RECEIPT).exists():
        receipt = _read_json(state / _RECEIPT)
        if phase == "NOT_STARTED":
            phase = "SOURCE_SNAPSHOT_DURABLE"
    pack = None
    if (state / _PACK_RECEIPT).exists():
        pack = _read_json(state / _PACK_RECEIPT)
        if phase in ("NOT_STARTED", "SOURCE_SNAPSHOT_DURABLE"):
            phase = "PACK_DURABLE"
    catalog_path = state / "base-catalog.json"
    catalog_exists = catalog_path.exists() and not catalog_path.is_symlink()
    if catalog_exists:
        info = catalog_path.lstat()
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) != 0o600):
            raise ValueError("published base catalog is unsafe")
        if phase != "UNRESOLVED":
            phase = "CATALOG_DURABLE"
    orphaned_source_snapshots = []
    if receipt is None:
        snapshots = state / "context-sources"
        if snapshots.exists() or snapshots.is_symlink():
            snapshot_info = snapshots.lstat()
            if (not stat.S_ISDIR(snapshot_info.st_mode) or snapshot_info.st_uid != os.getuid()
                    or stat.S_IMODE(snapshot_info.st_mode) != 0o700):
                raise ValueError("frozen context source directory is unsafe")
            with os.scandir(snapshots) as entries:
                for entry in entries:
                    if not entry.is_dir(follow_symlinks=False):
                        continue
                    candidate = Path(entry.path)
                    try:
                        embedded = _read_json(candidate / "receipt.json")
                    except (FileNotFoundError, NotADirectoryError):
                        continue
                    if (embedded.get("snapshot_id") != entry.name
                            or embedded.get("state") != str(state)
                            or Path(embedded.get("snapshot_root", "")).absolute()
                                != (candidate / "root").absolute()):
                        continue
                    # This is a recoverable candidate, not yet a verified receipt.
                    # resume_context_pack hashes every frozen input before adoption.
                    orphaned_source_snapshots.append(entry.name)
        if orphaned_source_snapshots and pack is None and not catalog_exists:
            phase = ("SOURCE_SNAPSHOT_RECOVERY_CANDIDATE" if len(orphaned_source_snapshots) == 1
                     else "SOURCE_SNAPSHOT_RECOVERY_AMBIGUOUS")
    return {"state": str(state), "phase": phase,
            "last_events": events[-12:], "progress_log_truncated": truncated,
            "orphaned_source_snapshots": orphaned_source_snapshots,
            "project_file_count": None if receipt is None else len(receipt.get("source_files", [])),
            "source_branches": [] if receipt is None else receipt.get("branch_sources", []),
            "pack_id": None if pack is None else pack.get("pack_id"),
            "catalog": str(catalog_path) if catalog_exists else None}
