"""Small durable user-conversation CLI backed by Context COW history."""
from __future__ import annotations
import fcntl, hashlib, json, os, re, stat, sys, tempfile, time, uuid
from contextlib import contextmanager
from pathlib import Path
from .cow_client import CowClient, HTTPTransport, OperationJournal, OperationIndeterminate

_BRANCH = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,127}\Z")
_OPERATION = _BRANCH
_MAX_MESSAGE_BYTES = 262144
_MAX_STATE_BYTES = 1024 * 1024
_STREAMED_TEXT = []

def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")

def _state_dir(path, *, create=False):
    path = Path(path).absolute()
    if path.is_symlink(): raise ValueError("chat state must be a real owned directory")
    if create and not path.exists(): path.mkdir(mode=0o700)
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
        raise ValueError("chat state directory must be owned by this user with mode 0700")
    return path

@contextmanager
def _locked(state):
    state = _state_dir(state)
    fd = os.open(state / ".chat.lock", os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "r+b") as lock:
        info = os.fstat(lock.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600:
            raise ValueError("invalid chat state lock")
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        yield state

def _read(state):
    fd = os.open(Path(state) / "chat.json", os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600:
            raise ValueError("chat state must be a private owned regular file")
        raw = stream.read(_MAX_STATE_BYTES + 1)
    if len(raw) > _MAX_STATE_BYTES: raise ValueError("chat state is too large")
    envelope = json.loads(raw)
    if type(envelope) is not dict or set(envelope) != {"chat", "sha256"} or envelope["sha256"] != hashlib.sha256(_canonical(envelope["chat"])).hexdigest():
        raise ValueError("chat state checksum is invalid")
    chat = envelope["chat"]
    if type(chat) is not dict or chat.get("schema") != 1 or not isinstance(chat.get("chat_id"), str) or not _BRANCH.fullmatch(chat.get("branch", "")) or type(chat.get("turn_count")) is not int or chat["turn_count"] < 0:
        raise ValueError("chat state has an invalid schema")
    return chat

def _write(state, chat):
    state = _state_dir(state)
    path = state / "chat.json"
    raw = _canonical({"chat": chat, "sha256": hashlib.sha256(_canonical(chat)).hexdigest()}) + b"\n"
    if len(raw) > _MAX_STATE_BYTES: raise ValueError("chat state is too large")
    fd, name = tempfile.mkstemp(prefix=".chat-", dir=state); temp = Path(name)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        os.replace(temp, path)
        dfd = os.open(state, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try: os.fsync(dfd)
        finally: os.close(dfd)
    finally:
        if temp.exists(): temp.unlink()

@contextmanager
def _queue_locked(state):
    state = _state_dir(state)
    fd = os.open(state / ".queue.lock", os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "r+b") as lock:
        info = os.fstat(lock.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600:
            raise ValueError("invalid chat queue lock")
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        yield state

def _queue_read(state):
    path = Path(state) / "chat-queue.json"
    try: fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    except FileNotFoundError: return []
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600:
            raise ValueError("chat queue must be a private owned regular file")
        raw = stream.read(_MAX_STATE_BYTES + 1)
    if len(raw) > _MAX_STATE_BYTES: raise ValueError("chat queue is too large")
    envelope = json.loads(raw)
    rows = envelope.get("queue") if isinstance(envelope,dict) else None
    if (not isinstance(envelope,dict) or set(envelope) != {"queue", "sha256"} or type(rows) is not list
            or envelope["sha256"] != hashlib.sha256(_canonical(rows)).hexdigest()):
        raise ValueError("chat queue checksum or schema is invalid")
    for row in rows:
        if (type(row) is not dict or set(row) != {"operation_id", "message", "max_tokens"}
                or not _BRANCH.fullmatch(row.get("operation_id", ""))
                or type(row.get("message")) is not str
                or len(row["message"].encode("utf-8")) > _MAX_MESSAGE_BYTES
                or type(row.get("max_tokens")) is not int or not 1 <= row["max_tokens"] <= 1_000_000):
            raise ValueError("chat queue contains an invalid item")
    return rows

def _queue_write(state, rows):
    state = _state_dir(state)
    raw = _canonical({"queue": rows, "sha256": hashlib.sha256(_canonical(rows)).hexdigest()}) + b"\n"
    if len(raw) > _MAX_STATE_BYTES: raise ValueError("chat queue is too large")
    fd, name = tempfile.mkstemp(prefix=".queue-", dir=state); temp = Path(name)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        os.replace(temp, state / "chat-queue.json")
        dfd = os.open(state, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try: os.fsync(dfd)
        finally: os.close(dfd)
    finally:
        if temp.exists(): temp.unlink()

def _pending_for_message(state, chat, message, operation_id, max_tokens, *, queue_item_ids=()):
    if chat["turn_count"] == 0:
        prep = "bwchat-prep-" + hashlib.sha256((chat["chat_id"] + operation_id).encode()).hexdigest()[:40]
        pending = {"kind": "first_prepare", "operation_id": prep, "answer_operation_id": operation_id,
                   "message": message, "max_tokens": max_tokens}
    else:
        head = chat.get("head")
        if not isinstance(head, dict): raise ValueError("chat has no committed branch head")
        controller = _current_controller(_client(state, chat), chat)
        if controller != "stopped": raise OperationIndeterminate("queued user message is waiting for the assistant turn to finish")
        pending = {"kind": "append_user", "operation_id": operation_id, "revision": head["revision"],
                   "message": message, "max_tokens": max_tokens}
    if queue_item_ids:
        pending["queue_item_ids"] = list(queue_item_ids)
    return pending

def _queue_batch(chat, rows):
    if not rows: raise ValueError("cannot form an empty queued turn")
    item_ids = [row["operation_id"] for row in rows]
    message = "\n\n".join(row["message"] for row in rows)
    if len(message.encode("utf-8")) > _MAX_MESSAGE_BYTES:
        raise ValueError("combined queued turn exceeds 256 KiB")
    max_tokens = rows[-1]["max_tokens"]
    identity = {"chat_id": chat["chat_id"], "branch": chat["branch"],
                "items": [{"id": row["operation_id"], "message": row["message"]} for row in rows],
                "max_tokens": max_tokens}
    operation_id = "bwchat-batch-" + hashlib.sha256(_canonical(identity)).hexdigest()[:40]
    return {"operation_id": operation_id, "message": message, "max_tokens": max_tokens,
            "queue_item_ids": item_ids}

def _discard_completed_queue(state, chat):
    item_ids = chat.get("completed_queue_item_ids")
    if item_ids is None: return chat
    if (type(item_ids) is not list or not item_ids
            or any(type(item) is not str or not _BRANCH.fullmatch(item) for item in item_ids)
            or len(set(item_ids)) != len(item_ids)):
        raise ValueError("completed queued-turn receipt is invalid")
    with _queue_locked(state):
        rows = _queue_read(state)
        row_ids = [row["operation_id"] for row in rows]
        if row_ids[:len(item_ids)] == item_ids:
            _queue_write(state, rows[len(item_ids):])
        elif any(item in row_ids for item in item_ids):
            raise OperationIndeterminate("queued-turn receipt no longer matches the local queue")
        # If none remain, the atomic queue replacement already happened before a crash.
    chat.pop("completed_queue_item_ids")
    _write(state, chat)
    return chat

def _drain_queue_locked(state, chat):
    if chat.get("pending") is not None or chat.get("status") != "ready": return
    chat = _discard_completed_queue(state, chat)
    while True:
        with _queue_locked(state): rows = _queue_read(state)
        if not rows: return
        batch = _queue_batch(chat, rows)
        try:
            pending = _pending_for_message(
                state, chat, batch["message"], batch["operation_id"], batch["max_tokens"],
                queue_item_ids=batch["queue_item_ids"])
        except OperationIndeterminate:
            return
        chat["pending"] = pending; chat["status"] = "pending"; _write(state, chat)
        _STREAMED_TEXT.clear()
        text = _dispatch(state, chat)
        if text is not None: _print_committed(text)
        chat = _read(state)
        if chat.get("status") != "ready" or chat.get("pending") is not None: return
        chat = _discard_completed_queue(state, chat)

def queue_command(state_path, message, *, message_file=None, operation_id=None, max_tokens=4096):
    message = _message(message, message_file)
    if type(max_tokens) is not int or not 1 <= max_tokens <= 1_000_000: raise ValueError("max tokens must be 1 through 1,000,000")
    state = _state_dir(state_path); op = _op(operation_id)
    with _queue_locked(state):
        rows = _queue_read(state)
        if any(row["operation_id"] == op for row in rows): raise ValueError("operation ID is already queued")
        combined = "\n\n".join([row["message"] for row in rows] + [message])
        if len(combined.encode("utf-8")) > _MAX_MESSAGE_BYTES:
            raise ValueError("combined queued turn exceeds 256 KiB")
        rows.append({"operation_id": op, "message": message, "max_tokens": max_tokens})
        _queue_write(state, rows); position = len(rows)
    print(json.dumps({"status": "queued", "operation_id": op, "position": position}, sort_keys=True), file=sys.stderr, flush=True)
    # Queue contents are durable before this process waits behind the active request.
    with _locked(state):
        chat = _read(state); _drain_queue_locked(state, chat)
    return 0

def stop_add_command(state_path, message, *, message_file=None, operation_id=None, max_tokens=4096):
    extra = _message(message, message_file)
    if type(max_tokens) is not int or not 1 <= max_tokens <= 1_000_000: raise ValueError("max tokens must be 1 through 1,000,000")
    state = _state_dir(state_path); observed = _read(state); old = observed.get("pending")
    if not isinstance(old,dict) or old.get("kind") not in ("first_answer","append_user"):
        raise ValueError("stop-add is available while a new user-turn answer is running; continue requests must finish first")
    old_operation=old["operation_id"]; client=_client(state,observed)
    client.cancel_generation(old_operation)
    deadline=time.monotonic()+60
    outcome=None
    while time.monotonic()<deadline:
        observation=client.operation(old_operation)
        if observation.durable:
            outcome="durable";break
        if observation.state=="cancelled":
            outcome="cancelled";break
        if observation.state=="failed":
            raise OperationIndeterminate("the request failed instead of cancelling; inspect its original operation")
        time.sleep(.05)
    if outcome is None: raise OperationIndeterminate("COW has not confirmed cancellation or durable completion")
    with _locked(state):
        chat=_read(state);current=chat.get("pending")
        if current is None:
            if outcome!="durable": raise OperationIndeterminate("chat state changed while stopping the request")
        elif current.get("operation_id")!=old_operation:
            raise OperationIndeterminate("a different chat operation replaced the request being stopped")
        if outcome=="durable":
            if current is not None:
                completed=client.reconcile_generation(old_operation)
                _complete(state,chat,completed,user=True)
                chat=_read(state)
            combined=extra
        else:
            live=client.head(chat["branch"]);saved=chat.get("head")
            if saved is not None and (live.revision!=saved["revision"] or live.tip!=saved["tip"]):
                raise OperationIndeterminate("branch moved during cancellation; inspect history before amending")
            original=old.get("message")
            if type(original) is not str:
                raise OperationIndeterminate("original user text is unavailable; refusing to replace it")
            combined=original+"\n\nAdditional context before answering:\n"+extra
            if old["kind"]=="first_answer":
                suffix="-amend-"+uuid.uuid4().hex[:12]
                chat["branch"]=chat["branch"][:128-len(suffix)]+suffix
                chat["head"]=None
        op=_op(operation_id)
        pending=_pending_for_message(
            state,chat,combined,op,max_tokens,
            queue_item_ids=old.get("queue_item_ids", ()) if outcome=="cancelled" else ())
        chat["status"]="pending";chat["pending"]=pending;_write(state,chat)
        _STREAMED_TEXT.clear()
        _print_committed(_dispatch(state,chat))
        return 0

def drain_command(state_path):
    state = _state_dir(state_path)
    with _locked(state):
        chat = _read(state); _drain_queue_locked(state, chat)
        with _queue_locked(state): remaining = len(_queue_read(state))
        print(json.dumps({"status": "drained" if not remaining else "waiting_for_turn",
                          "queued": remaining}, sort_keys=True))
    return 0

def _connection(path):
    raw = Path(path).read_bytes()
    if len(raw) > 65536: raise ValueError("connection profile is too large")
    value = json.loads(raw)
    keys = {"endpoint_url", "endpoint_pin", "model_contract_id", "execution_profile_id", "eos_tokens"}
    if type(value) is not dict or set(value) != keys: raise ValueError("connection needs endpoint/profile identities and EOS IDs")
    if any(type(value[k]) is not str or not value[k] for k in keys - {"eos_tokens"}): raise ValueError("connection identity fields must be nonempty strings")
    if type(value["eos_tokens"]) is not list or any(type(x) is not int or x < 0 for x in value["eos_tokens"]): raise ValueError("eos_tokens must be nonnegative IDs")
    HTTPTransport(value["endpoint_url"])
    return value

def _client(state, chat):
    def show_provisional(text):
        if not _STREAMED_TEXT:
            print("[assistant text is provisional until COW confirms the saved receipt]", file=sys.stderr, flush=True)
        _STREAMED_TEXT.append(text)
        sys.stdout.write(text)
        sys.stdout.flush()
    from .client_setup import key_for_connection
    return CowClient.http(chat["connection"]["endpoint_url"], journal=OperationJournal(Path(state) / "cow-operations"),
        api_key=key_for_connection(chat["connection"]), endpoint_pin=chat["connection"]["endpoint_pin"],
        stream_handler=show_provisional)

def _print_committed(text):
    if not _STREAMED_TEXT:
        print(text)
    else:
        print()

def _op(value=None):
    value = value or ("bwchat-" + uuid.uuid4().hex)
    if type(value) is not str or not _OPERATION.fullmatch(value): raise ValueError("operation ID must be 1-128 ASCII letters, digits, '_' or '-'")
    return value

def _save_head(chat, receipt):
    branch = receipt.branch
    if branch.name != chat["branch"]: raise ValueError("COW receipt names another conversation branch")
    raw = receipt.raw
    if (raw.get("model_contract_id") != chat["connection"]["model_contract_id"]
            or raw.get("execution_profile_id") != chat["connection"]["execution_profile_id"]):
        raise ValueError("COW receipt model or execution profile differs from the pinned chat connection")
    chat["head"] = {"revision": branch.revision, "tip": branch.tip, "root": branch.root}

def _current_controller(client, chat):
    view = client.history(chat["branch"])
    expected = chat.get("head")
    if (expected is not None
            and (view.revision != expected["revision"] or view.tip != expected["tip"])):
        raise ValueError("conversation branch moved outside this chat; inspect history and reconcile the saved tip")
    if view.raw.get("pending_request") not in (None, False, {}):
        raise OperationIndeterminate("COW reports a request still pending on the conversation branch")
    status = view.raw.get("controller_status")
    if status not in ("idle", "active", "stopped"):
        raise ValueError("COW history lacks a recognized controller status")
    return status

def _complete(state, chat, result, *, user=False):
    text = result.answer.get("text")
    if type(text) is not str: raise ValueError("COW receipt has no exact assistant text")
    _save_head(chat, result.receipt)
    if user: chat["turn_count"] += 1
    pending = chat.get("pending") or {}
    chat["last_completed_operation"] = pending.get("answer_operation_id", pending.get("operation_id"))
    if pending.get("queue_item_ids"):
        chat["completed_queue_item_ids"] = list(pending["queue_item_ids"])
    chat["pending"] = None; chat["status"] = "ready"; _write(state, chat)
    return text

def _dispatch(state, chat, *, reconcile=False):
    p = chat.get("pending")
    if not isinstance(p, dict): raise ValueError("there is no pending chat operation")
    client = _client(state, chat); kind = p["kind"]; op = p["operation_id"]
    def recovered():
        return client.reconcile_generation(op) if reconcile and client.journal.read(op) is not None else None
    if kind == "namespace":
        existing = client.journal.read(op)
        result = client.replay_original(op) if reconcile and existing is not None else client.create_namespace(p["title"], op)
        namespace = result.get("namespace_id") if isinstance(result, dict) else None
        if type(namespace) is not str: raise ValueError("COW namespace result lacks its ID")
        chat["namespace_id"] = namespace; chat["pending"] = None; chat["status"] = "ready"; _write(state, chat)
        return None
    if kind == "first_prepare":
        result = recovered()
        if result is None: result = client.prepare(chat["branch"], chat["namespace_id"], p["message"], op)
        _save_head(chat, result.receipt)
        chat["pending"] = {"kind": "first_answer", "operation_id": p["answer_operation_id"],
                           "revision": result.receipt.branch.revision, "message": p["message"],
                           "max_tokens": p["max_tokens"]}
        if p.get("queue_item_ids"):
            chat["pending"]["queue_item_ids"] = list(p["queue_item_ids"])
        _write(state, chat)
        return _dispatch(state, chat, reconcile=reconcile)
    if kind in ("first_answer", "append_user", "continue"):
        result = recovered()
        if result is None:
            if kind == "first_answer": result = client.answer(chat["branch"], p["revision"], op, p["max_tokens"])
            elif kind == "append_user": result = client.append_user(chat["branch"], p["revision"], op, p["message"], p["max_tokens"])
            else: result = client.continue_(chat["branch"], p["revision"], op, p["max_tokens"])
        return _complete(state, chat, result, user=(kind != "continue"))
    raise ValueError("unsupported pending chat operation")

def init_command(connection_path, state_path, branch, title, *, report=True):
    if type(branch) is not str or not _BRANCH.fullmatch(branch): raise ValueError("branch must be 1-128 ASCII letters, digits, '_' or '-'")
    if type(title) is not str or not title.strip() or len(title.encode()) > 512: raise ValueError("chat title must be nonempty and at most 512 bytes")
    connection = _connection(connection_path); state = _state_dir(state_path, create=True)
    with _locked(state):
        file = state / "chat.json"
        if file.exists() or file.is_symlink():
            chat = _read(state)
            if chat["branch"] != branch or chat["connection"] != connection: raise ValueError("state belongs to another branch or connection")
            if chat["status"] == "initializing": _dispatch(state, chat, reconcile=True); chat = _read(state)
            if report: print(json.dumps({"status": chat["status"], "branch": branch, "state": str(state)}, sort_keys=True))
            return 0
        op = "bwchat-ns-" + uuid.uuid4().hex
        chat = {"schema": 1, "chat_id": uuid.uuid4().hex, "title": title, "branch": branch,
            "connection": connection, "namespace_id": None, "head": None, "turn_count": 0,
            "status": "initializing", "pending": {"kind": "namespace", "operation_id": op, "title": title}}
        _write(state, chat); _dispatch(state, chat); chat = _read(state)
        if report: print(json.dumps({"status": chat["status"], "branch": branch, "namespace_id": chat["namespace_id"], "state": str(state)}, sort_keys=True))
        return 0

def coding_source(state_path):
    """Select an exact committed conversation tip; never select a newer live tip.

    This is a reference into COW's history, not a second transcript. The coding
    launcher persists this snapshot before it creates an independent work branch.
    """
    state = _state_dir(state_path)
    with _locked(state):
        chat = _read(state)
        if chat.get("pending") is not None or chat.get("status") != "ready":
            raise OperationIndeterminate("conversation has unresolved work; use /reconcile first")
        with _queue_locked(state):
            if _queue_read(state):
                raise OperationIndeterminate("conversation has unsent follow-ups; finish them before coding")
        if chat.get("head") is None:
            return None
        if _current_controller(_client(state, chat), chat) != "stopped":
            raise ValueError("Finish the assistant answer with /continue before starting coding.")
        return (chat["branch"], chat["head"]["tip"])


def _message(message, message_file):
    if message is not None and message_file is not None: raise ValueError("choose --message or --message-file")
    if message_file is not None:
        raw = Path(message_file).read_bytes()
        if len(raw) > _MAX_MESSAGE_BYTES: raise ValueError("message exceeds 256 KiB")
        message = raw.decode("utf-8")
    if type(message) is not str or not message.strip() or len(message.encode("utf-8")) > _MAX_MESSAGE_BYTES: raise ValueError("message must be nonempty text up to 256 KiB")
    return message

def send_command(state_path, message, *, message_file=None, operation_id=None, max_tokens=4096):
    message = _message(message, message_file)
    if type(max_tokens) is not int or not 1 <= max_tokens <= 1_000_000: raise ValueError("max tokens must be 1 through 1,000,000")
    state = _state_dir(state_path)
    with _locked(state):
        chat = _read(state); _drain_queue_locked(state, chat); chat = _read(state)
        if chat["status"] != "ready" or chat.get("pending") is not None: raise OperationIndeterminate("chat has unresolved work; run branchwrite chat reconcile first")
        op = _op(operation_id)
        client = _client(state, chat)
        controller = None if chat["turn_count"] == 0 else _current_controller(client, chat)
        if chat["turn_count"] > 0 and controller != "stopped":
            raise ValueError("assistant turn is not complete; use branchwrite chat continue first")
        pending = _pending_for_message(state, chat, message, op, max_tokens)
        chat["status"] = "pending"; chat["pending"] = pending; _write(state, chat)
        _STREAMED_TEXT.clear()
        _print_committed(_dispatch(state, chat)); return 0

def continue_command(state_path, *, operation_id=None, max_tokens=4096):
    if type(max_tokens) is not int or not 1 <= max_tokens <= 1_000_000: raise ValueError("max tokens must be 1 through 1,000,000")
    state = _state_dir(state_path)
    with _locked(state):
        chat = _read(state)
        if chat["status"] != "ready" or chat.get("pending") is not None: raise OperationIndeterminate("chat has unresolved work; run branchwrite chat reconcile first")
        if not isinstance(chat.get("head"), dict): raise ValueError("send the first message before continuing")
        controller = _current_controller(_client(state, chat), chat)
        if controller != "active": raise ValueError("there is no unfinished assistant turn to continue")
        chat["status"] = "pending"; chat["pending"] = {"kind": "continue", "operation_id": _op(operation_id),
            "revision": chat["head"]["revision"], "max_tokens": max_tokens}; _write(state, chat)
        _STREAMED_TEXT.clear()
        _print_committed(_dispatch(state, chat))
        chat = _read(state); _drain_queue_locked(state, chat)
        return 0

def reconcile_command(state_path, operation_id=None):
    state = _state_dir(state_path)
    with _locked(state):
        chat = _read(state); pending = chat.get("pending")
        if pending is None:
            print(json.dumps({"status": "ready", "branch": chat["branch"], "head": chat.get("head")}, sort_keys=True)); return 0
        if operation_id is not None and pending.get("operation_id") != operation_id: raise ValueError("operation ID differs from saved pending operation")
        _STREAMED_TEXT.clear()
        result = _dispatch(state, chat, reconcile=True); chat = _read(state)
        if isinstance(result, str): _print_committed(result)
        else: print(json.dumps({"status": chat["status"], "branch": chat["branch"], "head": chat.get("head")}, sort_keys=True))
        chat = _read(state); _drain_queue_locked(state, chat)
        return 0

def history_command(state_path, *, as_json=False):
    state = _state_dir(state_path); chat = _read(state); view = _client(state, chat).history(chat["branch"])
    result = {"branch": chat["branch"], "revision": view.revision, "tip": view.tip, "messages": [dict(row) for row in view.messages]}
    if as_json: print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    else:
        for row in view.messages: print(f'{row.get("role", "?")}: {row.get("text", "")}')
    return 0

def status_command(state_path, *, as_json=False):
    state = _state_dir(state_path)
    chat = _read(state)
    live = None
    if chat.get("head") is not None:
        view = _client(state, chat).history(chat["branch"])
        live = {"revision": view.revision, "tip": view.tip,
                "controller_status": view.raw.get("controller_status")}
    with _queue_locked(state): queued = len(_queue_read(state))
    result = {"status": chat["status"], "queued_messages": queued, "branch": chat["branch"], "namespace_id": chat.get("namespace_id"),
        "head": chat.get("head"), "live_head": live,
        "live_head_matches_saved": (None if live is None else
            live["revision"] == chat["head"]["revision"] and live["tip"] == chat["head"]["tip"]),
        "turn_count": chat["turn_count"],
        "pending_operation": None if chat.get("pending") is None else chat["pending"].get("operation_id")}
    if as_json: print(json.dumps(result, sort_keys=True))
    else:
        print(f'{result["status"]}: {result["branch"]}; {result["turn_count"]} user turns')
        if result["live_head"] is not None:
            print("COW controller: " + str(result["live_head"]["controller_status"]))
            if result["live_head_matches_saved"] is False:
                print("COW branch moved since this client saved its last tip; inspect history before sending.")
        if result["pending_operation"]: print("Pending operation: " + result["pending_operation"])
        if result["queued_messages"]: print(f"Queued messages: {result['queued_messages']}")
    return 0

def command(args):
    try:
        if args.chat_action == "init": return init_command(args.connection, args.state, args.branch, args.title)
        if args.chat_action == "send": return send_command(args.state, args.message, message_file=args.message_file, operation_id=args.operation_id, max_tokens=args.max_tokens)
        if args.chat_action == "continue": return continue_command(args.state, operation_id=args.operation_id, max_tokens=args.max_tokens)
        if args.chat_action == "queue": return queue_command(args.state, args.message, message_file=args.message_file, operation_id=args.operation_id, max_tokens=args.max_tokens)
        if args.chat_action == "drain": return drain_command(args.state)
        if args.chat_action == "stop-add": return stop_add_command(args.state, args.message, message_file=args.message_file, operation_id=args.operation_id, max_tokens=args.max_tokens)
        if args.chat_action == "reconcile": return reconcile_command(args.state, args.operation_id)
        if args.chat_action == "history": return history_command(args.state, as_json=args.json)
        if args.chat_action == "status": return status_command(args.state, as_json=args.json)
        raise ValueError("unknown chat action")
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
        code = 4 if isinstance(exc, OperationIndeterminate) else 2
        print("branchwrite: " + ascii(str(exc)), file=sys.stderr)
        if code == 4: print("Saved work stays pending; reconcile with its original operation ID.", file=sys.stderr)
        return code
