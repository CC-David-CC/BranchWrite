"""Typed, standard-library client for an already-running Context COW service.

This module owns request/return transport and a client intent journal. It does
not import COW implementation modules or own a model transcript, sampler, or KV
state. Network/CLI results stay provisional until a branch-bound receipt passes
validation.
"""
from __future__ import annotations

import base64
import hashlib
import http.client
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import Request
from .http_request import open_without_redirect as urlopen


_OP_ID = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,127}\Z")
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_JOURNAL_SCHEMA = 1
_MAX_IMAGE_BYTES = 16 * 1024 * 1024


class CowClientError(RuntimeError):
    """Base class for COW client failures."""


class RequestRejected(CowClientError):
    """The service explicitly rejected a request; no success is inferred."""

    def __init__(self, message, *, status_code=None):
        super().__init__(message)
        self.status_code = status_code


class OperationIndeterminate(CowClientError):
    """The request may have reached COW, but a durable result is unavailable."""


class GenerationIndeterminate(OperationIndeterminate):
    """A generation has no completion proof; retain its exact operation ID.

    A stream error is not proof that no consumed state was published. This
    exception never authorizes resending or clearing the pending journal.
    """

    def __init__(self, operation_id: str, message: str):
        super().__init__(message)
        self.operation_id = operation_id


class OperationReuseError(CowClientError):
    """An operation ID is already bound to different request bytes."""


class ReceiptError(CowClientError):
    """A response does not prove the requested durable state transition."""


class ClientLimitError(CowClientError):
    """A server response exceeded the configured resource bound."""


@dataclass(frozen=True)
class ImageUploadReceipt:
    namespace_id: str
    image_id: str
    size_bytes: int
    expires_ns: int
    endpoint_url: str
    endpoint_pin: str | None
    raw: Mapping[str, Any]


def _image_metadata(original: bytes) -> tuple[int, int, str]:
    """Optional client image boundary; no image library on text-only calls."""
    if type(original) is not bytes or not 0 < len(original) <= _MAX_IMAGE_BYTES:
        raise ValueError("image must contain 1 byte to 16 MiB of actual bytes")
    import io
    from PIL import Image
    try:
        with Image.open(io.BytesIO(original)) as image:
            width, height = image.size
            kind = image.format
            if kind not in ("PNG", "JPEG") or width <= 0 or height <= 0 or width * height > 16_000_000:
                raise ValueError("unsupported image format or dimensions")
            if getattr(image, "is_animated", False):
                raise ValueError("animated images are not supported")
            image.verify()
        with Image.open(io.BytesIO(original)) as image:
            image.load()
            orientation = image.getexif().get(274, 1)
            if orientation not in (None, 0, 1, 2, 3, 4, 5, 6, 7, 8):
                raise ValueError("invalid EXIF orientation")
            if orientation in (5, 6, 7, 8):
                width, height = height, width
    except Exception as error:
        raise ValueError("image is invalid or incomplete") from error
    return width, height, "image/png" if kind == "PNG" else "image/jpeg"


@dataclass(frozen=True)
class FrameKey:
    run_id: str
    invocation_id: str
    parent_id: str
    attempt_id: str
    child_id: str
    result_slot_id: str
    epoch: int
    operation_id: str
    branch: str

    def __post_init__(self) -> None:
        for field in ("run_id", "invocation_id", "parent_id", "attempt_id",
                      "child_id", "result_slot_id"):
            value = getattr(self, field)
            if not isinstance(value, str) or not value or len(value) > 256:
                raise ValueError(f"{field} must be a nonempty string of at most 256 characters")
        if type(self.epoch) is not int or self.epoch < 0:
            raise ValueError("epoch must be a nonnegative integer")
        if not _OP_ID.fullmatch(self.operation_id):
            raise ValueError("frame operation_id is invalid")
        if not isinstance(self.branch, str) or not self.branch:
            raise ValueError("frame branch must be nonempty")

    def to_json(self) -> dict[str, Any]:
        return {"run_id": self.run_id, "invocation_id": self.invocation_id,
                "parent_id": self.parent_id, "attempt_id": self.attempt_id,
                "child_id": self.child_id, "result_slot_id": self.result_slot_id,
                "epoch": self.epoch, "operation_id": self.operation_id,
                "branch": self.branch}

    @classmethod
    def from_json(cls, value: Any) -> "FrameKey":
        if not isinstance(value, dict) or set(value) != {
                "run_id", "invocation_id", "parent_id", "attempt_id",
                "child_id", "result_slot_id", "epoch", "operation_id", "branch"}:
            raise ValueError("invalid frame key")
        return cls(**value)


@dataclass(frozen=True)
class COWSourceBinding:
    operation_id: str
    branch: str
    source_branch: str
    revision: int
    snapshot: str
    endpoint_pin: str | None

    def __post_init__(self) -> None:
        if not _OP_ID.fullmatch(self.operation_id):
            raise ValueError("invalid source operation ID")
        if not isinstance(self.branch, str) or not self.branch:
            raise ValueError("target branch must be a nonempty string")
        if not isinstance(self.source_branch, str) or not self.source_branch:
            raise ValueError("source branch must be a nonempty string")
        if type(self.revision) is not int or self.revision < 0:
            raise ValueError("source revision must be a nonnegative integer")
        if not isinstance(self.snapshot, str) or not _HEX64.fullmatch(self.snapshot):
            raise ValueError("source snapshot must be lowercase SHA-256")

    def to_json(self) -> dict[str, Any]:
        return {"operation_id": self.operation_id, "branch": self.branch,
                "source_branch": self.source_branch,
                "revision": self.revision, "snapshot": self.snapshot,
                "endpoint_pin": self.endpoint_pin}

    @classmethod
    def from_json(cls, value: Any) -> "COWSourceBinding":
        if not isinstance(value, dict) or set(value) != {
                "operation_id", "branch", "source_branch", "revision", "snapshot", "endpoint_pin"}:
            raise ValueError("invalid COW source binding")
        return cls(**value)


class SlotReturns:
    """Order-independent, idempotent return slots for a parent frame."""

    def __init__(self, rows: list[dict[str, Any]] | None = None):
        self._rows: dict[str, dict[str, Any]] = {}
        for row in rows or []:
            key = FrameKey.from_json(row.get("frame_key"))
            source = COWSourceBinding.from_json(row.get("source_binding"))
            self.deliver(key, source, row.get("result_sha256"), row.get("value"))

    def deliver(self, key: FrameKey, source: COWSourceBinding,
                result_sha256: str, value: Any) -> bool:
        if not isinstance(key, FrameKey):
            raise TypeError("delivery requires a FrameKey")
        if not isinstance(source, COWSourceBinding):
            raise TypeError("delivery requires a COW source binding")
        if key.operation_id != source.operation_id or key.branch != source.branch:
            raise ValueError("frame and COW source binding disagree on operation or branch")
        if not isinstance(result_sha256, str) or not _HEX64.fullmatch(result_sha256):
            raise ValueError("result digest must be lowercase SHA-256")
        encoded_value = _canonical(value)
        if hashlib.sha256(encoded_value).hexdigest() != result_sha256:
            raise ValueError("result digest does not match the canonical returned value")
        # Detach caller-owned nested containers so a later mutation cannot
        # silently change a delivered slot after its digest was checked.
        value = json.loads(encoded_value.decode("utf-8"))
        slot = key.result_slot_id
        current = self._rows.get(slot)
        row = {"frame_key": key.to_json(), "source_binding": source.to_json(),
               "result_sha256": result_sha256,
               "value": value}
        if current is not None:
            if current != row:
                raise ValueError("conflicting or stale delivery for an occupied result slot")
            return False
        self._rows[slot] = row
        return True

    def get(self, slot_id: str) -> Any:
        row = self._rows.get(slot_id)
        if row is None:
            return None
        return json.loads(_canonical(row["value"]).decode("utf-8"))

    def to_json(self) -> dict[str, Any]:
        detached = json.loads(_canonical([self._rows[key] for key in sorted(self._rows)]).decode("utf-8"))
        return {"schema": 1, "slots": detached}

    @classmethod
    def from_json(cls, value: Any) -> "SlotReturns":
        if not isinstance(value, dict) or value.get("schema") != 1 or not isinstance(value.get("slots"), list):
            raise ValueError("invalid slot-return record")
        slots = cls(value["slots"])
        if len(slots._rows) != len(value["slots"]):
            raise ValueError("duplicate result slot in serialized return record")
        return slots


@dataclass(frozen=True)
class BranchHead:
    name: str
    revision: int
    tip: str
    root: str

    @classmethod
    def parse(cls, value: Any) -> "BranchHead":
        if isinstance(value, dict) and isinstance(value.get("branch"), dict):
            value = value["branch"]
        if (not isinstance(value, dict) or not isinstance(value.get("name"), str)
                or type(value.get("revision")) is not int or value["revision"] < 0
                or not isinstance(value.get("tip"), str) or not _HEX64.fullmatch(value["tip"])
                or not isinstance(value.get("root"), str) or not _HEX64.fullmatch(value["root"])):
            raise ReceiptError("response does not contain a valid branch head")
        return cls(value["name"], value["revision"], value["tip"], value["root"])


@dataclass(frozen=True)
class GenerationReceipt:
    operation_id: str
    branch: BranchHead
    snapshot: str
    raw: Mapping[str, Any]


@dataclass(frozen=True)
class GenerationResult:
    operation_id: str
    receipt: GenerationReceipt
    provisional_text: tuple[str, ...]
    answer: Mapping[str, Any]
    transport: str
    source_binding: COWSourceBinding | None = None


@dataclass(frozen=True)
class HistoryView:
    branch: str
    revision: int | None
    tip: str | None
    raw: Mapping[str, Any]
    messages: tuple[Mapping[str, Any], ...]


@dataclass(frozen=True)
class ServiceObservation:
    endpoint_pin: str | None
    endpoint_url: str
    capacity: Mapping[str, Any]
    identity_verified: bool = False


@dataclass(frozen=True)
class OperationObservation:
    operation_id: str
    state: str
    durable: bool
    scope: str
    raw: Mapping[str, Any]
    receipt: GenerationReceipt | None = None


@dataclass(frozen=True)
class OperationIntent:
    operation_id: str
    method: str
    path: str
    body: bytes
    branch: str | None
    revision: int | None
    frame_key: FrameKey | None
    endpoint_pin: str | None
    source_binding: COWSourceBinding | None = None


@dataclass(frozen=True)
class _Response:
    json_value: Any = None
    events: tuple[Mapping[str, Any], ...] = ()
    provisional_text: tuple[str, ...] = ()
    transport: str = "http"


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, OverflowError) as exc:
        raise CowClientError(f"request is not canonical JSON data: {exc}") from None


def _record_digest(record: Mapping[str, Any]) -> str:
    unsigned = {key: value for key, value in record.items() if key != "record_sha256"}
    return hashlib.sha256(_canonical(unsigned)).hexdigest()


class OperationJournal:
    """Atomic, private client intent journal; never stores auth headers."""

    def __init__(self, directory: str | os.PathLike[str]):
        self.directory = Path(directory)
        self._lock = threading.RLock()

    def _path(self, operation_id: str) -> Path:
        if not _OP_ID.fullmatch(operation_id):
            raise ValueError("invalid operation ID")
        digest = hashlib.sha256(operation_id.encode("ascii")).hexdigest()
        return self.directory / (digest + ".json")

    def _atomic(self, path: Path, record: Mapping[str, Any], *, create_only: bool = False) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        if os.name != "nt":
            try:
                self.directory.chmod(0o700)
            except OSError:
                pass
        raw = _canonical(dict(record)) + b"\n"
        tmp: Path | None = None
        fd = None
        try:
            fd, name = tempfile.mkstemp(prefix=".intent-", suffix=".tmp", dir=self.directory)
            tmp = Path(name)
            if os.name != "nt":
                os.fchmod(fd, 0o600)
            with os.fdopen(fd, "wb") as stream:
                fd = None
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            if create_only:
                # O_EXCL makes the intent-ID claim atomic across client threads/processes.
                try:
                    target_fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                except FileExistsError:
                    raise
                with os.fdopen(target_fd, "wb") as target:
                    target.write(raw)
                    target.flush()
                    os.fsync(target.fileno())
                tmp.unlink()
                tmp = None
            else:
                os.replace(tmp, path)
                tmp = None
            if os.name != "nt":
                dfd = os.open(self.directory, os.O_RDONLY)
                try:
                    os.fsync(dfd)
                finally:
                    os.close(dfd)
        except OSError as exc:
            raise CowClientError(f"cannot persist client operation journal: {exc}") from None
        finally:
            if fd is not None:
                os.close(fd)
            if tmp is not None:
                try:
                    tmp.unlink()
                except OSError:
                    pass

    def read(self, operation_id: str) -> dict[str, Any] | None:
        with self._lock:
            path = self._path(operation_id)
            try:
                raw = path.read_bytes()
            except FileNotFoundError:
                return None
            try:
                record = json.loads(raw.decode("utf-8"))
            except (UnicodeError, ValueError):
                raise CowClientError("operation journal is corrupt") from None
            if (not isinstance(record, dict) or record.get("schema") != _JOURNAL_SCHEMA
                    or record.get("operation_id") != operation_id
                    or record.get("record_sha256") != _record_digest(record)):
                raise CowClientError("operation journal integrity check failed")
            return record

    def begin(self, intent: OperationIntent, endpoint_url: str) -> tuple[dict[str, Any], bool]:
        raw_body = intent.body
        try:
            decoded = json.loads(raw_body.decode("utf-8"))
        except (UnicodeError, ValueError):
            raise CowClientError("mutation body must be UTF-8 JSON") from None
        if not isinstance(decoded, dict) or decoded.get("operation_id") != intent.operation_id:
            raise CowClientError("mutation body must bind the selected operation ID")
        record: dict[str, Any] = {
            "schema": _JOURNAL_SCHEMA,
            "operation_id": intent.operation_id,
            "method": intent.method,
            "path": intent.path,
            "body_b64": base64.b64encode(raw_body).decode("ascii"),
            "body_sha256": hashlib.sha256(raw_body).hexdigest(),
            "branch": intent.branch,
            "revision": intent.revision,
            "frame_key": None if intent.frame_key is None else intent.frame_key.to_json(),
            "endpoint_url": endpoint_url,
            "endpoint_pin": intent.endpoint_pin,
            "source_binding": None if intent.source_binding is None else intent.source_binding.to_json(),
            "state": "pending",
        }
        record["intent_sha256"] = _record_digest(record)
        record["record_sha256"] = _record_digest(record)
        with self._lock:
            existing = self.read(intent.operation_id)
            if existing is not None:
                if existing.get("intent_sha256") != record["intent_sha256"]:
                    raise OperationReuseError("operation ID is bound to different request bytes")
                if existing.get("state") == "complete":
                    return existing, False
                raise OperationIndeterminate("operation already has an unresolved journal intent")
            self._atomic(self._path(intent.operation_id), record, create_only=True)
        return record, True

    def complete(self, record: Mapping[str, Any], receipt: Mapping[str, Any], *,
                 answer: Mapping[str, Any] | None = None,
                 replay_source: Mapping[str, Any] | None = None) -> dict[str, Any]:
        with self._lock:
            current = self.read(str(record["operation_id"]))
            if current is None or current.get("intent_sha256") != record.get("intent_sha256"):
                raise CowClientError("journal intent changed while request was in flight")
            # Keep committed response bytes with the transport intent, in the
            # same atomic publication as its receipt. This is a cached output,
            # not another conversation/controller history or an execution grant.
            if current.get("state") == "complete":
                if _canonical(current.get("receipt")) != _canonical(dict(receipt)):
                    raise OperationReuseError("completed operation has a different receipt")
                if (answer is not None and "answer" in current
                        and _canonical(current["answer"]) != _canonical(dict(answer))):
                    raise ReceiptError("completed operation has a conflicting answer")
            complete = dict(current, state="complete", receipt=dict(receipt))
            if answer is not None:
                complete["answer"] = json.loads(_canonical(dict(answer)))
            if replay_source is not None:
                proof = json.loads(_canonical(dict(replay_source)))
                if (current.get("state") == "complete" and "replay_source" in current
                        and current["replay_source"] != proof):
                    raise ReceiptError("completed replay has a different original receipt")
                complete["replay_source"] = proof
            complete["record_sha256"] = _record_digest(complete)
            self._atomic(self._path(str(record["operation_id"])), complete)
            return complete

    def decode_body(self, record: Mapping[str, Any]) -> bytes:
        raw = base64.b64decode(record["body_b64"], validate=True)
        if hashlib.sha256(raw).hexdigest() != record.get("body_sha256"):
            raise CowClientError("journal request body hash mismatch")
        return raw


class Transport(Protocol):
    name: str

    def request(self, method: str, path: str, body: bytes | None = None,
                *, stream: bool = False) -> _Response: ...

    def upload_image(self, namespace_id: str, original: bytes) -> _Response: ...


class HTTPTransport:
    name = "http"

    def __init__(self, base_url: str, *, api_key: str | None = None, timeout: float = 1800,
                 max_stream_bytes: int = 32 * 1024 * 1024,
                 max_event_bytes: int = 1024 * 1024, notice_handler=None, stream_handler=None):
        parts = urlsplit(base_url)
        if (parts.scheme not in ("http", "https") or not parts.hostname or parts.username
                or parts.password or parts.query or parts.fragment):
            raise ValueError("COW URL must be an http(s) origin without credentials, query or fragment")
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be finite and positive")
        if max_stream_bytes <= 0 or max_event_bytes <= 0 or max_event_bytes > max_stream_bytes:
            raise ValueError("invalid stream bounds")
        if notice_handler is not None and not callable(notice_handler):
            raise ValueError("notice_handler must be callable")
        if stream_handler is not None and not callable(stream_handler):
            raise ValueError("stream_handler must be callable")
        self.notice_handler = notice_handler
        self.stream_handler = stream_handler
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.max_stream_bytes = max_stream_bytes
        self.max_event_bytes = max_event_bytes

    def request(self, method: str, path: str, body: bytes | None = None,
                *, stream: bool = False) -> _Response:
        return self._request(method, path, body, stream=stream)

    def upload_image(self, namespace_id: str, original: bytes) -> _Response:
        return self._request("POST", "/cow/images?" + urlencode({"namespace": namespace_id}),
            original, image_digest=hashlib.sha256(original).hexdigest())

    def _request(self, method: str, path: str, body: bytes | None = None,
                 *, stream: bool = False, image_digest: str | None = None) -> _Response:
        headers = {"Accept": "application/x-ndjson" if stream else "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json; charset=utf-8"
        if image_digest is not None:
            headers["Content-Type"] = "application/octet-stream"
            headers["X-COW-Content-SHA256"] = image_digest
        if self.api_key:
            headers["Authorization"] = "Bearer " + self.api_key
        request = Request(self.base_url + path, data=body, headers=headers, method=method)
        try:
            response = urlopen(request, timeout=self.timeout)
        except HTTPError as exc:
            if 300 <= exc.code < 400:
                exc.close()
                raise OperationIndeterminate("COW redirect refused; inspect the original operation status before retrying") from None
            with exc:
                detail = exc.read(16_384).decode("utf-8", "replace")
            try:
                decoded = json.loads(detail)
                detail = decoded.get("error", detail) if isinstance(decoded, dict) else detail
            except ValueError:
                pass
            if exc.code < 500:
                raise RequestRejected(f"COW HTTP {exc.code}: {detail}", status_code=exc.code) from None
            raise OperationIndeterminate(f"COW HTTP {exc.code}; inspect operation status: {detail}") from None
        except (URLError, http.client.HTTPException, TimeoutError, OSError) as exc:
            raise OperationIndeterminate(f"COW transport failed; inspect operation status: {exc}") from None
        if not stream:
            try:
                with response:
                    raw = response.read(8 * 1024 * 1024 + 1)
            except (http.client.HTTPException, TimeoutError, OSError) as exc:
                raise OperationIndeterminate(f"COW response ended unexpectedly: {exc}") from None
            if len(raw) > 8 * 1024 * 1024:
                raise ClientLimitError("JSON response exceeds 8 MiB")
            try:
                value = json.loads(raw.decode("utf-8"))
            except (UnicodeError, ValueError):
                raise CowClientError("COW returned invalid JSON") from None
            return _Response(json_value=value, transport=self.name)
        events: list[Mapping[str, Any]] = []
        texts: list[str] = []
        total = 0
        try:
            with response:
                while True:
                    line = response.readline(self.max_event_bytes + 1)
                    if not line:
                        break
                    total += len(line)
                    if len(line) > self.max_event_bytes or total > self.max_stream_bytes:
                        raise ClientLimitError("COW event stream exceeded configured bounds")
                    try:
                        event = json.loads(line.decode("utf-8"))
                    except (UnicodeError, ValueError):
                        raise CowClientError("COW sent malformed NDJSON") from None
                    if not isinstance(event, dict) or not isinstance(event.get("event"), str):
                        raise CowClientError("COW sent an invalid event")
                    events.append(event)
                    if (self.notice_handler is not None and event["event"] in {
                            "source_recomputation_started", "source_recomputed",
                            "source_recomputation_failed"}):
                        # Provisional operational observations,never snapshot
                        # authority. Detach so UI callbacks cannot alter receipt
                        # validation or the server's committed answer.
                        self.notice_handler(json.loads(_canonical(event)))
                    if event["event"] == "text":
                        text = event.get("text")
                        if not isinstance(text, str):
                            raise CowClientError("COW text event lacks text")
                        if self.stream_handler is not None:
                            self.stream_handler(text)
                        texts.append(text)
        except (http.client.HTTPException, TimeoutError, OSError) as exc:
            raise OperationIndeterminate(f"COW stream ended unexpectedly: {exc}") from None
        return _Response(events=tuple(events), provisional_text=tuple(texts), transport=self.name)


class CliTransport:
    """Conformance transport that executes the installed COW CLI program."""

    name = "cli"

    _SETTING_FLAGS = {
        "temperature": "--temperature", "min_p": "--min-p", "top_k": "--top-k",
        "top_p": "--top-p", "typical_p": "--typical-p", "xtc_probability": "--xtc-probability",
        "xtc_threshold": "--xtc-threshold", "mirostat": "--mirostat",
        "mirostat_tau": "--mirostat-tau", "mirostat_eta": "--mirostat-eta",
        "adaptive_target": "--adaptive-target", "adaptive_decay": "--adaptive-decay",
        "dynatemp_range": "--dynatemp-range", "dynatemp_exponent": "--dynatemp-exponent",
        "dry_multiplier": "--dry-multiplier", "dry_base": "--dry-base",
        "dry_allowed_length": "--dry-allowed-length", "dry_penalty_last_n": "--dry-penalty-last-n",
    }

    def __init__(self, base_url: str, cli_script: str | os.PathLike[str], *, state_dir: str | os.PathLike[str],
                 api_key: str | None = None, timeout: float = 1800,
                 max_capture_bytes: int = 32 * 1024 * 1024,
                 python_executable: str | None = None):
        self.http_identity = HTTPTransport(base_url, api_key=api_key, timeout=timeout)
        self.base_url = self.http_identity.base_url
        self.cli_script = str(Path(cli_script))
        self.state_dir = str(Path(state_dir))
        self.api_key = api_key
        self.timeout = timeout
        self.max_capture_bytes = max_capture_bytes
        self.python_executable = python_executable or sys.executable

    def upload_image(self, namespace_id: str, original: bytes) -> _Response:
        # The existing CLI consumes a local byte file; it sends raw bytes, not
        # this path. The file is private and always removed, including failure.
        with tempfile.NamedTemporaryFile("wb", suffix=".image", delete=False) as stream:
            stream.write(original)
            temporary = Path(stream.name)
        try:
            return self._run("upload-image", ["--namespace-id", namespace_id, "--file", str(temporary)],
                             mutation=False)
        finally:
            temporary.unlink(missing_ok=True)

    def _argv(self, command: str, args: list[str], *, machine_result: bool = False) -> list[str]:
        prefix = [self.python_executable, self.cli_script, "--url", self.base_url,
                  "--timeout", str(self.timeout), "--state-dir", self.state_dir]
        if machine_result:
            prefix.append("--machine-result")
        return [*prefix, command, *args]

    def _run(self, command: str, args: list[str], *, mutation: bool,
             streamed: bool = False) -> _Response:
        Path(self.state_dir).mkdir(parents=True, exist_ok=True)
        if os.name != "nt":
            try:
                Path(self.state_dir).chmod(0o700)
            except OSError:
                pass
        env = os.environ.copy()
        if self.api_key:
            env["COW_API_KEY"] = self.api_key
        try:
            process = subprocess.Popen(self._argv(command, args, machine_result=streamed or mutation), stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, env=env)
        except OSError as exc:
            raise OperationIndeterminate(f"could not start COW CLI subprocess: {exc}") from None
        output: dict[str, bytearray] = {"stdout": bytearray(), "stderr": bytearray()}
        overflow = threading.Event()

        def drain(name: str, pipe: Any) -> None:
            while True:
                chunk = pipe.read(65536)
                if not chunk:
                    return
                target = output[name]
                if len(target) + len(chunk) > self.max_capture_bytes:
                    overflow.set()
                    # Continue draining so the child cannot block on a full pipe.
                    continue
                target.extend(chunk)

        readers = [threading.Thread(target=drain, args=(name, pipe), daemon=True)
                   for name, pipe in (("stdout", process.stdout), ("stderr", process.stderr))]
        for reader in readers:
            reader.start()
        try:
            deadline = time.monotonic() + self.timeout
            while process.poll() is None:
                if overflow.is_set():
                    process.kill()
                    raise ClientLimitError("COW CLI output exceeded configured capture bound")
                if time.monotonic() >= deadline:
                    process.kill()
                    raise OperationIndeterminate("COW CLI timed out; inspect the original operation ID")
                time.sleep(0.02)
            for reader in readers:
                reader.join(timeout=2)
        finally:
            if process.poll() is None:
                process.kill()
            process.wait()
            for pipe in (process.stdout, process.stderr):
                if pipe:
                    pipe.close()
        if overflow.is_set():
            raise ClientLimitError("COW CLI output exceeded configured capture bound")
        stdout = bytes(output["stdout"])
        stderr = bytes(output["stderr"])
        try:
            out_text = stdout.decode("utf-8")
            err_text = stderr.decode("utf-8")
        except UnicodeError:
            raise CowClientError("COW CLI returned non-UTF-8 output") from None
        if process.returncode != 0:
            detail = err_text.strip()[-4096:]
            if mutation:
                # Exit 2 also covers lost/malformed replies after real durable
                # publication. Only an explicit, operation-bound machine error
                # can establish rejection; legacy/unknown failures stay unknown.
                try:
                    failure = json.loads(out_text)
                except ValueError:
                    failure = None
                expected_op = (args[args.index('--operation-id') + 1]
                               if '--operation-id' in args else None)
                if (isinstance(failure, dict) and set(failure) == {'schema', 'error'}
                        and type(failure['schema']) is int and failure['schema'] == 1
                        and isinstance(failure['error'], dict)
                        and set(failure['error']) == {'outcome', 'operation_id', 'message'}
                        and failure['error'].get('outcome') == 'rejected'
                        and failure['error'].get('operation_id') in (None, expected_op)
                        and isinstance(failure['error'].get('message'), str)):
                    raise RequestRejected(f"COW CLI rejected request: {detail}")
                raise OperationIndeterminate(f"COW CLI failed; inspect operation status: {detail}")
            raise CowClientError(f"COW CLI command failed: {detail}")
        if streamed:
            try:
                envelope = json.loads(out_text)
            except ValueError:
                raise CowClientError("COW CLI machine result is malformed JSON") from None
            if (not isinstance(envelope, dict) or set(envelope) != {"schema", "answer", "receipt"}
                    or envelope.get("schema") != 1 or not isinstance(envelope.get("answer"), dict)
                    or ("text" in envelope["answer"]
                        and not isinstance(envelope["answer"].get("text"), str))
                    or not isinstance(envelope.get("receipt"), dict)):
                raise ReceiptError("COW CLI machine result lacks the exact answer and durable receipt")
            return _Response(events=({"event": "complete", "answer": envelope["answer"],
                                      "receipt": envelope["receipt"]},),
                             transport=self.name)
        if mutation:
            marker = "durable receipt:\n"
            index = err_text.find(marker)
            if index >= 0:
                try:
                    value = json.loads(err_text[index + len(marker):])
                except ValueError:
                    raise CowClientError("COW CLI receipt is malformed JSON") from None
            else:
                value = json.loads(out_text)
            return _Response(json_value=value, transport=self.name)
        try:
            return _Response(json_value=json.loads(out_text), transport=self.name)
        except ValueError:
            raise CowClientError("COW CLI returned invalid JSON") from None

    def request(self, method: str, path: str, body: bytes | None = None,
                *, stream: bool = False) -> _Response:
        parsed = urlsplit(path)
        route = parsed.path
        data: dict[str, Any] = {}
        if body is not None:
            try:
                data = json.loads(body.decode("utf-8"))
            except (UnicodeError, ValueError):
                raise CowClientError("CLI transport request is invalid JSON") from None
        if method == "GET":
            query = parse_qs(parsed.query)
            if route == "/cow/status":
                return self._run("status", [], mutation=False)
            if route == "/cow/branches":
                return self._run("branches", [], mutation=False)
            if route == "/cow/head":
                all_branches = self._run("branches", [], mutation=False).json_value
                branch = query.get("branch", [None])[0]
                rows = all_branches.get("branches", []) if isinstance(all_branches, dict) else []
                found = next((row for row in rows if row.get("name") == branch), None)
                if found is None:
                    raise RequestRejected("COW branch does not exist")
                return _Response(json_value=found, transport=self.name)
            if route == "/cow/workspace/history":
                return self._run("history", ["--branch", query["branch"][0]], mutation=False)
            if route == "/cow/operation":
                return self._run("operation", ["--operation-id", query["operation"][0]], mutation=False)
            raise CowClientError(f"COW CLI conformance transport does not support {route}")

        if method != "POST":
            raise CowClientError("COW CLI transport supports only GET and POST")
        branch = data.get("branch")
        op = data.get("operation_id")
        args: list[str]
        command: str
        is_stream = False
        if route == "/cow/namespace":
            command, args = "namespace", ["--title", data["title"], "--operation-id", op]
        elif route in ("/cow/text/context", "/cow/text/prepare"):
            messages = data.get("messages")
            if route.endswith("/context"):
                with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as stream_file:
                    json.dump(messages, stream_file, ensure_ascii=False)
                    temp_path = stream_file.name
                try:
                    command = "load"
                    args = ["--messages-file", temp_path, "--namespace-id", data["namespace_id"],
                            "--branch", branch, "--operation-id", op]
                    return self._run(command, args, mutation=True, streamed=True)
                finally:
                    Path(temp_path).unlink(missing_ok=True)
            first = messages[0]["content"]
            if isinstance(first, list):
                if len(messages) != 1 or messages[0].get("role") != "user":
                    raise CowClientError("CLI image preparation requires one ordered user input")
                with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".parts", delete=False) as stream_file:
                    json.dump(first, stream_file, ensure_ascii=False)
                    temporary = Path(stream_file.name)
                try:
                    return self._run("prepare", ["--branch", branch, "--namespace-id", data["namespace_id"],
                        "--parts-file", str(temporary), "--operation-id", op], mutation=True, streamed=True)
                finally:
                    temporary.unlink(missing_ok=True)
            command, args = "prepare", ["--branch", branch, "--namespace-id", data["namespace_id"],
                                         "--text", first, "--operation-id", op]
            is_stream = True
        elif route in ("/cow/text/answer", "/cow/text/ask", "/cow/text/resume", "/cow/text/append-user"):
            revision = data.get("revision")
            if type(revision) is not int or revision < 0:
                raise CowClientError("generation request lacks its expected branch revision")
            branch_rows = self._run("branches", [], mutation=False).json_value
            branches = branch_rows.get("branches", []) if isinstance(branch_rows, dict) else []
            current = next((row for row in branches
                            if isinstance(row, dict) and row.get("name") == branch), None)
            if current is None:
                raise RequestRejected("COW branch does not exist")
            if type(current.get("revision")) is not int or current["revision"] != revision:
                raise RequestRejected("branch revision changed before CLI dispatch")
            command = {"/cow/text/answer": "answer", "/cow/text/ask": "ask",
                       "/cow/text/resume": "continue", "/cow/text/append-user": "append-user"}[route]
            args = ["--branch", branch, "--revision", str(revision),
                    "--max-tokens", str(data["max_tokens"]), "--operation-id", op]
            if command in ("ask", "append-user"):
                args.extend(["--text", data["content"]])
            if data.get("grammar_state") is not None:
                args.extend(["--grammar-state", data["grammar_state"]])
            settings = data.get("settings")
            if settings is not None:
                if not isinstance(settings, dict):
                    raise CowClientError("settings must be an object")
                for key, value in settings.items():
                    flag = self._SETTING_FLAGS.get(key)
                    if flag is None:
                        raise CowClientError(f"COW CLI does not expose setting {key!r}")
                    args.extend([flag, str(value)])
            is_stream = True
        elif route == "/cow/fork":
            command, args = "fork", ["--source-branch", data["source_branch"], "--snapshot", data["snapshot"],
                                      "--name", data["name"], "--operation-id", op]
        elif route == "/cow/text/retry":
            command, args = "retry", ["--from-operation", data["from_operation"],
                                      "--branch", branch, "--operation-id", op]
            settings = data.get("settings")
            if settings:
                for key, value in settings.items():
                    flag = self._SETTING_FLAGS.get(key)
                    if flag is None:
                        raise CowClientError(f"COW CLI does not expose setting {key!r}")
                    args.extend([flag, str(value)])
            is_stream = True
        else:
            raise CowClientError(f"COW CLI conformance transport does not support {route}")
        return self._run(command, args, mutation=True, streamed=is_stream or stream)


_COMPLETION_ROUTE = '/cow/training/job-reconciliations'
_COMPLETION_APPROVAL = 'adopt-completed-original-native-v1'
_COMPLETION_HASHES = {'job_record_sha256','evidence_sha256','candidate_sha256',
                      'native_configuration_sha256','source_closure_sha256','runtime_environment_sha256'}
_COMPLETION_ACTIONS = {'eligible':['adopt_original_completion'],'adoption_pending':['resume_original_adoption'],
                       'adopted':['reconcile_learning_run'],'unavailable':['hold'],'ineligible':['hold']}
_COMPLETION_REASONS = {'eligible':{'original_completion_verified'},'adoption_pending':{'original_adoption_pending'},
    'adopted':{'original_adoption_verified'},'unavailable':{'training_boundary_busy','original_process_live','original_evidence_incomplete'},
    'ineligible':{'legacy_provenance_missing','original_evidence_invalid','adoption_transaction_conflict','original_job_already_complete'}}


def _completion_approval(body):
    fields={'operation_id','job_id','expected_job_record_sha256','expected_evidence_sha256','expected_candidate_sha256','approval'}
    if (type(body) is not dict or set(body)!=fields or body.get('approval')!=_COMPLETION_APPROVAL
            or any(type(body.get(k)) is not str or not _OP_ID.fullmatch(body[k]) for k in ('operation_id','job_id'))
            or any(type(body.get(k)) is not str or not _HEX64.fullmatch(body[k]) for k in fields if k.startswith('expected_'))):
        raise ReceiptError('Completion adoption needs exact original CAS identities and explicit owner approval')
    return dict(body)


def validate_completion_inspection(value, *, job_id, model_contract_id):
    """Validate the owner recovery API; a saved intent is not a completed ack."""
    common={'schema','kind','job_id','model_contract_id','state','reason_code','next_actions','eligible',
            'current_evidence_verified','message','model_calls_started','native_jobs_started','promoted'}
    if (type(value) is not dict or type(value.get('schema')) is not int or value['schema']!=1
            or value.get('kind')!='pcc.native-completion-recovery.v1' or value.get('job_id')!=job_id
            or type(job_id) is not str or not _OP_ID.fullmatch(job_id)
            or type(model_contract_id) is not str or not _HEX64.fullmatch(model_contract_id)
            or value.get('model_contract_id')!=model_contract_id):
        raise ReceiptError('Completion inspection belongs to another job/model or unsupported API')
    state=value.get('state')
    if type(state) is not str or state not in _COMPLETION_ACTIONS:raise ReceiptError('Unknown completion inspection state')
    verified=state in ('eligible','adoption_pending','adopted')
    fields=common | (_COMPLETION_HASHES if verified else set())
    if state=='adoption_pending':fields|={'pending_operation_id','pending_request'}
    if state=='adopted':fields.add('adoption_operation_id')
    actions=(['inspect_original_job','learning_status'] if state=='ineligible' and value.get('reason_code')=='original_job_already_complete' else _COMPLETION_ACTIONS[state])
    if (set(value)!=fields or value.get('eligible') is not (state=='eligible')
            or value.get('current_evidence_verified') is not verified or value.get('promoted') is not False
            or type(value.get('message')) is not str or len(value['message'])>512
            or type(value.get('reason_code')) is not str or value['reason_code'] not in _COMPLETION_REASONS[state]
            or value.get('next_actions')!=actions
            or any(type(value.get(k)) is not int or value[k]!=0 for k in ('model_calls_started','native_jobs_started'))):
        raise ReceiptError('Completion inspection state/action/evidence contract differs')
    if verified and any(type(value.get(k)) is not str or not _HEX64.fullmatch(value[k]) for k in _COMPLETION_HASHES):
        raise ReceiptError('Completion inspection has incomplete original evidence identities')
    if state=='adoption_pending':
        original=_completion_approval(value['pending_request'])
        if (value.get('pending_operation_id')!=original['operation_id'] or original['job_id']!=job_id
                or any(original['expected_'+k]!=value[k] for k in ('job_record_sha256','evidence_sha256','candidate_sha256'))):
            raise ReceiptError('Pending adoption is not the exact original job/approval')
    if state=='adopted' and (type(value.get('adoption_operation_id')) is not str or not _OP_ID.fullmatch(value['adoption_operation_id'])):
        raise ReceiptError('Completed original adoption identity is invalid')
    return json.loads(_canonical(value))


class CowClient:
    def __init__(self, transport: Transport, *, endpoint_url: str, journal: OperationJournal,
                 endpoint_pin: str | None = None):
        self.transport = transport
        self.endpoint_url = endpoint_url.rstrip("/")
        self.endpoint_pin = endpoint_pin
        self.journal = journal

    @classmethod
    def http(cls, base_url: str, *, journal: OperationJournal,
             api_key: str | None = None, endpoint_pin: str | None = None,
             timeout: float = 1800, max_stream_bytes: int = 32 * 1024 * 1024,
             notice_handler=None, stream_handler=None) -> "CowClient":
        transport = HTTPTransport(base_url, api_key=api_key, timeout=timeout,
                                  max_stream_bytes=max_stream_bytes, notice_handler=notice_handler,
                                  stream_handler=stream_handler)
        return cls(transport, endpoint_url=transport.base_url, journal=journal,
                   endpoint_pin=endpoint_pin)

    @classmethod
    def cli(cls, base_url: str, cli_script: str | os.PathLike[str], *, journal: OperationJournal,
            state_dir: str | os.PathLike[str], api_key: str | None = None,
            endpoint_pin: str | None = None, timeout: float = 1800) -> "CowClient":
        transport = CliTransport(base_url, cli_script, state_dir=state_dir,
                                 api_key=api_key, timeout=timeout)
        return cls(transport, endpoint_url=transport.base_url, journal=journal,
                   endpoint_pin=endpoint_pin)

    def status(self) -> ServiceObservation:
        value = self.transport.request("GET", "/cow/status").json_value
        if not isinstance(value, dict):
            raise CowClientError("COW status response must be an object")
        return ServiceObservation(self.endpoint_pin, self.endpoint_url, value, False)

    def require_capabilities(self, model_contract_id, execution_profile_id, *, required=('text','inline_grammars')):
        from .capabilities import observe
        return observe(self.transport, model_contract_id=model_contract_id,
                       execution_profile_id=execution_profile_id, required=required)

    def head(self, branch: str) -> BranchHead:
        value = self.transport.request("GET", "/cow/head?" + urlencode({"branch": branch})).json_value
        return BranchHead.parse(value)

    def image_namespace(self, source: BranchHead) -> str:
        """Observe namespace and exact source together; no mutation or head rebase."""
        if not isinstance(source, BranchHead):
            raise ValueError("observed source head required")
        value = self.transport.request("GET", "/cow/head?" + urlencode({"branch": source.name})).json_value
        if BranchHead.parse(value) != source:
            raise RequestRejected("image feedback source head changed")
        namespace = value.get("namespace_id") if isinstance(value, dict) else None
        if type(namespace) is not str or re.fullmatch("[0-9a-f]{32}", namespace) is None:
            raise ReceiptError("source response lacks an exact image namespace")
        return namespace

    def history(self, branch: str) -> HistoryView:
        value = self.transport.request("GET", "/cow/workspace/history?" + urlencode({"branch": branch})).json_value
        if not isinstance(value, dict) or value.get("id") != branch:
            raise CowClientError("COW history response is not bound to the requested branch")
        messages = value.get("messages", [])
        if not isinstance(messages, list) or any(not isinstance(row, dict) for row in messages):
            raise CowClientError("COW history messages have an invalid shape")
        revision = value.get("revision")
        tip = value.get("tip")
        if revision is not None and (type(revision) is not int or revision < 0):
            raise CowClientError("COW history revision is invalid")
        if tip is not None and (not isinstance(tip, str) or not _HEX64.fullmatch(tip)):
            raise CowClientError("COW history tip is invalid")
        return HistoryView(branch, revision, tip, value, tuple(messages))

    def context_budget(self, branch: str) -> Mapping[str, Any]:
        """Read a snapshot-bound context count without preparing or generating."""
        if type(branch) is not str or not branch:
            raise ValueError('branch name required')
        value=self.transport.request('GET','/cow/context-budget?'+urlencode({'branch':branch})).json_value
        fields={'schema','branch','revision','snapshot','model_contract_id','execution_profile_id',
                'capacity_tokens','used_tokens','remaining_tokens'}
        if (type(value) is not dict or set(value)!=fields or type(value['schema']) is not int
                or value['schema']!=1 or value['branch']!=branch
                or type(value['revision']) is not int or value['revision']<0
                or type(value['snapshot']) is not str or not _HEX64.fullmatch(value['snapshot'])
                or any(type(value[k]) is not str or not value[k] for k in ('model_contract_id','execution_profile_id'))
                or any(type(value[k]) is not int for k in ('capacity_tokens','used_tokens','remaining_tokens'))
                or value['capacity_tokens']<=0 or value['used_tokens']<0
                or value['remaining_tokens']<0
                or value['used_tokens']+value['remaining_tokens']!=value['capacity_tokens']):
            raise CowClientError('Invalid or mismatched COW context budget')
        return value

    def text_context_preflight(self, source: BranchHead, mode: str, content: str | None,
                               max_tokens: int) -> Mapping[str, Any]:
        """Count an exact text request without dispatching a model operation."""
        if not isinstance(source,BranchHead) or mode not in ('answer','ask','append_user','continue'):
            raise ValueError('bound source and supported text mode required')
        if type(max_tokens) is not int or not 1<=max_tokens<=65536:
            raise ValueError('bounded positive output token request required')
        if (mode in ('ask','append_user') and type(content) is not str
                or mode in ('answer','continue') and content is not None):
            raise ValueError('content does not match text request mode')
        body=dict(branch=source.name,revision=source.revision,snapshot=source.tip,
                  mode=mode,content=content,max_tokens=max_tokens)
        value=self.transport.request('POST','/cow/text/context-preflight',_canonical(body)).json_value
        fields={'schema','branch','revision','snapshot','model_contract_id','execution_profile_id',
                'mode','content_sha256','capacity_tokens','used_tokens','input_tokens',
                'requested_output_tokens','available_output_tokens','fits'}
        content_sha=None if content is None else hashlib.sha256(content.encode('utf-8')).hexdigest()
        if (type(value) is not dict or set(value)!=fields or type(value['schema']) is not int
                or value['schema']!=1 or value['branch']!=source.name
                or type(value['revision']) is not int or value['revision']!=source.revision
                or value['snapshot']!=source.tip or value['mode']!=mode or value['content_sha256']!=content_sha
                or value['requested_output_tokens']!=max_tokens
                or any(type(value[k]) is not str or not value[k] for k in ('model_contract_id','execution_profile_id'))
                or any(type(value[k]) is not int or value[k]<0 for k in
                       ('capacity_tokens','used_tokens','input_tokens','requested_output_tokens','available_output_tokens'))
                or value['capacity_tokens']<=0 or value['used_tokens']>value['capacity_tokens']
                or value['available_output_tokens']!=max(0,value['capacity_tokens']-value['used_tokens']-value['input_tokens'])
                or type(value['fits']) is not bool
                or value['fits']!=(value['used_tokens']+value['input_tokens']+max_tokens<=value['capacity_tokens'])):
            raise CowClientError('Invalid or mismatched COW text context preflight')
        return value

    def operation(self, operation_id: str) -> OperationObservation:
        try:
            response = self.transport.request("GET", "/cow/operation?" + urlencode({"operation": operation_id}))
        except RequestRejected as exc:
            if "404" in str(exc) or "not exist" in str(exc).lower():
                raise OperationIndeterminate("COW operation is unknown in this process; commit state is indeterminate") from None
            raise
        value = response.json_value
        if not isinstance(value, dict) or value.get("operation_id") != operation_id:
            raise CowClientError("COW operation lookup is not bound to its query")
        durable = value.get("durable")
        if type(durable) is not bool:
            raise CowClientError("COW operation lookup lacks durable status")
        receipt = None
        if durable:
            receipt = self._receipt(value.get("receipt"), operation_id=operation_id)
        scope = value.get("scope")
        state = value.get("state")
        if not isinstance(scope, str) or not isinstance(state, str):
            raise CowClientError("COW operation status lacks scope or state")
        return OperationObservation(operation_id, state, durable, scope, value, receipt)

    def operation_diagnostic(self, operation_id: str) -> Mapping[str, Any]:
        """Read private live failure details; this is not a settlement receipt."""
        op=self._operation_id(operation_id)
        value=self.transport.request('GET','/cow/operation-diagnostic?'+urlencode({'operation':op})).json_value
        if (type(value) is not dict or value.get('operation_id')!=op
                or value.get('scope')!='coordinator-process'
                or value.get('diagnostic_scope')!='coordinator-process-only'
                or type(value.get('durable')) is not bool
                or type(value.get('branch')) is not str
                or type(value.get('state')) is not str
                or type(value.get('publication_retryable')) is not bool
                or 'failure' not in value):
            raise CowClientError('Invalid or mismatched COW operation diagnostic')
        failure=value['failure']
        if failure is not None and (type(failure) is not dict or set(failure)!={'type','message'}
                or type(failure['type']) is not str or type(failure['message']) is not str
                or len(failure['message'])>4096 or value['state']!='failed'):
            raise CowClientError('Invalid COW failure diagnostic')
        return value

    def cancel_generation(self, operation_id: str) -> Mapping[str, Any]:
        """Request transient cancellation; inspect operation() to learn whether it won."""
        op=self._operation_id(operation_id)
        value=self.transport.request("POST","/cow/cancel",_canonical({"operation_id":op})).json_value
        if (not isinstance(value,dict) or set(value)!={"operation_id","active","cancel_requested"}
                or value.get("operation_id")!=op or type(value.get("active")) is not bool
                or type(value.get("cancel_requested")) is not bool
                or value["cancel_requested"] and not value["active"]):
            raise CowClientError("COW cancellation response is invalid or mismatched")
        return value

    def pause_generation(self, operation_id: str) -> Mapping[str, Any]:
        """Request a smaller consumed work bound, not durable settlement.

        Keep a short, independent control connection; never change the active
        generation transport's timeout, request body, journal or operation ID.
        """
        op=self._operation_id(operation_id)
        if not isinstance(self.transport,HTTPTransport):
            raise CowClientError('Generation pause control requires HTTP transport')
        control=HTTPTransport(self.transport.base_url,api_key=self.transport.api_key,
            timeout=min(2.0,self.transport.timeout),max_stream_bytes=4096,max_event_bytes=4096)
        value=control.request('POST','/cow/pause',_canonical({'operation_id':op})).json_value
        if (not isinstance(value,dict) or set(value)!={'operation_id','active','pause_requested'}
                or value.get('operation_id')!=op or type(value.get('active')) is not bool
                or type(value.get('pause_requested')) is not bool
                or value['pause_requested'] and not value['active']):
            raise CowClientError('COW pause response is invalid or mismatched')
        return value

    def recover(self, operation_id: str) -> OperationObservation:
        record = self.journal.read(operation_id)
        if record is None:
            raise OperationIndeterminate("no original client intent is available for this operation")
        if record["state"] == "complete":
            receipt = self._receipt(record.get("receipt"), operation_id=operation_id,
                                    expected_branch=record.get("branch"),
                                    expected_revision=(None if record.get("revision") is None
                                                       else record["revision"] + 1))
            self._validate_receipt_against_record(receipt, record)
            return OperationObservation(operation_id, "durable", True, "client-journal",
                                        {"receipt": dict(receipt.raw)}, receipt)
        observation = self.operation(operation_id)
        if observation.durable:
            self._validate_receipt_against_record(observation.receipt, record)
            self.journal.complete(record, observation.receipt.raw)
        return observation

    def register_grammars(self, definitions: Mapping[str, Any],
                          operation_id: str | None = None) -> Mapping[str, Any]:
        """Journal immutable grammar admission; unresolved sends require exact replay."""
        if isinstance(self.transport,CliTransport):
            raise RequestRejected("grammar registration requires the HTTP transport")
        if (type(definitions) is not dict or set(definitions)!={"schema","states"}
                or type(definitions["schema"]) is not int or definitions["schema"]!=1
                or type(definitions["states"]) is not dict
                or not 1<=len(definitions["states"])<=64
                or any(type(name) is not str or not name for name in definitions["states"])):
            raise ValueError("closed bounded grammar definition required")
        detached=json.loads(_canonical(definitions))
        if len(_canonical(detached))>4*1024*1024:
            raise ValueError("grammar definition exceeds4MiB")
        op=self._operation_id(operation_id)
        body=dict(detached,operation_id=op)
        return self._mutate(op,"/cow/grammars",body,stream=False).json_value

    def create_namespace(self, title: str, operation_id: str | None = None) -> Mapping[str, Any]:
        op = self._operation_id(operation_id)
        body = {"title": title, "operation_id": op}
        response = self._mutate(op, "/cow/namespace", body, stream=False)
        value = response.json_value
        if not isinstance(value, dict) or not isinstance(value.get("namespace_id"), str) or not value["namespace_id"]:
            raise ReceiptError("namespace response lacks namespace_id")
        return value

    def load_context(self, branch: str, namespace_id: str, messages: list[Mapping[str, Any]],
                     operation_id: str | None = None, *, frame_key: FrameKey | None = None) -> GenerationResult:
        op = self._operation_id(operation_id)
        body = {"branch": branch, "namespace_id": namespace_id, "messages": list(messages),
                "operation_id": op, "stream": True}
        return self._generation_mutation(op, "/cow/text/context", body, branch=branch,
                                         revision=None, frame_key=frame_key)

    def prepare(self, branch: str, namespace_id: str, text: str,
                operation_id: str | None = None, *, frame_key: FrameKey | None = None,
                images: tuple[ImageUploadReceipt, ...] = ()) -> GenerationResult:
        if not isinstance(images, (tuple, list)) or len(images) > 8:
            raise ValueError("image inputs must be at most eight verified upload receipts")
        for image in images:
            if (not isinstance(image, ImageUploadReceipt) or image.namespace_id != namespace_id
                    or image.endpoint_url != self.endpoint_url or image.endpoint_pin != self.endpoint_pin):
                raise ValueError("image receipt belongs to another namespace or endpoint")
        content = text
        if images:
            if type(text) is not str:
                raise ValueError("image question must be text")
            content = [dict(type="image", image_id=image.image_id) for image in images]
            content.append(dict(type="text", text=text))
        op = self._operation_id(operation_id)
        body = {"branch": branch, "namespace_id": namespace_id,
                "messages": [{"role": "user", "content": content}],
                "operation_id": op, "stream": True}
        return self._generation_mutation(op, "/cow/text/prepare", body, branch=branch,
                                         revision=None, frame_key=frame_key)

    def upload_image(self, namespace_id: str, original: bytes) -> ImageUploadReceipt:
        """Upload immutable bytes; the server owns grants, retention and encoding.

        Uploading is content-addressed, not a model/branch mutation. Generation
        subsequently journals only acknowledged IDs. No implicit upload retry,
        model forwarding, remote URL fetch or stateless inference fallback occurs.
        """
        if type(namespace_id) is not str or re.fullmatch("[0-9a-f]{32}", namespace_id) is None:
            raise ValueError("image namespace must be an exact namespace identity")
        width, height, media_type = _image_metadata(original)
        if not getattr(self.transport, "api_key", None):
            raise ValueError("image upload requires a configured API key")
        digest = hashlib.sha256(original).hexdigest()
        value = self.transport.upload_image(namespace_id, original).json_value
        if (not isinstance(value, dict) or value.get("namespace_id") != namespace_id
                or value.get("image_id") != digest or type(value.get("bytes")) is not int
                or value["bytes"] != len(original) or type(value.get("expires_ns")) is not int
                or value["expires_ns"] <= 0 or type(value.get("width")) is not int
                or type(value.get("height")) is not int or (value["width"], value["height"]) != (width, height)
                or value.get("media_type") != media_type):
            raise ReceiptError("image upload receipt differs from actual bytes, namespace or dimensions")
        return ImageUploadReceipt(namespace_id, digest, len(original), value["expires_ns"],
                                  self.endpoint_url, self.endpoint_pin, dict(value))

    def answer(self, branch: str, revision: int, operation_id: str,
               max_tokens: int, *, settings: Mapping[str, Any] | None = None,
               grammar_state: str | None = None, frame_key: FrameKey | None = None) -> GenerationResult:
        body = self._generation_body(branch, revision, operation_id, max_tokens, settings, grammar_state)
        return self._generation_mutation(operation_id, "/cow/text/answer", body, branch=branch,
                                         revision=revision, frame_key=frame_key)

    def ask(self, branch: str, revision: int, operation_id: str, content: str,
            max_tokens: int, *, settings: Mapping[str, Any] | None = None,
            grammar_state: str | None = None, frame_key: FrameKey | None = None) -> GenerationResult:
        body = self._generation_body(branch, revision, operation_id, max_tokens, settings, grammar_state)
        body["content"] = content
        return self._generation_mutation(operation_id, "/cow/text/ask", body, branch=branch,
                                         revision=revision, frame_key=frame_key)

    def continue_(self, branch: str, revision: int, operation_id: str, max_tokens: int, *,
                  settings: Mapping[str, Any] | None = None, grammar_state: str | None = None,
                  frame_key: FrameKey | None = None) -> GenerationResult:
        body = self._generation_body(branch, revision, operation_id, max_tokens, settings, grammar_state)
        return self._generation_mutation(operation_id, "/cow/text/resume", body, branch=branch,
                                         revision=revision, frame_key=frame_key)

    def append_user(self, branch: str, revision: int, operation_id: str, content: str,
                    max_tokens: int, *, settings: Mapping[str, Any] | None = None,
                    grammar_state: str | None = None, frame_key: FrameKey | None = None) -> GenerationResult:
        body = self._generation_body(branch, revision, operation_id, max_tokens, settings, grammar_state)
        body["content"] = content
        return self._generation_mutation(operation_id, "/cow/text/append-user", body, branch=branch,
                                         revision=revision, frame_key=frame_key)

    def fork(self, source_branch: str, snapshot: str, name: str, operation_id: str,
             *, frame_key: FrameKey | None = None) -> BranchHead:
        body = {"source_branch": source_branch, "snapshot": snapshot, "name": name,
                "operation_id": operation_id}
        existing = self.journal.read(operation_id)
        if existing is not None:
            binding = (COWSourceBinding.from_json(existing["source_binding"])
                       if existing.get("source_binding") else None)
            if (binding is None or binding.operation_id != operation_id
                    or binding.branch != name or binding.source_branch != source_branch
                    or binding.snapshot != snapshot or binding.endpoint_pin != self.endpoint_pin):
                raise OperationReuseError("journaled fork source binding differs from the request")
        else:
            source = self.head(source_branch)
            binding = COWSourceBinding(operation_id, name, source_branch, source.revision,
                                       snapshot, self.endpoint_pin)
        intent = self._intent(operation_id, "POST", "/cow/fork", body, name, None,
                              frame_key, binding)
        response = self._send_mutation(intent, stream=False)
        return BranchHead.parse(response.json_value)

    def read_completed_fork(self, operation_id: str) -> BranchHead:
        """Read a validated original fork locally; never send or infer it from head.

        A branch with the right current name alone cannot prove which operation
        created it. Pending/missing records stay unresolved until explicit
        read-only status recovery establishes the original durable receipt.
        """
        record = self.journal.read(operation_id)
        if record is None or record.get("state") != "complete":
            raise OperationIndeterminate("no complete fork receipt is retained")
        if record.get("method") != "POST" or record.get("path") != "/cow/fork":
            raise ReceiptError("operation is not a fork")
        if (record.get("endpoint_url") != self.endpoint_url
                or record.get("endpoint_pin") != self.endpoint_pin):
            raise OperationReuseError("completed fork belongs to another endpoint")
        receipt = self._receipt(record.get("receipt"), operation_id=operation_id)
        self._validate_receipt_against_record(receipt, record)
        return receipt.branch

    def retry_saved(self, source_operation: str, branch: str, revision: int,
                    operation_id: str, *, settings: Mapping[str, Any] | None = None,
                    frame_key: FrameKey | None = None) -> GenerationResult:
        # This is an explicit new COW retry operation. It never automatically retries a lost send.
        body: dict[str, Any] = {"from_operation": source_operation, "operation_id": operation_id,
                                "branch": branch, "revision": revision, "stream": True}
        if settings is not None:
            body["settings"] = dict(settings)
        return self._generation_mutation(operation_id, "/cow/text/retry", body,
                                         branch=branch, revision=revision, frame_key=frame_key)

    @staticmethod
    def _operation_id(operation_id: str | None) -> str:
        value = operation_id or ("bw-" + uuid.uuid4().hex)
        if not _OP_ID.fullmatch(value):
            raise ValueError("operation ID must start with a letter and contain at most 128 ASCII bytes using alphanumeric, _ or - characters")
        return value

    @staticmethod
    def _generation_body(branch: str, revision: int, operation_id: str, max_tokens: int,
                         settings: Mapping[str, Any] | None, grammar_state: str | None) -> dict[str, Any]:
        if type(revision) is not int or revision < 0:
            raise ValueError("revision must be a nonnegative integer")
        if type(max_tokens) is not int or max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        body: dict[str, Any] = {"branch": branch, "revision": revision,
                                "operation_id": operation_id, "max_tokens": max_tokens,
                                "stream": True}
        if settings is not None:
            body["settings"] = dict(settings)
        if grammar_state is not None:
            body["grammar_state"] = grammar_state
        return body

    def _intent(self, operation_id: str, method: str, path: str, body: Mapping[str, Any],
                branch: str | None, revision: int | None,
                frame_key: FrameKey | None,
                source_binding: COWSourceBinding | None = None) -> OperationIntent:
        if frame_key is not None:
            if frame_key.operation_id != operation_id or frame_key.branch != branch:
                raise ValueError("frame key is not bound to this operation and target branch")
        if source_binding is not None:
            if (source_binding.operation_id != operation_id
                    or source_binding.branch != branch
                    or source_binding.endpoint_pin != self.endpoint_pin):
                raise ValueError("source binding is not bound to this operation, branch, and endpoint")
        return OperationIntent(operation_id, method, path, _canonical(dict(body)), branch,
                               revision, frame_key, self.endpoint_pin, source_binding)

    def _mutate(self, operation_id: str, path: str, body: Mapping[str, Any], *,
                stream: bool, branch: str | None = None, revision: int | None = None,
                frame_key: FrameKey | None = None) -> _Response:
        intent = self._intent(operation_id, "POST", path, body, branch, revision, frame_key)
        return self._send_mutation(intent, stream=stream)

    def _send_mutation(self, intent: OperationIntent, *, stream: bool,
                       explicit_replay: bool = False) -> _Response:
        record, should_send = self.journal.begin(intent, self.endpoint_url)
        if not should_send:
            if record.get("state") == "complete":
                return _Response(json_value=record.get("receipt"), transport="client-journal")
            if not explicit_replay:
                raise OperationIndeterminate("existing request is unresolved; reconcile before explicit replay")
        try:
            response = self.transport.request(intent.method, intent.path, intent.body, stream=stream)
        except RequestRejected:
            # Keep exact intent: a later status lookup can establish whether the endpoint committed.
            raise
        except OperationIndeterminate:
            raise
        if stream:
            return self._accept_stream(response, record, intent)
        value = response.json_value
        receipt = self._validate_nonstream(intent, value)
        self.journal.complete(record, receipt)
        return response

    def _generation_mutation(self, operation_id: str, path: str, body: Mapping[str, Any], *,
                             branch: str, revision: int | None,
                             frame_key: FrameKey | None) -> GenerationResult:
        binding = None
        existing = self.journal.read(operation_id)
        if existing is not None and existing.get("source_binding") is not None:
            binding = COWSourceBinding.from_json(existing["source_binding"])
        if revision is not None:
            if existing is not None:
                if binding is None:
                    raise CowClientError("journaled generation intent lacks its source binding")
                if (binding.operation_id != operation_id or binding.branch != branch
                        or binding.source_branch != branch or binding.revision != revision
                        or binding.endpoint_pin != self.endpoint_pin):
                    raise OperationReuseError("journaled source binding differs from the requested continuation")
            else:
                source_head = self.head(branch)
                if source_head.revision != revision:
                    raise RequestRejected("branch revision changed before dispatch; read the head and decide explicitly")
                binding = COWSourceBinding(operation_id, branch, branch, revision,
                                           source_head.tip, self.endpoint_pin)
        intent = self._intent(operation_id, "POST", path, body, branch, revision,
                              frame_key, binding)
        record, should_send = self.journal.begin(intent, self.endpoint_url)
        if not should_send:
            if record.get("state") == "complete":
                return self._journal_generation(record)
            raise GenerationIndeterminate(operation_id, "existing request is unresolved; inspect operation status")
        try:
            response = self.transport.request("POST", path, intent.body, stream=True)
        except RequestRejected:
            raise
        except OperationIndeterminate as exc:
            raise GenerationIndeterminate(operation_id, str(exc)) from exc
        return self._accept_stream(response, record, intent)

    def reconcile_generation(self, operation_id: str) -> GenerationResult:
        """Explicitly recover exact output only after proof of durable commitment.

        This does not authorize a fresh generation. Unknown or in-flight work
        remains unresolved. Completed local answers require no network. Missing
        answers, including legacy receipt-only records, replay the original
        immutable request only after validating its durable server receipt.
        Normal workflow stepping still never resends uncertain work implicitly.
        """
        record = self.journal.read(operation_id)
        if record is None:
            raise OperationIndeterminate("no original generation intent is available")
        if (record.get("endpoint_url") != self.endpoint_url
                or record.get("endpoint_pin") != self.endpoint_pin):
            raise OperationReuseError("original generation belongs to another endpoint")
        if record.get("method") != "POST" or record.get("path") not in {
                "/cow/text/context", "/cow/text/prepare", "/cow/text/answer",
                "/cow/text/ask", "/cow/text/append-user", "/cow/text/resume",
                "/cow/text/retry", "/cow/text/generate"}:
            raise ReceiptError("operation is not a supported generation request")
        if record.get("state") == "complete" and "answer" in record:
            return self.read_completed_generation(operation_id)
        body = self.journal.decode_body(record)
        intent = OperationIntent(operation_id, record["method"], record["path"], body,
            record.get("branch"), record.get("revision"),
            FrameKey.from_json(record["frame_key"]) if record.get("frame_key") else None,
            record.get("endpoint_pin"),
            COWSourceBinding.from_json(record["source_binding"]) if record.get("source_binding") else None)
        data = json.loads(body)
        if (intent.path == "/cow/text/retry"
                and set(data) == {"from_operation", "operation_id", "branch", "revision", "stream"}
                and data["stream"] is True):
            # This exact API form is a read of an already committed answer,
            # not a generation admission. Recover only the recorded bytes/ID.
            source = self.operation(data["from_operation"])
            if not source.durable or source.receipt is None:
                raise OperationIndeterminate("saved retry source has no durable result")
            response = self.transport.request(intent.method, intent.path, intent.body, stream=True)
            return self._accept_stream(response, record, intent)
        observation = self.operation(operation_id)
        if not observation.durable:
            raise OperationIndeterminate("original generation has no proven durable result")
        self._validate_receipt_against_record(observation.receipt, record)
        if (record.get("state") == "complete"
                and _canonical(record.get("receipt")) != _canonical(dict(observation.receipt.raw))):
            raise ReceiptError("durable lookup differs from retained receipt")
        response = self.transport.request(intent.method, intent.path, intent.body, stream=True)
        completions = [event for event in response.events if event.get("event") == "complete"]
        if len(completions) != 1:
            raise ReceiptError("recovered output differs from proven durable receipt")
        replayed_receipt = self._receipt(
            completions[0].get("receipt"), operation_id=operation_id,
            expected_branch=record.get("branch"))
        self._validate_receipt_against_record(replayed_receipt, record)
        observed_raw = dict(observation.receipt.raw)
        replayed_raw = dict(replayed_receipt.raw)
        common_fields = observed_raw.keys() & replayed_raw.keys()
        if (replayed_receipt.branch != observation.receipt.branch
                or replayed_receipt.snapshot != observation.receipt.snapshot
                or any(observed_raw[field] != replayed_raw[field] for field in common_fields)):
            raise ReceiptError("recovered output differs from proven durable receipt")
        return self._accept_stream(response, record, intent)

    def replay_original(self, operation_id: str) -> GenerationResult | Mapping[str, Any]:
        record = self.journal.read(operation_id)
        if record is None:
            raise OperationIndeterminate("no original request is available")
        if record["state"] == "complete":
            if record.get("path")=="/cow/grammars":
                intent=OperationIntent(operation_id,record["method"],record["path"],
                    self.journal.decode_body(record),record.get("branch"),record.get("revision"),
                    None,record.get("endpoint_pin"))
                if record.get("endpoint_url")!=self.endpoint_url or intent.endpoint_pin!=self.endpoint_pin:
                    raise OperationReuseError("original registration belongs to another endpoint")
                return self._validate_nonstream(intent,record.get("receipt"))
            return self._journal_generation(record)
        body = self.journal.decode_body(record)
        intent = OperationIntent(operation_id, record["method"], record["path"], body,
            record.get("branch"), record.get("revision"),
            FrameKey.from_json(record["frame_key"]) if record.get("frame_key") else None,
            record.get("endpoint_pin"),
            COWSourceBinding.from_json(record["source_binding"]) if record.get("source_binding") else None)
        if record.get("endpoint_url") != self.endpoint_url or intent.endpoint_pin != self.endpoint_pin:
            raise OperationReuseError("original request is bound to a different endpoint")
        response = self.transport.request(intent.method, intent.path, intent.body,
                                          stream="text/" in intent.path)
        if "text/" in intent.path:
            return self._accept_stream(response, record, intent)
        receipt = self._validate_nonstream(intent, response.json_value)
        self.journal.complete(record, receipt)
        return response.json_value

    @staticmethod
    def _check_answer_binding(path: str, answer: Any, snapshot: str) -> None:
        if type(answer) is not dict:
            raise ReceiptError("retained generation answer is not an object")
        if path in {"/cow/text/answer", "/cow/text/ask", "/cow/text/resume",
                    "/cow/text/append-user", "/cow/text/retry"} and type(answer.get("text")) is not str:
            raise ReceiptError("retained generation answer lacks exact text")
        if answer.get("snapshot") is not None and answer["snapshot"] != snapshot:
            raise ReceiptError("retained answer snapshot differs from durable receipt")
        # Nested thinking completion remains the responsibility of the existing
        # completed_thinking_text guard. Retaining a partial never makes it legal
        # control output, and no provisional stream is persisted as a final.
        _canonical(answer)

    def _journal_generation(self, record: Mapping[str, Any], *, exact_answer: bool = False) -> GenerationResult:
        if (record.get("endpoint_url") != self.endpoint_url
                or record.get("endpoint_pin") != self.endpoint_pin):
            raise OperationReuseError("completed request belongs to another endpoint")
        replay = record.get("replay_source")
        receipt_op = replay.get("operation_id") if isinstance(replay, dict) else record["operation_id"]
        receipt = self._receipt(record.get("receipt"), operation_id=receipt_op)
        self._validate_receipt_against_record(receipt, record)
        binding = (COWSourceBinding.from_json(record["source_binding"])
                   if record.get("source_binding") else None)
        if record.get("revision") is not None:
            if (binding is None or binding.operation_id != record["operation_id"]
                    or binding.branch != record.get("branch")
                    or binding.source_branch != record.get("branch")
                    or binding.revision != record["revision"]
                    or binding.endpoint_pin != self.endpoint_pin):
                raise ReceiptError("retained source binding has a different operation owner")
        if "answer" in record:
            answer = json.loads(_canonical(record["answer"]))
            self._check_answer_binding(record["path"], answer, receipt.snapshot)
        elif exact_answer:
            raise ReceiptError("completed receipt has no retained generation answer; do not regenerate")
        else:
            # Historical receipt-only records stay available to metadata callers.
            # A model/control consumer must use read_completed_generation instead.
            answer = {}
        return GenerationResult(record["operation_id"], receipt, (), answer, "client-journal", binding)

    def read_completed_generation(self, operation_id: str) -> GenerationResult:
        """Read exact committed output locally; never send, replay or synthesize.

        An absent/pending record stays indeterminate. Legacy receipt-only records
        cannot satisfy this stronger contract. Receipt/status lookup remains a
        separate observation and must not manufacture missing model output.
        """
        record = self.journal.read(operation_id)
        if record is None or record.get("state") != "complete":
            raise OperationIndeterminate("no complete generation output is retained")
        if "/text/" not in record.get("path", ""):
            raise ReceiptError("operation is not a generation")
        return self._journal_generation(record, exact_answer=True)

    def _accept_stream(self, response: _Response, record: Mapping[str, Any],
                       intent: OperationIntent) -> GenerationResult:
        complete = None
        for event in response.events:
            if complete is not None:
                raise ReceiptError("COW emitted an event after completion")
            kind = event["event"]
            if kind == "error":
                raise GenerationIndeterminate(intent.operation_id, "COW stream error without completion proof: " + str(event.get("error", "unknown error")))
            if kind == "failure":
                raise GenerationIndeterminate(intent.operation_id, "COW stream failure without completion proof: " + str(event.get("error", "unknown failure")))
            if kind == "complete":
                complete = event
        if complete is None:
            raise GenerationIndeterminate(intent.operation_id, "COW stream ended without a durable complete receipt")
        answer = complete.get("answer")
        if not isinstance(answer, dict):
            raise ReceiptError("complete event lacks an answer object")
        if "text" in answer and not isinstance(answer.get("text"), str):
            raise ReceiptError("complete answer text is not a string")
        if intent.path in {"/cow/text/answer", "/cow/text/ask", "/cow/text/resume",
                           "/cow/text/append-user", "/cow/text/retry"} and not isinstance(
                               answer.get("text"), str):
            raise ReceiptError("generation completion lacks exact answer text")
        replay_source = None
        retry_body = json.loads(intent.body) if intent.path == "/cow/text/retry" else None
        if retry_body is not None and complete.get("replayed") is True:
            # A saved-answer read returns the original immutable receipt. It
            # does not move the requested branch, even if it advanced since.
            source_op = retry_body["from_operation"]
            observation = self.operation(source_op)
            if not observation.durable or observation.receipt is None:
                raise ReceiptError("saved-answer replay lacks original durable proof")
            original = observation.receipt
            receipt = self._receipt(complete.get("receipt"), operation_id=source_op,
                expected_branch=original.branch.name, expected_revision=original.branch.revision,
                expected_snapshot=original.snapshot)
            # Legacy canonical presentations can omit optional checkpoint
            # metadata. Bind the whole branch and snapshot, and reject every
            # conflicting identity field carried by both receipt forms.
            if (receipt.branch != original.branch or receipt.snapshot != original.snapshot
                    or any(receipt.raw[k] != original.raw[k]
                           for k in receipt.raw.keys() & original.raw.keys())):
                raise ReceiptError("replay differs from the original durable receipt")
            replay_source = dict(operation_id=source_op, receipt=dict(original.raw))
        else:
            if retry_body is not None and "settings" not in retry_body:
                raise ReceiptError("unchanged retry must return its original saved answer")
            receipt = self._receipt(complete.get("receipt"), operation_id=intent.operation_id,
                                    expected_branch=intent.branch,
                                    expected_revision=(None if intent.revision is None else intent.revision + 1))
        if answer.get("snapshot") is not None and answer["snapshot"] != receipt.snapshot:
            raise ReceiptError("answer snapshot differs from durable receipt")
        if "text" in answer and isinstance(answer["text"], str):
            streamed = "".join(response.provisional_text)
            # Original-request replay can return only its checked completion,
            # without replaying provisional callbacks. Compare any observed
            # fragments; the receipt-bound complete answer is authoritative.
            if response.transport == "http" and response.provisional_text and streamed != answer["text"]:
                raise ReceiptError("provisional stream text differs from committed answer text")
        self._check_answer_binding(intent.path, answer, receipt.snapshot)
        self.journal.complete(record, receipt.raw, answer=answer, replay_source=replay_source)
        return GenerationResult(intent.operation_id, receipt,
                                response.provisional_text, answer, response.transport,
                                intent.source_binding)

    def _receipt(self, value: Any, *, operation_id: str,
                 expected_branch: str | None = None,
                 expected_revision: int | None = None,
                 expected_snapshot: str | None = None) -> GenerationReceipt:
        if not isinstance(value, dict):
            raise ReceiptError("response lacks a structured durable receipt")
        receipt_op = value.get("operation_id")
        if receipt_op is not None and receipt_op != operation_id:
            raise ReceiptError("durable receipt operation ID does not match request")
        branch = BranchHead.parse(value.get("branch"))
        snapshot = value.get("snapshot")
        if not isinstance(snapshot, str) or not _HEX64.fullmatch(snapshot) or branch.tip != snapshot:
            raise ReceiptError("receipt snapshot does not match committed branch tip")
        if expected_branch is not None and branch.name != expected_branch:
            raise ReceiptError("receipt belongs to a different branch")
        if expected_revision is not None and branch.revision != expected_revision:
            raise ReceiptError("receipt branch revision does not match expected transition")
        if expected_snapshot is not None and snapshot != expected_snapshot:
            raise ReceiptError("receipt snapshot differs from requested snapshot")
        return GenerationReceipt(operation_id, branch, snapshot, dict(value))

    def inspect_completion(self,job_id,*,model_contract_id):
        if type(job_id) is not str or not _OP_ID.fullmatch(job_id):raise ValueError('Invalid original native job ID')
        value=self.transport.request('GET','/cow/training/jobs/'+job_id+'/completion-recovery').json_value
        return validate_completion_inspection(value,job_id=job_id,model_contract_id=model_contract_id)

    def _adopt_original_completion(self,payload,operation_id):
        """Only this metadata transaction may repeat its exact original POST."""
        if type(payload) is not dict or 'operation_id' in payload:raise ValueError('Completion payload cannot replace the explicit original operation ID')
        operation_id=self._operation_id(operation_id)
        body=_completion_approval(dict(payload,operation_id=operation_id))
        intent=self._intent(operation_id,'POST',_COMPLETION_ROUTE,body,None,None,None)
        record=self.journal.read(operation_id)
        if record is not None:
            if (record.get('endpoint_url')!=self.endpoint_url or record.get('endpoint_pin')!=self.endpoint_pin
                    or record.get('method')!='POST' or record.get('path')!=_COMPLETION_ROUTE
                    or self.journal.decode_body(record)!=intent.body or record.get('branch') is not None
                    or record.get('revision') is not None or record.get('frame_key') is not None
                    or record.get('source_binding') is not None):
                raise OperationReuseError('Original completion approval belongs to another request or endpoint')
            if record.get('state')=='complete':return dict(self._validate_nonstream(intent,record.get('receipt')))
            if record.get('state')!='pending':raise ReceiptError('Invalid original completion approval journal state')
        else:
            record,_=self.journal.begin(intent,self.endpoint_url)
        try:value=self.transport.request('POST',_COMPLETION_ROUTE,intent.body,stream=False).json_value
        except OperationIndeterminate:
            # GET can acknowledge only a fully committed adoption. A pending
            # approval remains pending; the next explicit invocation may resume
            # this same metadata POST, never a native job or changed request.
            try:value=self.transport.request('GET','/cow/training/operations/'+operation_id).json_value
            except CowClientError:
                raise OperationIndeterminate('Original completion adoption is unresolved; hold and reuse this exact approval operation') from None
        receipt=self._validate_nonstream(intent,value)
        self.journal.complete(record,receipt)
        return dict(receipt)

    def completion_learning_status(self,run_id,*,model_contract_id):
        value=self.training_read('learning-runs',run_id)
        if (type(value.get('schema')) is not int or value['schema']!=1
                or value.get('model_contract_id')!=model_contract_id
                or type(value.get('revision')) is not int or value['revision']<0
                or type(value.get('phase')) is not str or type(value.get('available_actions')) is not list
                or value.get('promoted') is not False):
            raise ReceiptError('Completion recovery learning status is not bound to this run/model')
        return value

    def reconcile_completion(self,run_id,operation_id,expected_revision,*,model_contract_id):
        """Explicit adopted-completion metadata only; never generic training retry."""
        operation_id=self._operation_id(operation_id)
        if type(run_id) is not str or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',run_id):raise ValueError('Invalid original learning run ID')
        if type(expected_revision) is not int or expected_revision<0:raise ValueError('Explicit nonnegative original run revision is required')
        body=dict(operation_id=operation_id,run_id=run_id,expected_revision=expected_revision,action='reconcile')
        path='/cow/training/learning-steps'
        intent=self._intent(operation_id,'POST',path,body,None,None,None)
        record=self.journal.read(operation_id)
        if record is not None:
            if (record.get('endpoint_url')!=self.endpoint_url or record.get('endpoint_pin')!=self.endpoint_pin
                    or record.get('method')!='POST' or record.get('path')!=path
                    or self.journal.decode_body(record)!=intent.body or record.get('branch') is not None
                    or record.get('revision') is not None or record.get('frame_key') is not None
                    or record.get('source_binding') is not None):
                raise OperationReuseError('Original completion reconciliation binds another request or endpoint')
            if record.get('state')=='complete':return dict(self._validate_nonstream(intent,record.get('receipt')))
            if record.get('state')!='pending':raise ReceiptError('Invalid completion reconciliation journal state')
            # The original acknowledgment may have advanced the phase already.
            # Validate it before looking at the current phase; never mint a new step.
            try:value=self.transport.request('GET','/cow/training/operations/'+operation_id).json_value
            except CowClientError:pass
            else:
                receipt=self._validate_nonstream(intent,value);self.journal.complete(record,receipt);return dict(receipt)
        status=self.completion_learning_status(run_id,model_contract_id=model_contract_id)
        if (status['phase']!='needs_operator' or status['revision']!=expected_revision
                or status.get('operator_reason_code')!='native_job_unresolved'
                or dict(action='reconcile',required_fields=[]) not in status['available_actions']):
            raise ReceiptError('HOLD: run is not the exact adopted-completion reconciliation boundary')
        if record is None:record,_=self.journal.begin(intent,self.endpoint_url)
        try:value=self.transport.request('POST',path,intent.body,stream=False).json_value
        except OperationIndeterminate:
            try:value=self.transport.request('GET','/cow/training/operations/'+operation_id).json_value
            except CowClientError:
                raise OperationIndeterminate('Original completion reconciliation is unresolved; retain this exact step ID and request') from None
        receipt=self._validate_nonstream(intent,value);self.journal.complete(record,receipt);return dict(receipt)

    def training_submit(self,kind,payload,operation_id):
        if kind=='job-reconciliations':return self._adopt_original_completion(payload,operation_id)
        if kind not in ('lessons','jobs','exports','learning-runs','learning-steps'):raise ValueError('Unknown training operation')
        operation_id=self._operation_id(operation_id)
        path='/cow/training/'+kind;body=dict(payload,operation_id=operation_id)
        try:return self._mutate(operation_id,path,body,stream=False).json_value
        except OperationIndeterminate:
            # Reconcile by reading the original acceptance. Never send another
            # training mutation to resolve a lost response.
            try:value=self.transport.request('GET','/cow/training/operations/'+operation_id).json_value
            except CowClientError:raise OperationIndeterminate('Training acceptance is unknown; reuse this operation ID for status reconciliation') from None
            intent=self._intent(operation_id,'POST',path,body,None,None,None)
            receipt=self._validate_nonstream(intent,value)
            self.journal.complete(self.journal.read(operation_id),receipt)
            return receipt

    def training_read(self,resource,identity=None,*,round_index=None):
        if resource not in ('lessons','jobs','operations','skills','optimizer-profiles','exports','learning-policies','learning-runs'):raise ValueError('Unknown training resource')
        if identity is not None and (type(identity) is not str or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',identity)):
            raise ValueError('Invalid training resource identity')
        path='/cow/training/'+resource+('' if identity is None else '/'+identity)
        if round_index is not None:
            if resource!='learning-runs' or identity is None or type(round_index) is not int or not 1<=round_index<=100000:
                raise ValueError('Learning round read requires run identity and bounded positive index')
            path+='/rounds/'+str(round_index)
        value=self.transport.request('GET',path).json_value
        if type(value) is not dict or value.get('schema')!=1:raise ReceiptError('Invalid training resource')
        if resource=='learning-runs' and identity is not None and (value.get('run_id')!=identity or value.get('promoted') is not False):
            raise ReceiptError('Learning run identity or promotion status is invalid')
        if round_index is not None and value.get('round')!=round_index:raise ReceiptError('Learning round identity differs')
        if resource=='jobs' and (value.get('job_id')!=identity or value.get('promoted') is not False):
            raise ReceiptError('Training job identity or promotion status is invalid')
        return value

    def _validate_nonstream(self, intent: OperationIntent, value: Any) -> Mapping[str, Any]:
        if intent.path==_COMPLETION_ROUTE:
            body=_completion_approval(json.loads(intent.body))
            binding=hashlib.sha256(_canonical([intent.path,body])).hexdigest()
            expected=dict(schema=1,operation_id=intent.operation_id,request_sha256=binding,
                job_id=body['job_id'],candidate_sha256=body['expected_candidate_sha256'],adopted=True,promoted=False)
            if (type(value) is not dict or value!=expected or type(value.get('schema')) is not int
                    or value.get('adopted') is not True or value.get('promoted') is not False):
                raise ReceiptError('Completion adoption acknowledgment does not bind the committed original owner approval')
            return dict(value)
        if intent.path in ('/cow/training/learning-runs','/cow/training/learning-steps'):
            body=json.loads(intent.body);fields={'schema','operation_id','request_sha256','run_id'}
            if intent.path.endswith('/learning-steps'):fields.add('step_id')
            binding=hashlib.sha256(_canonical([intent.path,body])).hexdigest()
            if (type(value) is not dict or set(value)!=fields or type(value['schema']) is not int or value['schema']!=1
                    or value['operation_id']!=intent.operation_id or value['request_sha256']!=binding
                    or value['run_id']!=(body['run_id'] if 'step_id' in fields else intent.operation_id)
                    or ('step_id' in fields and value['step_id']!=intent.operation_id)):
                raise ReceiptError('Learning acceptance does not bind the original request')
            return dict(value)
        if intent.path=='/cow/training/exports':
            body=json.loads(intent.body)
            fields={'schema','operation_id','request_sha256','export_id','name','model_sha256','file','weights_published'}
            binding=hashlib.sha256(_canonical([intent.path,body])).hexdigest()
            if (type(value) is not dict or set(value)!=fields or type(value['schema']) is not int or value['schema']!=1
                    or value['operation_id']!=intent.operation_id or value['request_sha256']!=binding
                    or type(value['export_id']) is not str or not _HEX64.fullmatch(value['export_id'])
                    or value['name']!=body['name'] or value['file']!=body['name']+'.gguf'
                    or value['model_sha256']!=body['expected_sha256'] or value['weights_published'] is not False):
                raise ReceiptError('Model preservation acceptance does not bind the original request')
            return dict(value)
        if intent.path in ('/cow/training/lessons','/cow/training/jobs'):
            body=json.loads(intent.body)
            field='lesson_id' if intent.path.endswith('/lessons') else 'job_id'
            binding=hashlib.sha256(_canonical([intent.path,body])).hexdigest()
            if (type(value) is not dict or set(value)!={'schema','operation_id','request_sha256',field}
                    or type(value['schema']) is not int or value['schema']!=1
                    or value['operation_id']!=intent.operation_id or value['request_sha256']!=binding):
                raise ReceiptError('Training acceptance does not bind the original request')
            expected=hashlib.sha256(_canonical(body['lesson'])).hexdigest() if field=='lesson_id' else intent.operation_id
            if value[field]!=expected:raise ReceiptError('Training acceptance has a different identity')
            return dict(value)
        if intent.path == "/cow/grammars":
            body=json.loads(intent.body)
            definitions={key:item for key,item in body.items() if key!="operation_id"}
            required={"schema","group_id","states","engine_id","spec_sha256","tokenizer_sha256",
                      "llguidance_version","operation_id","definition_sha256"}
            digest=hashlib.sha256(_canonical(definitions)).hexdigest()
            if (type(value) is not dict or set(value)!=required
                    or type(value.get("schema")) is not int or value["schema"]!=1
                    or value["operation_id"]!=intent.operation_id
                    or value["definition_sha256"]!=digest
                    or any(type(value.get(key)) is not str or not _HEX64.fullmatch(value[key])
                           for key in ("group_id","engine_id","spec_sha256","tokenizer_sha256","definition_sha256"))
                    or type(value["llguidance_version"]) is not str or not value["llguidance_version"]):
                raise ReceiptError("grammar receipt does not bind original definitions and operation")
            expected={name:"g"+value["group_id"]+"_s"+str(i)
                      for i,name in enumerate(sorted(definitions["states"]))}
            if value["states"]!=expected:
                raise ReceiptError("grammar receipt state mapping differs from admitted definitions")
            return dict(value)
        if intent.path == "/cow/namespace":
            if not isinstance(value, dict) or not isinstance(value.get("namespace_id"), str):
                raise ReceiptError("namespace response lacks namespace_id")
            return value
        if intent.path == "/cow/fork":
            head = BranchHead.parse(value)
            if intent.branch is not None and head.name != intent.branch:
                raise ReceiptError("fork receipt names another branch")
            body = json.loads(intent.body.decode("utf-8"))
            if head.tip != body.get("snapshot") or head.revision != 0:
                raise ReceiptError("fork receipt does not bind the requested snapshot")
            raw = dict(value)
            raw.setdefault("branch", value if "branch" not in value else value["branch"])
            raw.setdefault("snapshot", head.tip)
            raw.setdefault("operation_id", intent.operation_id)
            return raw
        if intent.path == "/cow/publication/retry":
            receipt = value.get("receipt") if isinstance(value, dict) else None
            return self._receipt(receipt, operation_id=intent.operation_id).raw
        raise ReceiptError(f"no receipt validator for {intent.path}")

    def _validate_receipt_against_record(self, receipt: GenerationReceipt | None,
                                         record: Mapping[str, Any]) -> None:
        if receipt is None:
            raise ReceiptError("durable operation status lacks a receipt")
        branch = record.get("branch")
        revision = record.get("revision")
        replay = record.get("replay_source")
        if replay is not None:
            body = json.loads(self.journal.decode_body(record))
            if (record.get("path") != "/cow/text/retry" or type(replay) is not dict
                    or set(replay) != {"operation_id", "receipt"}
                    or replay["operation_id"] != body.get("from_operation")):
                raise ReceiptError("saved-answer proof differs from original retry intent")
            original = self._receipt(replay["receipt"], operation_id=replay["operation_id"])
            self._receipt(receipt.raw, operation_id=replay["operation_id"],
                expected_branch=original.branch.name, expected_revision=original.branch.revision,
                expected_snapshot=original.snapshot)
            if (receipt.branch != original.branch or receipt.snapshot != original.snapshot
                    or any(receipt.raw[k] != original.raw[k]
                           for k in receipt.raw.keys() & original.raw.keys())):
                raise ReceiptError("retained replay differs from original durable receipt")
            return
        if record.get("path") == "/cow/fork":
            body = json.loads(self.journal.decode_body(record))
            binding = COWSourceBinding.from_json(record.get("source_binding"))
            if (set(body) != {"source_branch", "snapshot", "name", "operation_id"}
                    or body["operation_id"] != record["operation_id"]
                    or body["name"] != branch or binding.operation_id != record["operation_id"]
                    or binding.branch != branch or binding.source_branch != body["source_branch"]
                    or binding.snapshot != body["snapshot"] or binding.endpoint_pin != self.endpoint_pin):
                raise ReceiptError("fork source binding differs from original intent")
            self._receipt(receipt.raw, operation_id=record["operation_id"],
                          expected_branch=branch, expected_revision=0,
                          expected_snapshot=body["snapshot"])
            if record.get("frame_key") is not None:
                key = FrameKey.from_json(record["frame_key"])
                if key.operation_id != record["operation_id"] or key.branch != branch:
                    raise ReceiptError("fork frame owner differs from original intent")
            return
        expected_revision = revision + 1 if type(revision) is int and "/text/" in record.get("path", "") else None
        self._receipt(receipt.raw, operation_id=record["operation_id"],
                      expected_branch=branch, expected_revision=expected_revision)


__all__ = [
    "BranchHead", "COWSourceBinding", "CliTransport", "CowClient", "CowClientError", "FrameKey",
    "GenerationReceipt", "GenerationResult", "HistoryView", "HTTPTransport",
    "OperationIndeterminate", "OperationIntent", "OperationJournal",
    "OperationObservation", "OperationReuseError", "ReceiptError", "RequestRejected",
    "ServiceObservation", "SlotReturns",
]
