"""First-run connection exercises real HTTP, private files and CLI subprocesses."""
import contextlib
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch


INFO = dict(schema=1, service="context-cow", model_contract_id="a"*64,
            execution_profile_id="b"*64, eos_tokens=[10, 20],
            capabilities=dict(text=True, inline_grammars=True))


class ClientSetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.requests = []
        self.reply = INFO
        self.response_code = 200
        outer = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_): pass
            def do_GET(self):
                outer.requests.append((self.command, self.path, self.headers.get("Authorization")))
                status = outer.response_code if self.headers.get("Authorization") == "Bearer example-secret" else 401
                payload = json.dumps(outer.reply).encode()
                self.send_response(status)
                if status == 302: self.send_header("Location", "/stolen-key")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            def do_POST(self):
                outer.requests.append((self.command, self.path, self.headers.get("Authorization")))
                self.send_error(500)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.thread.join, 5)
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.url = "http://127.0.0.1:" + str(self.server.server_port)
        self.env = {"XDG_CONFIG_HOME": str(self.home / "config")}

    def test_default_connection_does_not_persist_the_api_key(self):
        from branchwrite.client_setup import connect, saved_api_key
        path = connect(self.url, "example-secret", home=self.home, environ=self.env)
        self.assertFalse((path.parent / "credentials.json").exists())
        self.assertIsNone(saved_api_key(path))
        for item in path.parent.iterdir():
            self.assertNotIn(b"example-secret", item.read_bytes())

    def test_reconnecting_without_opt_in_removes_an_old_saved_key(self):
        from branchwrite.client_setup import connect, saved_api_key
        path = connect(self.url, "example-secret", home=self.home, environ=self.env, save_api=True)
        self.assertEqual(saved_api_key(path), "example-secret")
        connect(self.url, "example-secret", home=self.home, environ=self.env)
        self.assertIsNone(saved_api_key(path))
        self.assertFalse((path.parent / "credentials.json").exists())

    def test_cli_save_api_flag_explicitly_persists_private_key(self):
        from branchwrite.client_setup import saved_api_key
        env = dict(os.environ, **self.env, HOME=str(self.home), BW_COW_API_KEY="example-secret")
        result = subprocess.run([sys.executable, "-m", "branchwrite", "connect", self.url, "--save-api"],
                                env=env, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("example-secret", result.stdout + result.stderr)
        self.assertEqual(saved_api_key(self.home / "config" / "branchwrite" / "connection.json"), "example-secret")

    def test_default_session_save_api_flag_is_explicit(self):
        from branchwrite.__main__ import main
        with patch("branchwrite.interactive_cli.run", return_value=0) as run:
            self.assertEqual(main(["--save-api"]), 0)
            run.assert_called_once_with(project=Path.cwd(),state=None,save_api=True)

    def test_connection_discovers_identities_and_private_key_can_be_reused(self):
        from branchwrite.client_setup import connect, read_connection, saved_api_key
        path = connect(self.url, "example-secret", home=self.home, environ=self.env, save_api=True)
        connection = read_connection(path)
        self.assertEqual(connection["endpoint_url"], self.url)
        self.assertEqual(connection["execution_profile_id"], "b"*64)
        self.assertEqual(connection["eos_tokens"], [10, 20])
        self.assertEqual(self.requests, [("GET", "/cow/info", "Bearer example-secret")])
        self.assertNotIn("example-secret", path.read_text())
        self.assertEqual(saved_api_key(path), "example-secret")
        self.assertEqual(stat.S_IMODE(path.parent.stat().st_mode), 0o700)
        for item in path.parent.iterdir():
            self.assertEqual(stat.S_IMODE(item.stat().st_mode), 0o600)

    def test_failed_authentication_does_not_create_settings(self):
        from branchwrite.client_setup import connect
        with self.assertRaisesRegex(ValueError, "API key"):
            connect(self.url, "wrong", home=self.home, environ=self.env, save_api=True)
        self.assertFalse((self.home / "config").exists())

    def test_redirects_do_not_forward_bearer_credentials(self):
        from branchwrite.client_setup import connect
        self.response_code = 302
        with self.assertRaisesRegex(ValueError, "redirect"):
            connect(self.url, "example-secret", home=self.home, environ=self.env, save_api=True)
        self.assertEqual(len(self.requests), 1)
        self.assertFalse((self.home / "config").exists())

    def test_normal_cow_requests_do_not_follow_redirects_either(self):
        from branchwrite.cow_client import HTTPTransport, OperationIndeterminate
        self.response_code = 302
        transport = HTTPTransport(self.url, api_key="example-secret", timeout=2)
        with self.assertRaisesRegex(OperationIndeterminate, "redirect"):
            transport.request("GET", "/cow/status")
        self.assertEqual(self.requests, [("GET", "/cow/status", "Bearer example-secret")])

    def test_invalid_or_unsupported_server_response_preserves_existing_settings(self):
        from branchwrite.client_setup import connect
        path = connect(self.url, "example-secret", home=self.home, environ=self.env, save_api=True)
        original = {p.name:p.read_bytes() for p in path.parent.iterdir()}
        for change in [dict(model_contract_id="invented"), dict(eos_tokens=[True]),
                       dict(schema=2), dict(capabilities=dict(text=True, inline_grammars=False))]:
            with self.subTest(change=change):
                self.reply = dict(INFO, **change)
                with self.assertRaises(ValueError):
                    connect(self.url, "example-secret", home=self.home, environ=self.env, save_api=True)
                self.assertEqual({p.name:p.read_bytes() for p in path.parent.iterdir()}, original)

    def test_key_does_not_follow_changed_connection_or_loose_file_permissions(self):
        from branchwrite.client_setup import connect, saved_api_key
        path = connect(self.url, "example-secret", home=self.home, environ=self.env, save_api=True)
        raw = path.read_bytes()
        connection = json.loads(raw)
        connection["endpoint_url"] = "http://127.0.0.1:2"
        path.write_text(json.dumps(connection))
        with self.assertRaisesRegex(ValueError, "connection"):
            saved_api_key(path)
        path.write_bytes(raw)
        credentials = path.parent / "credentials.json"
        credentials.chmod(0o644)
        with self.assertRaisesRegex(ValueError, "private"):
            saved_api_key(path)

    def test_linked_config_directory_or_credential_file_is_not_overwritten(self):
        from branchwrite.client_setup import connect
        config = self.home / "config"
        config.mkdir()
        elsewhere = self.home / "elsewhere"
        elsewhere.mkdir(mode=0o700)
        (config / "branchwrite").symlink_to(elsewhere, target_is_directory=True)
        with self.assertRaises(ValueError):
            connect(self.url, "example-secret", home=self.home, environ=self.env, save_api=True)
        self.assertEqual(list(elsewhere.iterdir()), [])
        (config / "branchwrite").unlink()
        path = connect(self.url, "example-secret", home=self.home, environ=self.env, save_api=True)
        key = path.parent / "credentials.json"
        key.unlink()
        target = elsewhere / "target"
        target.write_text("keep")
        key.symlink_to(target)
        with self.assertRaises(ValueError):
            connect(self.url, "example-secret", home=self.home, environ=self.env, save_api=True)
        self.assertEqual(target.read_text(), "keep")

    def test_saved_key_applies_only_to_the_exact_admitted_connection(self):
        from branchwrite.client_setup import connect, read_connection, key_for_connection
        path = connect(self.url, "example-secret", home=self.home, environ=self.env, save_api=True)
        connection = read_connection(path)
        self.assertEqual(key_for_connection(dict(connection, branch="old-task"), home=self.home, environ=self.env), "example-secret")
        for field, value in [("endpoint_url", "http://127.0.0.1:2"), ("model_contract_id", "c"*64),
                             ("execution_profile_id", "d"*64), ("eos_tokens", [30])]:
            with self.subTest(field=field):
                self.assertIsNone(key_for_connection(dict(connection, **{field:value}), home=self.home, environ=self.env))
        self.assertEqual(key_for_connection({}, home=self.home, environ=dict(self.env, BW_COW_API_KEY="override")), "override")

    def test_interrupted_configuration_never_uses_key_for_a_changed_connection(self):
        from branchwrite import client_setup
        path = client_setup.connect(self.url, "example-secret", home=self.home, environ=self.env, save_api=True)
        original_key = (path.parent / "credentials.json").read_bytes()
        self.reply = dict(INFO, execution_profile_id="c"*64)
        replace = os.replace
        def interrupt(src, dst, **kwargs):
            if dst == "credentials.json":
                raise OSError("injected interrupted key publication")
            return replace(src, dst, **kwargs)
        with patch("branchwrite.client_setup.os.replace", side_effect=interrupt):
            with self.assertRaises(OSError):
                client_setup.connect(self.url, "example-secret", home=self.home, environ=self.env, save_api=True)
        self.assertEqual((path.parent / "credentials.json").read_bytes(), original_key)
        with self.assertRaisesRegex(ValueError, "connection"):
            client_setup.saved_api_key(path)
        client_setup.connect(self.url, "example-secret", home=self.home, environ=self.env, save_api=True)
        self.assertEqual(client_setup.saved_api_key(path), "example-secret")

    def test_cli_connect_uses_environment_key_without_printing_it(self):
        env = dict(os.environ, **self.env, HOME=str(self.home), BW_COW_API_KEY="example-secret")
        completed = subprocess.run([sys.executable, "-m", "branchwrite", "connect", self.url],
                                   env=env, capture_output=True, text=True, timeout=10)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("Connected", completed.stdout)
        self.assertFalse((self.home / "config" / "branchwrite" / "credentials.json").exists())
        self.assertNotIn("example-secret", completed.stdout + completed.stderr)
        self.assertEqual([r[:2] for r in self.requests], [("GET", "/cow/info")])

    def test_real_terminal_first_start_connects_and_hides_the_key(self):
        import pty
        import select
        import time
        master, slave = pty.openpty()
        env = dict(os.environ, **self.env, HOME=str(self.home))
        env.pop("BW_COW_API_KEY", None)
        env.pop("BW_COW_CONNECTION", None)
        project=self.home/'first-project';project.mkdir()
        env['PYTHONPATH']=os.pathsep.join([str(Path(__file__).resolve().parents[1]),env.get('PYTHONPATH','')])
        proc = subprocess.Popen([sys.executable, "-m", "branchwrite"],cwd=project,
                                stdin=slave, stdout=slave, stderr=slave, env=env, start_new_session=True)
        os.close(slave)
        transcript = bytearray()
        def until(marker):
            end = time.monotonic() + 10
            while marker not in transcript and time.monotonic() < end:
                ready, _, _ = select.select([master], [], [], 0.1)
                if ready:
                    try: part = os.read(master, 4096)
                    except OSError: break
                    if not part: break
                    transcript.extend(part)
            self.assertIn(marker, transcript, transcript.decode(errors="replace"))
        try:
            until(b"Server address:")
            os.write(master, self.url.encode() + b"\n")
            until(b"COW API key (hidden):")
            os.write(master, b"example-secret\n")
            until(b"You>")
            os.write(master, b"\x04")  # EOF cleanly closes the idle interactive session.
            proc.wait(timeout=10)
            self.assertEqual(proc.returncode, 0)
            self.assertNotIn(b"example-secret", transcript)
            self.assertFalse((self.home / "config" / "branchwrite" / "credentials.json").exists())
            self.assertEqual([r[:2] for r in self.requests], [("GET", "/cow/info")])
        finally:
            if proc.poll() is None:
                proc.terminate()
                proc.wait(timeout=5)
            os.close(master)

    def test_missing_settings_can_be_configured_inside_first_run(self):
        from branchwrite import guided_cli
        answers = iter([self.url, ""])  # Connect, then leave the task blank; no model work.
        (self.home / "project").mkdir()
        (self.home / "project" / "index.html").write_text("hello")
        output = io.StringIO()
        with patch("branchwrite.guided_cli.coding_start") as start:
            status = guided_cli.run(cwd=self.home / "project", home=self.home, environ=self.env,
                                    input_fn=lambda _:next(answers), secret_fn=lambda _:"example-secret",
                                    output_fn=lambda text:print(text, file=output))
        self.assertEqual(status, 2)
        start.assert_not_called()
        self.assertIn("Connected", output.getvalue())
        self.assertNotIn("No such file", output.getvalue())
        self.assertEqual([r[:2] for r in self.requests], [("GET", "/cow/info")])


if __name__ == "__main__":
    unittest.main()
