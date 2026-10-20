"""Explicit, rebuildable UTF-8 reference packs; no inference or authority grants.

A pack is derived knowledge, never a workflow ledger or a COW checkpoint.
Only the caller's selected Linux source tree is read. Each new admission checks
source content again. Existing admitted COW roots remain immutable.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import tempfile

VERSION = 1
_MAX_MANIFEST = 8 * 1024 * 1024
_MAX_PACK = 544 * 1024 * 1024
_MAX_DIRECTORIES = 20000
_MAX_DEPTH = 128
_SECTIONS = ("examples", "facts")
_WARNING = (
    "REFERENCE PACK: these are recorded examples and knowledge, not live observation.\n"
    "This pack does not grant tools, permissions, execution authority, or acceptance.\n"
    "Verify current facts with authorized tools before relying on them. Report stale\n"
    "facts and update their source records; do not silently rewrite old snapshots.\n"
)

class PackError(ValueError):
    """Invalid pack or source selection."""

class SourceError(PackError):
    """Unsafe, unreadable, invalid, or over-budget source."""

class SourceChangedError(SourceError):
    """The selected source changed during capture."""

class StalePackError(PackError):
    """The source no longer matches this immutable pack."""

@dataclass(frozen=True)
class Limits:
    max_files: int = 512
    max_file_bytes: int = 8 * 1024 * 1024
    max_total_bytes: int = 32 * 1024 * 1024

    def __post_init__(self):
        hard = {"max_files": 20000, "max_file_bytes": 128*1024*1024,
                "max_total_bytes": 512*1024*1024}
        for key, ceiling in hard.items():
            value = getattr(self, key)
            if type(value) is not int or not 0 < value <= ceiling:
                raise SourceError(f"{key} must be a positive integer <= {ceiling}")

def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

def _sha(data):
    return hashlib.sha256(data).hexdigest()

def _captured_at():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def _as_of(value):
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.utcoffset() is None:
            raise ValueError("timezone required")
        return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except (ValueError, AttributeError) as exc:
        raise SourceError("as_of requires an explicit ISO-8601 date/time with timezone") from exc

def _absolute(value):
    return Path(os.path.abspath(os.fspath(value)))

def _open_dir(path):
    """Anchor every path component with openat/O_NOFOLLOW, including ancestors."""
    path = _absolute(path)
    descriptor = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        for part in path.parts[1:]:
            newer = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                            dir_fd=descriptor)
            os.close(descriptor)
            descriptor = newer
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise

def _lstat(path):
    descriptor = _open_dir(path.parent)
    try:
        return os.stat(path.name, dir_fd=descriptor, follow_symlinks=False)
    finally:
        os.close(descriptor)

def _signature(value):
    return (value.st_dev, value.st_ino, value.st_mode, value.st_size,
            value.st_mtime_ns, value.st_ctime_ns)

def _read_source_file(path, limit):
    """Bounded, no-follow regular-file read; reject replacement/mutation."""
    descriptor = None
    parent = None
    try:
        parent = _open_dir(path.parent)
        before = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        if not stat.S_ISREG(before.st_mode):
            raise SourceError(f"not a regular file: {path}")
        if before.st_size > limit:
            raise SourceError(f"file exceeds byte limit: {path}")
        descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent)
        opened = os.fstat(descriptor)
        if _signature(before) != _signature(opened):
            raise SourceChangedError(f"source replaced before read: {path}")
        chunks = []
        size = 0
        while True:
            data = os.read(descriptor, min(1024*1024, limit + 1 - size))
            if not data:
                break
            chunks.append(data)
            size += len(data)
            if size > limit:
                raise SourceError(f"file exceeds byte limit: {path}")
        after = os.fstat(descriptor)
        named = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        if _signature(opened) != _signature(after) or _signature(after) != _signature(named):
            raise SourceChangedError(f"source changed during read: {path}")
        payload = b"".join(chunks)
        try:
            payload.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise SourceError(f"source is not strict UTF-8: {path}") from exc
        return payload
    except PackError:
        raise
    except OSError as exc:
        raise SourceError(f"cannot read safe regular file {path}: {exc.strerror}") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if parent is not None:
            os.close(parent)

def _selection(section, value):
    if not isinstance(value, str) or not value or "\\" in value:
        raise SourceError("selections must be nonempty relative POSIX paths")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        raise SourceError(f"selection is outside approved root: {value}")
    return {"section": section, "path": str(path)}

def _inventory(root, selections, limits):
    records = {}
    directories = {}
    total_bytes = 0
    def visit(path, section):
        nonlocal total_bytes
        try:
            found = _lstat(path)
            relative = path.relative_to(root).as_posix()
            if len(path.relative_to(root).parts) > _MAX_DEPTH:
                raise SourceError("source tree exceeds maximum depth")
            if stat.S_ISLNK(found.st_mode):
                raise SourceError(f"symlink is forbidden: {path}")
            if stat.S_ISDIR(found.st_mode):
                descriptor = _open_dir(path)
                try:
                    directories[str(path)] = _signature(os.fstat(descriptor))
                    if len(directories) > _MAX_DIRECTORIES:
                        raise SourceError("source tree exceeds maximum directory count")
                    with os.scandir(descriptor) as iterator:
                        names = sorted(entry.name for entry in iterator)
                    for name in names:
                        visit(path / name, section)
                    if directories[str(path)] != _signature(os.fstat(descriptor)):
                        raise SourceChangedError(f"directory changed during scan: {path}")
                finally:
                    os.close(descriptor)
                return
            if not stat.S_ISREG(found.st_mode):
                raise SourceError(f"not a regular text file/directory: {path}")
            if relative in records and records[relative]["section"] != section:
                raise SourceError(f"same source selected for both sections: {relative}")
            if relative not in records:
                total_bytes += found.st_size
            records[relative] = {"section": section, "path": relative, "signature": _signature(found)}
            if len(records) > limits.max_files:
                raise SourceError("selected files exceed max_files")
            if found.st_size > limits.max_file_bytes:
                raise SourceError(f"file exceeds byte limit: {path}")
            if total_bytes > limits.max_total_bytes:
                raise SourceError("selected sources exceed total byte limit")
        except PackError:
            raise
        except OSError as exc:
            raise SourceError(f"unsafe/unreadable source {path}: {exc.strerror}") from exc
    descriptor = None
    try:
        descriptor = _open_dir(root)
    except OSError as exc:
        raise SourceError(f"approved root must be a real directory without symlinks: {root}") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
    for selection in selections:
        visit(root / selection["path"], selection["section"])
    return records, directories

def _capture(root, selections, limits):
    first, dirs = _inventory(root, selections, limits)
    files = []
    payloads = {}
    for relative, record in sorted(first.items(), key=lambda pair: (_SECTIONS.index(pair[1]["section"]), pair[0])):
        path = root / relative
        try:
            current_signature = _signature(_lstat(path))
        except OSError as exc:
            raise SourceChangedError(f"source disappeared before capture: {path}") from exc
        if current_signature != record["signature"]:
            raise SourceChangedError(f"source changed before capture: {path}")
        data = _read_source_file(path, limits.max_file_bytes)
        if len(data) != record["signature"][3]:
            raise SourceChangedError(f"source size changed: {path}")
        files.append({"section": record["section"], "path": relative,
                      "bytes": len(data), "sha256": _sha(data)})
        payloads[relative] = data.decode("utf-8")
    second, second_dirs = _inventory(root, selections, limits)
    if first != second or dirs != second_dirs:
        raise SourceChangedError("selected source tree changed during capture")
    return files, payloads

def _render(files, payloads, as_of):
    parts = [_WARNING, f"Recorded facts as of: {as_of}\n"]
    for section, title in (("examples", "WORKED EXAMPLES"), ("facts", "RECORDED ENVIRONMENT FACTS")):
        parts.append(f"\n=== {title} ===\n")
        chosen = [file for file in files if file["section"] == section]
        if not chosen:
            parts.append("(No selected files in this section.)\n")
        for file in chosen:
            header = json.dumps({"source": file["path"], "utf8_bytes": file["bytes"],
                                 "sha256": file["sha256"]}, ensure_ascii=False, sort_keys=True)
            parts.append(f"\n--- BEGIN SOURCE {header} ---\n")
            parts.append(payloads[file["path"]])
            parts.append("\n--- END SOURCE ---\n")
    return "".join(parts)

def _write_durable(path, payload):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    path.chmod(0o400)

def _fsync_dir(path):
    descriptor = _open_dir(path)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)

def _receipt(manifest, pack_dir, status):
    identity = manifest["identity"]
    return {"status": status, "pack_id": manifest["pack_id"], "pack_path": str(pack_dir),
            "captured_at": manifest["captured_at"], "as_of": identity["as_of"],
            "source_files": len(identity["files"]),
            "source_bytes": sum(file["bytes"] for file in identity["files"]),
            "prefix_bytes": identity["prefix_bytes"], "limits": identity["limits"]}

def build_pack(*, root, examples=(), facts=(), output, as_of, limits=None):
    """Capture explicit sources and publish a content-addressed immutable pack."""
    if os.name != "posix" or not hasattr(os, "O_NOFOLLOW"):
        raise SourceError("safe source traversal is currently qualified on POSIX only")
    limits = limits or Limits()
    if isinstance(examples, (str, bytes)) or isinstance(facts, (str, bytes)):
        raise SourceError("examples and facts must be explicit path sequences")
    root, output = _absolute(root), _absolute(output)
    if output == root or root in output.parents:
        raise SourceError("pack output must be outside the selected source root")
    selections = [_selection(section, value) for section, values in
                  (("examples", examples), ("facts", facts)) for value in values]
    selections = sorted({(item["section"], item["path"]) for item in selections},
                        key=lambda item: (_SECTIONS.index(item[0]), item[1]))
    selections = [{"section": section, "path": path} for section, path in selections]
    if not selections:
        raise SourceError("explicitly select at least one source")
    if len(selections) > limits.max_files:
        raise SourceError("too many explicit source selections")
    as_of = _as_of(as_of)
    files, payloads = _capture(root, selections, limits)
    if not files:
        raise SourceError("no selected text files")
    prefix = _render(files, payloads, as_of).encode("utf-8")
    identity = {"version": VERSION, "root": str(root), "selections": selections,
                "as_of": as_of, "files": files, "prefix_bytes": len(prefix),
                "prefix_sha256": _sha(prefix), "limits": asdict(limits)}
    pack_id = _sha(_json(identity))
    manifest = {"pack_id": pack_id, "captured_at": _captured_at(), "identity": identity}
    # Fail rather than following a symlink in an existing output ancestor.
    ancestor = output
    while not ancestor.exists():
        ancestor = ancestor.parent
    try:
        descriptor = _open_dir(ancestor)
        os.close(descriptor)
        output.mkdir(mode=0o700, parents=True, exist_ok=True)
        descriptor = _open_dir(output)
        os.close(descriptor)
    except OSError as exc:
        raise SourceError(f"unsafe/unwritable pack output: {output}: {exc.strerror}") from exc
    destination = output / pack_id
    if destination.exists():
        previous, _ = _read_pack(destination)
        if previous["identity"] != identity:
            raise PackError("existing identity collision")
        return _receipt(previous, destination, "reused")
    staging = Path(tempfile.mkdtemp(prefix=".building-", dir=output))
    try:
        encoded = _json(manifest) + b"\n"
        _write_durable(staging/"manifest.json", encoded)
        _write_durable(staging/"prefix.txt", prefix)
        _write_durable(staging/"manifest.sha256", (_sha(encoded)+"\n").encode("ascii"))
        _fsync_dir(staging)
        try:
            staging.rename(destination)
        except OSError:
            if not destination.exists():
                raise
            previous, _ = _read_pack(destination)
            if previous["identity"] != identity:
                raise PackError("concurrent pack publication conflict")
            return _receipt(previous, destination, "reused")
        _fsync_dir(output)
    except OSError as exc:
        raise PackError(f"pack publication failed: {exc.strerror}") from exc
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return _receipt(manifest, destination, "built")

def _validate_identity(identity):
    required = {"version", "root", "selections", "as_of", "files",
                "prefix_bytes", "prefix_sha256", "limits"}
    if set(identity) != required or identity["version"] != VERSION:
        raise PackError("unsupported or incomplete reference-pack identity")
    if not isinstance(identity["root"], str) or str(_absolute(identity["root"])) != identity["root"]:
        raise PackError("approved root must be an absolute canonical path")
    limits = Limits(**identity["limits"])
    selections = identity["selections"]
    if not isinstance(selections, list) or not 0 < len(selections) <= limits.max_files:
        raise PackError("invalid source selections")
    normalized = []
    for item in selections:
        if set(item) != {"section", "path"} or item["section"] not in _SECTIONS:
            raise PackError("invalid source section")
        clean = _selection(item["section"], item["path"])
        if clean != item:
            raise PackError("noncanonical source selection")
        normalized.append(clean)
    ordered = sorted(normalized, key=lambda item: (_SECTIONS.index(item["section"]), item["path"]))
    if ordered != normalized or len({(x["section"], x["path"]) for x in normalized}) != len(normalized):
        raise PackError("source selections must be unique and ordered")
    files = identity["files"]
    if not isinstance(files, list) or not 0 < len(files) <= limits.max_files:
        raise PackError("invalid source file count")
    seen = set()
    for file in files:
        if set(file) != {"section", "path", "bytes", "sha256"} or file["section"] not in _SECTIONS:
            raise PackError("invalid source file record")
        if _selection(file["section"], file["path"])["path"] != file["path"] or file["path"] in seen:
            raise PackError("invalid or duplicate source file path")
        seen.add(file["path"])
        if type(file["bytes"]) is not int or not 0 <= file["bytes"] <= limits.max_file_bytes:
            raise PackError("invalid source byte count")
        if not isinstance(file["sha256"], str) or len(file["sha256"]) != 64 or any(c not in "0123456789abcdef" for c in file["sha256"]):
            raise PackError("invalid source digest")
    if sum(file["bytes"] for file in files) > limits.max_total_bytes:
        raise PackError("invalid total source byte count")
    if _as_of(identity["as_of"]) != identity["as_of"]:
        raise PackError("noncanonical as-of timestamp")

def _read_pack(pack_path):
    path = _absolute(pack_path)
    try:
        descriptor = _open_dir(path)
        try:
            with os.scandir(descriptor) as iterator:
                names = {entry.name for entry in iterator}
        finally:
            os.close(descriptor)
        if names != {"manifest.json", "manifest.sha256", "prefix.txt"}:
            raise PackError("pack has missing or unexpected files")
        encoded = _read_source_file(path/"manifest.json", _MAX_MANIFEST)
        expected = _read_source_file(path/"manifest.sha256", 128).decode("ascii").strip()
        if expected != _sha(encoded):
            raise PackError("manifest checksum mismatch")
        manifest = json.loads(encoded)
        identity = manifest["identity"]
        _validate_identity(identity)
        if manifest["pack_id"] != _sha(_json(identity)) or path.name != manifest["pack_id"]:
            raise PackError("manifest identity/path mismatch")
        Limits(**identity["limits"])
        if type(identity["prefix_bytes"]) is not int or not 0 < identity["prefix_bytes"] <= _MAX_PACK:
            raise PackError("invalid prefix byte count")
        if not isinstance(manifest["captured_at"], str):
            raise PackError("missing capture provenance")
        _as_of(manifest["captured_at"])
        _as_of(identity["as_of"])
        prefix = _read_source_file(path/"prefix.txt", identity["prefix_bytes"])
        if len(prefix) != identity["prefix_bytes"] or _sha(prefix) != identity["prefix_sha256"]:
            raise PackError("prefix payload checksum/size mismatch")
        return manifest, prefix.decode("utf-8")
    except PackError:
        raise
    except (OSError, KeyError, TypeError, ValueError, UnicodeError) as exc:
        raise PackError(f"invalid reference pack: {exc}") from exc

def _source_changes(before_files, after_files):
    before = {(x["section"], x["path"]): x for x in before_files}
    after = {(x["section"], x["path"]): x for x in after_files}
    return [
        {"section": key[0], "path": key[1],
         "kind": "added" if key not in before else "deleted" if key not in after else "modified"}
        for key in sorted(before.keys() | after.keys())
        if before.get(key) != after.get(key)
    ]

def _verify_sources(manifest, pack_path):
    identity = manifest["identity"]
    try:
        current, _ = _capture(Path(identity["root"]), identity["selections"], Limits(**identity["limits"]))
    except (SourceError, OSError) as exc:
        return {**_receipt(manifest, _absolute(pack_path), "stale"), "changes": [], "reason": str(exc)}
    changes = _source_changes(identity["files"], current)
    return {**_receipt(manifest, _absolute(pack_path), "stale" if changes else "fresh"), "changes": changes}

def verify_pack(pack_path):
    """Return fresh/stale; integrity failures raise instead of looking stale."""
    manifest, _ = _read_pack(pack_path)
    return _verify_sources(manifest, pack_path)

def refresh_pack(pack_path, *, output, as_of, expected_id=None):
    """Rebuild changed sources using the old pack's explicit scope and limits.

    Returns a new derived pack, never a changed old prefix or moved COW branch.
    Unchanged sources retain their original as-of time. This is a point-in-time
    byte capture, not proof that statements are true or a lock on future edits.
    Unsafe/missing selections fail rather than silently reducing the scope.
    Callers must explicitly admit the returned pack into a new COW root and
    retain its reference in their existing workflow ledger.
    """
    manifest, _ = _read_pack(pack_path)
    if expected_id is not None and expected_id != manifest["pack_id"]:
        raise PackError("pinned reference-pack identity mismatch")
    as_of = _as_of(as_of)
    identity = manifest["identity"]
    limits = Limits(**identity["limits"])
    current, _ = _capture(Path(identity["root"]), identity["selections"], limits)
    if not _source_changes(identity["files"], current):
        return {**_receipt(manifest, _absolute(pack_path), "fresh"),
                "action": "unchanged", "previous_pack_id": manifest["pack_id"],
                "changes": []}
    result = build_pack(
        root=identity["root"],
        examples=[x["path"] for x in identity["selections"] if x["section"] == "examples"],
        facts=[x["path"] for x in identity["selections"] if x["section"] == "facts"],
        output=output, as_of=as_of, limits=limits)
    # Report the actually published capture, not the earlier change probe.
    published, _ = _read_pack(result["pack_path"])
    return {**result, "action": "rebuilt", "previous_pack_id": manifest["pack_id"],
            "changes": _source_changes(identity["files"], published["identity"]["files"])}

def load_verified_prefix(pack_path, *, expected_id=None):
    """Return the exact validated prefix bytes, after a source freshness check.

    expected_id optionally binds admission to a caller-pinned content identity.
    The payload is read and validated once; later file replacement cannot alter
    the returned in-memory text. Existing COW roots are never rewritten.
    This is recorded knowledge, not a lock on a changing external environment.
    """
    manifest, prefix = _read_pack(pack_path)
    if expected_id is not None and expected_id != manifest["pack_id"]:
        raise PackError("pinned reference-pack identity mismatch")
    result = _verify_sources(manifest, pack_path)
    if result["status"] != "fresh":
        raise StalePackError(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return prefix

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build", help="capture explicitly approved UTF-8 sources")
    build.add_argument("--root", required=True)
    build.add_argument("--examples", action="append", default=[])
    build.add_argument("--facts", action="append", default=[])
    build.add_argument("--output", required=True)
    build.add_argument("--as-of", required=True)
    for field, value in asdict(Limits()).items():
        build.add_argument("--"+field.replace("_", "-"), type=int, default=value)
    verify = commands.add_parser("verify", help="validate pack integrity and current selected sources")
    verify.add_argument("pack_path")
    refresh = commands.add_parser("refresh", help="rebuild changed sources under a new immutable pack identity")
    refresh.add_argument("pack_path")
    refresh.add_argument("--output", required=True)
    refresh.add_argument("--as-of", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            result = build_pack(root=args.root, examples=args.examples, facts=args.facts,
                output=args.output, as_of=args.as_of, limits=Limits(
                    args.max_files, args.max_file_bytes, args.max_total_bytes))
        elif args.command == "refresh":
            result = refresh_pack(args.pack_path, output=args.output, as_of=args.as_of)
        else:
            result = verify_pack(args.pack_path)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 2 if result["status"] == "stale" else 0
    except PackError as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False, sort_keys=True))
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
