"""Model-free tests for the native COW transport and identity boundary."""
from __future__ import annotations

import hashlib
import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from branchwrite.cow_client import (
    CowClient,
    COWSourceBinding,
    FrameKey,
    OperationIndeterminate,
    OperationJournal,
    OperationReuseError,
    ReceiptError,
    SlotReturns,
    _Response,
    CliTransport,
)


ROOT = "a" * 64
SNAP0 = "b" * 64
SNAP1 = "c" * 64


class FakeCOW:
    def __init__(self):
        self.requests = []
        self.journal_dir = None
        self.reply_mode = "complete"
        self.head_revision = 0
        self.head_tip = SNAP0

    def handler_type(self):
        owner = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *_args):
                pass

            def _send_json(self, code, value):
                raw = json.dumps(value, separators=(",", ":")).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_GET(self):
                parts = urlsplit(self.path)
                owner.requests.append(("GET", parts.path, None))
                if parts.path == "/cow/status":
                    return self._send_json(200, {"workers": 1, "active": 0})
                if parts.path == "/cow/head":
                    return self._send_json(200, {"name": "main", "revision": owner.head_revision,
                        "tip": owner.head_tip, "root": ROOT})
                if parts.path == "/cow/workspace/history":
                    return self._send_json(200, {"id": "main", "revision": 0,
                        "tip": SNAP0, "messages": []})
                if parts.path == "/cow/operation":
                    return self._send_json(404, {"error": "unknown operation"})
                return self._send_json(404, {"error": "not found"})

            def do_POST(self):
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length)
                body = json.loads(raw.decode("utf-8"))
                owner.requests.append(("POST", self.path, raw))
                if owner.journal_dir is not None:
                    self.server.journal_was_pending = OperationJournal(
                        owner.journal_dir).read(body["operation_id"])["state"] == "pending"
                receipt = {"operation_id": body["operation_id"], "snapshot": SNAP1,
                    "branch": {"name": body["branch"], "revision": 1,
                               "tip": SNAP1, "root": ROOT}}
                event = {"event": "complete", "answer": {"text": "snow ☃", "snapshot": SNAP1},
                         "receipt": receipt}
                if owner.reply_mode == "eof":
                    self.send_response(200)
                    self.send_header("Content-Type", "application/x-ndjson")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                if owner.reply_mode == "wrong-branch":
                    event["receipt"]["branch"]["name"] = "other"
                rows = [{"event": "text", "text": "snow ☃"}, event]
                payload = b"".join(json.dumps(row, ensure_ascii=False).encode() + b"\n" for row in rows)
                self.send_response(200)
                self.send_header("Content-Type", "application/x-ndjson")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        return Handler


class CowClientTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.server_state = FakeCOW()
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), self.server_state.handler_type())
        self.addCleanup(self.httpd.server_close)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(lambda: (self.httpd.shutdown(), self.thread.join(timeout=2)))
        self.journal_dir = Path(self.temp.name) / "intent"
        self.server_state.journal_dir = self.journal_dir
        self.client = CowClient.http(
            f"http://127.0.0.1:{self.httpd.server_port}",
            journal=OperationJournal(self.journal_dir),
            endpoint_pin="test-endpoint",
            max_stream_bytes=2 * 1024 * 1024,
        )

    def test_read_routes_return_typed_observations(self):
        status = self.client.status()
        self.assertEqual(status.capacity["workers"], 1)
        head = self.client.head("main")
        self.assertEqual((head.name, head.revision, head.tip), ("main", 0, SNAP0))
        history = self.client.history("main")
        self.assertEqual(history.branch, "main")
        self.assertEqual(history.messages, ())

    def test_intent_is_durable_before_stream_send_and_receipt_is_bound(self):
        frame = FrameKey("run", "inv", "parent", "attempt", "child", "answer", 0,
                         "op-1", "main")
        result = self.client.answer("main", 0, "op-1", 3,
                                    frame_key=frame, settings={"temperature": 0.0})
        self.assertTrue(self.httpd.journal_was_pending)
        self.assertEqual(result.provisional_text, ("snow ☃",))
        self.assertEqual(result.receipt.snapshot, SNAP1)
        self.assertEqual(result.receipt.branch.revision, 1)
        saved = self.client.journal.read("op-1")
        self.assertEqual(saved["state"], "complete")
        self.assertEqual(saved["source_binding"]["snapshot"], SNAP0)
        self.assertNotIn("api_key", json.dumps(saved).lower())

    def test_completed_operation_replay_uses_original_receipt_without_head_read(self):
        result = self.client.answer("main", 0, "stable", 3)
        request_count = len(self.server_state.requests)
        self.server_state.head_revision, self.server_state.head_tip = 8, "d" * 64
        replay = self.client.answer("main", 0, "stable", 3)
        self.assertEqual(replay.receipt.raw, result.receipt.raw)
        self.assertEqual(len(self.server_state.requests), request_count)
        binding = replay.source_binding
        self.assertEqual(binding.source_branch, "main")
        self.assertEqual(binding.revision, 0)
        self.assertEqual(binding.snapshot, SNAP0)

    def test_eof_leaves_exact_intent_pending_and_never_resends_automatically(self):
        self.server_state.reply_mode = "eof"
        with self.assertRaises(OperationIndeterminate):
            self.client.answer("main", 0, "lost", 3)
        head_reads = sum(row[0] == "GET" and row[1] == "/cow/head"
                         for row in self.server_state.requests)
        self.server_state.head_revision, self.server_state.head_tip = 8, "d" * 64
        self.assertEqual(self.client.journal.read("lost")["state"], "pending")
        with self.assertRaises(OperationIndeterminate):
            self.client.answer("main", 0, "lost", 3)
        self.assertEqual(sum(row[0] == "POST" for row in self.server_state.requests), 1)
        self.assertEqual(sum(row[0] == "GET" and row[1] == "/cow/head"
                             for row in self.server_state.requests), head_reads)

    def test_receipt_for_wrong_branch_is_rejected_and_intent_retained(self):
        self.server_state.reply_mode = "wrong-branch"
        with self.assertRaises(ReceiptError):
            self.client.answer("main", 0, "wrong", 3)
        self.assertEqual(self.client.journal.read("wrong")["state"], "pending")

    def test_generation_completion_without_exact_text_is_rejected_and_intent_retained(self):
        body = self.client._generation_body("main", 0, "answer-no-text", 1, None, None)
        intent = self.client._intent("answer-no-text", "POST", "/cow/text/answer", body,
                                     "main", 0, None)
        record, _ = self.client.journal.begin(intent, self.client.endpoint_url)
        receipt = {"operation_id": "answer-no-text", "snapshot": SNAP1,
                   "branch": {"name": "main", "revision": 1, "tip": SNAP1, "root": ROOT}}
        response = _Response(events=({"event": "complete", "answer": {"snapshot": SNAP1},
                                      "receipt": receipt},), transport="cli")
        with self.assertRaisesRegex(ReceiptError, "lacks exact answer text"):
            self.client._accept_stream(response, record, intent)
        self.assertEqual(self.client.journal.read("answer-no-text")["state"], "pending")

    def test_unknown_process_local_operation_is_indeterminate(self):
        with self.assertRaises(OperationIndeterminate):
            self.client.recover("unknown")

    def test_operation_id_accepts_128_ascii_bytes(self):
        operation_id = "o" + "x" * 127
        self.assertEqual(CowClient._operation_id(operation_id), operation_id)
        with self.assertRaises(ValueError):
            CowClient._operation_id("o" + "x" * 128)

    def test_operation_id_cannot_be_reused_for_changed_bytes(self):
        self.server_state.reply_mode = "eof"
        with self.assertRaises(OperationIndeterminate):
            self.client.answer("main", 0, "same", 3)
        with self.assertRaises(OperationReuseError):
            self.client.ask("main", 0, "same", "changed", 3)


class FrameSlotTests(unittest.TestCase):
    @staticmethod
    def digest(value):
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def test_reverse_delivery_duplicate_old_result_and_restart_identity(self):
        a = FrameKey("r", "parent-call", "p", "try-1", "A", "slot-A", 4,
                     "op-A", "branch-A")
        b = FrameKey("r", "parent-call", "p", "try-1", "B", "slot-B", 7,
                     "op-B", "branch-B")
        source_a = COWSourceBinding("op-A", "branch-A", "source-A", 3, SNAP0, "service-pin")
        source_b = COWSourceBinding("op-B", "branch-B", "source-B", 7, SNAP1, "service-pin")
        slots = SlotReturns()
        value_a, value_b = {"text": "A"}, {"text": "B"}
        digest_a, digest_b = self.digest(value_a), self.digest(value_b)
        slots.deliver(b, source_b, digest_b, value_b)
        slots.deliver(a, source_a, digest_a, value_a)
        self.assertEqual(slots.get("slot-A"), {"text": "A"})
        self.assertEqual(slots.get("slot-B"), {"text": "B"})
        slots_after_restart = SlotReturns.from_json(slots.to_json())
        slots_after_restart.deliver(a, source_a, digest_a, value_a)
        self.assertEqual(slots_after_restart.get("slot-A"), {"text": "A"})
        with self.assertRaises(ValueError):
            slots_after_restart.deliver(
                FrameKey("r", "parent-call", "p", "try-1", "A", "slot-A", 3,
                         "op-A", "branch-A"),
                source_a, self.digest({"text": "late stale A"}), {"text": "late stale A"})
        with self.assertRaises(ValueError):
            slots_after_restart.deliver(a,
                COWSourceBinding("op-other", "branch-A", "source-A", 3, SNAP0, "service-pin"),
                digest_a, value_a)

    def test_slot_rejects_digest_mismatch_and_detaches_return_value(self):
        key = FrameKey("r", "inv", "p", "a", "c", "slot", 1, "op", "branch")
        source = COWSourceBinding("op", "branch", "branch", 2, SNAP0, "pin")
        value = {"tokens": [1, 2]}
        digest = self.digest(value)
        slots = SlotReturns()
        with self.assertRaisesRegex(ValueError, "does not match"):
            slots.deliver(key, source, "0" * 64, value)
        slots.deliver(key, source, digest, value)
        value["tokens"].append(3)
        self.assertEqual(slots.get("slot"), {"tokens": [1, 2]})
        returned = slots.get("slot")
        returned["tokens"].append(4)
        self.assertEqual(slots.get("slot"), {"tokens": [1, 2]})
        serialized = slots.to_json()
        serialized["slots"][0]["value"]["tokens"].append(5)
        self.assertEqual(slots.get("slot"), {"tokens": [1, 2]})


class CliRevisionMappingTests(unittest.TestCase):
    def test_generation_commands_pass_the_original_revision_to_cli(self):
        import tempfile
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as directory:
            transport = CliTransport("http://127.0.0.1:8080", "cow_cli.py",
                                     state_dir=directory)
            for path, extra in (
                    ("/cow/text/answer", {}),
                    ("/cow/text/ask", {"content": "question"}),
                    ("/cow/text/resume", {}),
                    ("/cow/text/append-user", {"content": "tool result"})):
                with self.subTest(path=path):
                    calls = []

                    def fake_run(command, args, *, mutation, streamed=False):
                        calls.append((command, list(args), mutation, streamed))
                        if command == "branches":
                            return _Response(json_value={"branches": [{
                                "name": "main", "revision": 7, "tip": SNAP0, "root": ROOT}]})
                        return _Response(events=({"event": "complete"},), transport="cli")

                    body = {"branch": "main", "revision": 7, "operation_id": "revision-op",
                            "max_tokens": 2, "stream": True, **extra}
                    with patch.object(transport, "_run", side_effect=fake_run):
                        transport.request("POST", path, json.dumps(body).encode(), stream=True)
                    self.assertEqual(len(calls), 2)
                    argv = calls[1][1]
                    revision_index = argv.index("--revision")
                    self.assertEqual(argv[revision_index + 1], "7")

    def test_stale_expected_revision_is_rejected_before_cli_mutation(self):
        import tempfile
        from unittest.mock import patch
        from branchwrite.cow_client import RequestRejected

        with tempfile.TemporaryDirectory() as directory:
            transport = CliTransport("http://127.0.0.1:8080", "cow_cli.py",
                                     state_dir=directory)
            calls = []

            def fake_run(command, args, *, mutation, streamed=False):
                calls.append(command)
                return _Response(json_value={"branches": [{
                    "name": "main", "revision": 8, "tip": SNAP1, "root": ROOT}]})

            body = {"branch": "main", "revision": 7, "operation_id": "stale-op",
                    "max_tokens": 2, "stream": True}
            with patch.object(transport, "_run", side_effect=fake_run):
                with self.assertRaisesRegex(RequestRejected, "revision changed"):
                    transport.request("POST", "/cow/text/answer", json.dumps(body).encode(), stream=True)
            self.assertEqual(calls, ["branches"])


class CliMachineResultTests(unittest.TestCase):
    def test_cli_machine_envelope_preserves_exact_answer_text(self):
        import sys
        import tempfile
        from pathlib import Path

        from branchwrite.cow_client import CliTransport

        answer = {"text": "patch\n", "tokens": [7], "snapshot": SNAP0}
        receipt = {"operation_id": "machine-op", "snapshot": SNAP0,
                   "branch": {"name": "main", "revision": 4, "tip": SNAP0, "root": ROOT}}
        envelope = {"schema": 1, "answer": answer, "receipt": receipt}
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "fake_cli.py"
            script.write_text(
                "import json\n"
                "print(json.dumps(" + repr(envelope) +
                ", ensure_ascii=False, separators=(',', ':')))\n",
                encoding="utf-8")
            transport = CliTransport("http://127.0.0.1:8080", script,
                                     state_dir=Path(directory) / "state",
                                     python_executable=sys.executable)
            response = transport._run("answer", [], mutation=True, streamed=True)
        self.assertEqual(response.transport, "cli")
        self.assertEqual(response.provisional_text, ())
        self.assertEqual(response.events, ({"event": "complete", "answer": answer,
                                            "receipt": receipt},))
        self.assertEqual(response.events[0]["answer"]["text"], "patch\n")

    def test_cli_machine_envelope_preserves_prepare_answer_without_text(self):
        import sys
        import tempfile
        from pathlib import Path

        answer = {"snapshot": SNAP1, "tokens": []}
        receipt = {"operation_id": "prepare-op", "snapshot": SNAP1,
                   "branch": {"name": "main", "revision": 0, "tip": SNAP1, "root": ROOT}}
        envelope = {"schema": 1, "answer": answer, "receipt": receipt}
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "fake_cli.py"
            script.write_text(
                "import json\n"
                "print(json.dumps(" + repr(envelope) + ", separators=(',', ':')))\n",
                encoding="utf-8")
            transport = CliTransport("http://127.0.0.1:8080", script,
                                     state_dir=Path(directory) / "state",
                                     python_executable=sys.executable)
            response = transport._run("prepare", [], mutation=True, streamed=True)
        self.assertEqual(response.events, ({"event": "complete", "answer": answer,
                                           "receipt": receipt},))

    def test_cli_machine_envelope_rejects_nonstring_optional_text(self):
        import sys
        import tempfile
        from pathlib import Path

        answer = {"text": 7, "snapshot": SNAP1}
        receipt = {"operation_id": "bad-op", "snapshot": SNAP1,
                   "branch": {"name": "main", "revision": 0, "tip": SNAP1, "root": ROOT}}
        envelope = {"schema": 1, "answer": answer, "receipt": receipt}
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "fake_cli.py"
            script.write_text(
                "import json\n"
                "print(json.dumps(" + repr(envelope) + ", separators=(',', ':')))\n",
                encoding="utf-8")
            transport = CliTransport("http://127.0.0.1:8080", script,
                                     state_dir=Path(directory) / "state",
                                     python_executable=sys.executable)
            with self.assertRaisesRegex(ReceiptError, "exact answer"):
                transport._run("prepare", [], mutation=True, streamed=True)

    def test_frame_identity_rejects_wrong_operation_or_target_branch(self):
        key = FrameKey("r", "i", "p", "a", "c", "s", 0, "op-A", "branch-A")
        slots = SlotReturns()
        with self.assertRaisesRegex(ValueError, "operation or branch"):
            slots.deliver(key,
                COWSourceBinding("op-B", "branch-A", "source-A", 0, SNAP0, "pin"),
                "a" * 64, {})
        with self.assertRaisesRegex(ValueError, "operation or branch"):
            slots.deliver(key,
                COWSourceBinding("op-A", "branch-B", "source-A", 0, SNAP0, "pin"),
                "a" * 64, {})


if __name__ == "__main__":
    unittest.main()
