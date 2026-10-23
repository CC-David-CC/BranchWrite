"""Discover a COW connection and keep its key in private client settings.

This performs authenticated discovery GETs. It creates no model context or workflow.
Saved coding launches still pin their own connection and execution identities.
"""
from __future__ import annotations

import fcntl
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import uuid
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request
from .http_request import open_without_redirect

_LIMIT = 64 * 1024
_FIELDS = {"endpoint_url", "endpoint_pin", "model_contract_id", "execution_profile_id", "eos_tokens"}


def _pairs(rows):
    result = {}
    for key, value in rows:
        if key in result:
            raise ValueError("Duplicate field in connection settings")
        result[key] = value
    return result


def _json(raw):
    def invalid(_):
        raise ValueError("Non-finite value in connection settings")
    return json.loads(raw, object_pairs_hook=_pairs, parse_constant=invalid)


def _bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf8")


def _origin(value):
    if type(value) is not str or not value or any(ord(c) <= 32 or ord(c) == 127 for c in value):
        raise ValueError("Enter the COW server address, for example http://127.0.0.1:18099")
    parts = urlsplit(value)
    if (parts.scheme not in ("http", "https") or not parts.hostname or parts.username is not None
            or parts.password is not None or parts.path not in ("", "/") or parts.query or parts.fragment):
        raise ValueError("Use an http(s) server address without a path, password, query or fragment")
    parts.port  # Validate malformed/out-of-range ports before any request.
    return urlunsplit((parts.scheme, parts.netloc, "", "", ""))


def _key(value):
    if type(value) is not str or not 1 <= len(value) <= 4096 or any(not 33 <= ord(c) <= 126 for c in value):
        raise ValueError("Enter a nonempty API key without spaces or control characters")
    return value


def connection_path(home=None, environ=None):
    env = os.environ if environ is None else environ
    home = Path.home() if home is None else Path(home)
    if env.get("BW_COW_CONNECTION"):
        return Path(env["BW_COW_CONNECTION"]).expanduser().absolute()
    base = Path(env.get("XDG_CONFIG_HOME") or home / ".config").expanduser()
    if not base.is_absolute():
        raise ValueError("XDG_CONFIG_HOME must be an absolute folder")
    return base / "branchwrite" / "connection.json"


def read_connection(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("Connection settings must be a regular file")
        raw = stream.read(_LIMIT + 1)
    if len(raw) > _LIMIT:
        raise ValueError("Connection settings are too large")
    value = _json(raw)
    if type(value) is not dict or set(value) != _FIELDS:
        raise ValueError("Connection settings need server/model identities and EOS IDs; keep keys separate")
    _origin(value["endpoint_url"])
    if any(type(value[k]) is not str or not value[k] for k in _FIELDS - {"endpoint_url", "eos_tokens"}):
        raise ValueError("Connection settings have missing identities")
    eos = value["eos_tokens"]
    if type(eos) is not list or not eos or any(type(n) is not int or n < 0 for n in eos):
        raise ValueError("Connection settings need actual EOS token IDs")
    return value


def discover(url, key):
    url = _origin(url)
    key = _key(key)
    request = Request(url + "/cow/info", headers={"Authorization": "Bearer " + key, "Accept": "application/json"})
    try:
        with open_without_redirect(request, timeout=10) as response:
            raw = response.read(_LIMIT + 1)
    except HTTPError as error:
        status = error.code
        error.close()
        if status in (401, 403):
            raise ValueError("The server rejected the API key or access. Check the address and key.") from None
        if 300 <= status < 400:
            raise ValueError("The server returned a redirect; the API key was not forwarded. Use its direct COW address.") from None
        if status == 404:
            raise ValueError("This server lacks COW connection discovery. Ask its operator to update it, or use an existing connection file.") from None
        raise ValueError("COW connection discovery is unavailable (HTTP " + str(status) + "). No task was sent.") from None
    except (URLError, TimeoutError, OSError):
        raise ValueError("Cannot reach the COW server. Check that the server and any SSH tunnel are running. No task was sent.") from None
    if len(raw) > _LIMIT:
        raise ValueError("COW connection information exceeds the size limit")
    value = _json(raw)
    fields = {"schema", "service", "model_contract_id", "execution_profile_id", "eos_tokens", "capabilities"}
    if (type(value) is not dict or set(value) != fields or type(value["schema"]) is not int
            or value["schema"] != 1 or value["service"] != "context-cow"):
        raise ValueError("The server did not return supported COW connection information")
    if any(type(value[k]) is not str or re.fullmatch("[0-9a-f]{64}", value[k]) is None
           for k in ("model_contract_id", "execution_profile_id")):
        raise ValueError("The server did not identify its actual model and execution profile")
    eos = value["eos_tokens"]
    if (type(eos) is not list or not 1 <= len(eos) <= 256
            or any(type(n) is not int or not 0 <= n < 2**31 for n in eos) or len(set(eos)) != len(eos)):
        raise ValueError("The server returned invalid EOS token IDs")
    capabilities = value["capabilities"]
    if type(capabilities) is not dict or any(capabilities.get(k) is not True for k in ("text", "inline_grammars")):
        raise ValueError("BranchWrite needs COW text serving and authenticated inline grammars enabled")
    from .capabilities import observe
    from .cow_client import HTTPTransport, CowClientError
    try:
        observe(HTTPTransport(url,api_key=key,timeout=10),
                model_contract_id=value['model_contract_id'],
                execution_profile_id=value['execution_profile_id'],legacy_info=value)
    except CowClientError as error:
        raise ValueError('COW capability discovery failed: '+str(error)) from error
    return dict(endpoint_url=url, endpoint_pin="bw-origin-" + hashlib.sha256(url.encode()).hexdigest(),
                model_contract_id=value["model_contract_id"], execution_profile_id=value["execution_profile_id"], eos_tokens=eos)


def _directory(path, *, create=False):
    if create:
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError("Client settings must be in a private owned folder, not a link")
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    info = os.fstat(fd)
    if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
        os.close(fd)
        raise ValueError("Client settings folder must be private and owned by you (mode 700)")
    return fd


def _read_private(fd, name):
    try:
        handle = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
    except FileNotFoundError:
        return None
    except OSError:
        raise ValueError("Client settings must be private regular files, not links") from None
    with os.fdopen(handle, "rb") as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) != 0o600):
            raise ValueError("Client settings must be private owned regular files (mode 600)")
        raw = stream.read(_LIMIT + 1)
        if len(raw) > _LIMIT:
            raise ValueError("Client settings exceed the size limit")
        return raw


def _replace(fd, name, raw):
    temporary = ".setup-" + uuid.uuid4().hex
    handle = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, name, src_dir_fd=fd, dst_dir_fd=fd)
        os.fsync(fd)
    finally:
        try: os.unlink(temporary, dir_fd=fd)
        except FileNotFoundError: pass


def key_for_connection(connection, *, home=None, environ=None):
    env = os.environ if environ is None else environ
    if env.get("BW_COW_API_KEY"):
        return env["BW_COW_API_KEY"]
    path = connection_path(home, env)
    if not path.exists():
        return None
    saved = read_connection(path)
    if any(connection.get(field) != saved[field] for field in _FIELDS):
        return None
    return saved_api_key(path)


def connect(url, key, *, home=None, environ=None, save_api=False):
    """Save server identities; keep credentials only with explicit opt-in."""
    connection = discover(url, key)
    path = connection_path(home, environ)
    if path.name in ("credentials.json", ".setup.lock"):
        raise ValueError("Choose a separate filename for the public connection settings")
    directory = _directory(path.parent, create=True)
    try:
        lock = os.open(".setup.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=directory)
        with os.fdopen(lock, "r+b") as stream:
            _read_private(directory, ".setup.lock")
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            _read_private(directory, path.name)
            _read_private(directory, "credentials.json")
            raw = _bytes(connection)
            # Reconnecting without --save-api also removes a previously saved
            # key. Remove it before publication, so interruption cannot leave
            # that key available under newly admitted server settings.
            if not save_api:
                try: os.unlink("credentials.json", dir_fd=directory)
                except FileNotFoundError: pass
                os.fsync(directory)
            _replace(directory, path.name, raw)
            if save_api:
                credentials = _bytes(dict(schema=1, connection_sha256=hashlib.sha256(raw).hexdigest(), api_key=key))
                # Interrupted opt-in publication cannot reuse a mismatched key.
                _replace(directory, "credentials.json", credentials)
    finally:
        os.close(directory)
    return path


def saved_api_key(path):
    path = Path(path)
    # Operator-provided connection files remain usable without a stored key.
    if not (path.parent / "credentials.json").exists():
        return None
    directory = _directory(path.parent)
    try:
        raw = _read_private(directory, path.name)
        key_bytes = _read_private(directory, "credentials.json")
        if raw is None or key_bytes is None:
            return None
        credentials = _json(key_bytes)
        if (type(credentials) is not dict or set(credentials) != {"schema", "connection_sha256", "api_key"}
                or type(credentials["schema"]) is not int or credentials["schema"] != 1
                or credentials["connection_sha256"] != hashlib.sha256(raw).hexdigest()):
            raise ValueError("Saved key does not match these connection settings. Run branchwrite connect again.")
        return _key(credentials["api_key"])
    finally:
        os.close(directory)


def command(url=None, *, home=None, environ=None, input_fn=None, secret_fn=None, output_fn=print, save_api=False, on_key=None):
    env = os.environ if environ is None else environ
    input_fn = input if input_fn is None else input_fn
    secret_fn = getpass.getpass if secret_fn is None else secret_fn
    try:
        if url is None:
            output_fn("Connect to the COW server your operator gave you.")
            url = input_fn("Server address: ").strip()
        output_fn("Server settings will be saved. " + (
            "The API key will also be saved privately (--save-api)." if save_api else
            "The API key stays in memory; use --save-api only if you want to save it."))
        key = env.get("BW_COW_API_KEY") or secret_fn("COW API key (hidden): ").strip()
        path = connect(url, key, home=home, environ=env, save_api=save_api)
        if on_key is not None:
            on_key(key)
        output_fn("Connected. Open your project folder and run branchwrite.")
        output_fn("Settings: " + str(path))
        return 0
    except (OSError, ValueError) as error:
        output_fn("BranchWrite setup: " + str(error))
        return 2
    except (KeyboardInterrupt, EOFError):
        output_fn("Connection setup canceled. No coding task was sent.")
        return 130
