"""Actual CPU-only COW HTTP and CLI client conformance against FlowModel."""
from __future__ import annotations

import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path

from branchwrite.cow_client import CowClient, OperationJournal, RequestRejected


class CowClientFlowTests(unittest.TestCase):
    """Uses COW's real coordinator, text adapter, Store, HTTP handler and CLI."""

    def setUp(self):
        from context_time_travel.coordinator import ContextCoordinator
        from context_time_travel.pools import PoolConfig
        from serve.cow_adapter import CowAdapter
        from serve.cow_http import make_server
        from serve.cow_text_adapter import CowTextAdapter
        from serve.cow_workspace import CowWorkspace
        from serve.test_cow_presentation_flow import (
            ByteTokenizer, FlowModel, append_initial_user_suffix,
            append_user_suffix, encode, initial_root_mode, render,
        )

        self.temp = tempfile.TemporaryDirectory(prefix="branchwrite-cow-flow-")
        self.addCleanup(self.temp.cleanup)
        self.trace = []
        self.models = {}
        gate = threading.Event()
        gate.set()
        config = PoolConfig(gpus=(0,), ram_bytes=1024 * 1024,
                            disk_bytes=8 * 1024 * 1024, min_available_bytes=0)

        def factory(gpu):
            model = getattr(self,'model_factory',FlowModel)(self.temp.name, gpu, (0,), self.trace, gate)
            self.models[gpu] = model
            return model

        self.coordinator = ContextCoordinator(self.temp.name, config, factory)
        self.addCleanup(self.coordinator.close)
        self.coordinator.ready(5)
        tokens = ByteTokenizer()
        cow_adapter = CowAdapter(self.coordinator)
        self.text = CowTextAdapter(
            cow_adapter, tokens, render, encode,
            append_user_suffix=append_user_suffix,
            append_initial_user_suffix=append_initial_user_suffix,
            initial_root_mode=initial_root_mode, renderer_id="b" * 64)
        workspace = CowWorkspace(
            self.coordinator.store, tokens,
            root_mode_resolver=self.text.root_mode_for_projection)
        self.server = make_server(
            cow_adapter, host="127.0.0.1", port=0, api_key="cpu-flow-secret",
            text_adapter=self.text, workspace=workspace,
            connection_info=getattr(self,'connection_info',None))
        self.addCleanup(self.server.server_close)
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()
        self.addCleanup(self._stop_server)
        host, port = self.server.server_address[:2]
        self.base_url = f"http://{host}:{port}"

    def _stop_server(self):
        self.server.shutdown()
        self.server_thread.join(timeout=3)

    def _client(self, transport: str, name: str) -> CowClient:
        root = Path(self.temp.name)
        journal = OperationJournal(root / f"journal-{name}")
        if transport == "http":
            return CowClient.http(self.base_url, journal=journal,
                                  api_key="cpu-flow-secret", endpoint_pin="flow-model-free")
        cli = os.environ.get("COW_CLI_SCRIPT")
        if not cli:
            self.fail("COW_CLI_SCRIPT must name the actual checked-out tools/cow_cli.py")
        return CowClient.cli(
            self.base_url, cli, journal=journal,
            state_dir=root / f"cli-state-{name}", api_key="cpu-flow-secret",
            endpoint_pin="flow-model-free")

    def test_user_conversation_tip_stays_current_and_work_fork_is_independent(self):
        client = self._client("http", "user-conversation")
        namespace = client.create_namespace("User conversation", "user-conversation-ns")
        conversation = "user-conversation"
        first = client.prepare(conversation, namespace["namespace_id"],
                               "I need help with the current project.", "user-turn-1")
        first_answer = client.answer(conversation, first.receipt.branch.revision,
                                     "answer-op", 1)
        completed = client.continue_(conversation, first_answer.receipt.branch.revision,
                                     "resume-op", 2)
        shared_tip = completed.receipt.branch.tip
        worker = client.fork(conversation, shared_tip, "work-main", "work-fork-1")
        self.assertEqual(worker.tip, shared_tip)

        latest = client.append_user(conversation, completed.receipt.branch.revision,
                                    "user-op", "Latest update: the server was restarted.", 2)
        self.assertNotEqual(latest.receipt.branch.tip, shared_tip)
        self.assertEqual(client.head(conversation), latest.receipt.branch)
        self.assertEqual(client.head("work-main"), worker)
        current_text = "\n".join(row.get("text", "") for row in client.history(conversation).messages)
        worker_text = "\n".join(row.get("text", "") for row in client.history("work-main").messages)
        self.assertIn("Latest update: the server was restarted.", current_text)
        self.assertNotIn("Latest update: the server was restarted.", worker_text)

    def test_real_http_accepts_128_byte_branch_and_operation_names(self):
        client = self._client("http", "long-names")
        namespace = client.create_namespace("Long names", "long-name-namespace")
        branch = "b" + "x" * 127
        operation = "o" + "x" * 127
        result = client.prepare(branch, namespace["namespace_id"], "A user conversation.", operation)
        self.assertEqual(result.receipt.branch.name, branch)
        self.assertEqual(result.receipt.operation_id, operation)
        self.assertEqual(client.head(branch), result.receipt.branch)

    def _exercise(self, transport: str):
        client = self._client(transport, transport)
        status = client.status()
        self.assertFalse(status.identity_verified)
        namespace = client.create_namespace(f"BranchWrite {transport}", f"ns-{transport}")
        prepared = client.prepare(
            f"bw-{transport}", namespace["namespace_id"], "Solve the task.",
            f"root-{transport}")
        self.assertEqual(prepared.receipt.branch.revision, 1)
        root_head = client.head(f"bw-{transport}")
        self.assertEqual(root_head.tip, prepared.receipt.snapshot)

        answer = client.answer(root_head.name, root_head.revision, "answer-op", 1)
        if transport == "http":
            self.assertEqual("".join(answer.provisional_text), "hi")
        else:
            self.assertEqual(answer.provisional_text, ())
        self.assertEqual(answer.answer["snapshot"], answer.receipt.snapshot)
        self.assertEqual(answer.answer["text"], "hi")
        self.assertEqual(answer.answer["tokens"], [257])
        canonical = self.coordinator.store.lineage(answer.receipt.snapshot)[1]
        self.assertEqual(tuple(canonical[-len(answer.answer["tokens"]):]),
                         tuple(answer.answer["tokens"]))
        self.assertEqual(answer.answer["text"], "".join(
            self.text.tokenizer.token_bytes(token).decode("utf-8")
            for token in answer.answer["tokens"]))
        self.assertEqual(answer.receipt.branch.revision, 2)
        history = client.history(root_head.name)
        self.assertEqual(history.tip, answer.receipt.snapshot)

        alt = client.fork(root_head.name, answer.receipt.snapshot, f"bw-{transport}-alt",
                          f"fork-{transport}")
        self.assertEqual(alt.tip, answer.receipt.snapshot)
        alt_result = client.continue_(alt.name, alt.revision, "copy-resume", 2)
        self.assertEqual(alt_result.receipt.branch.revision, 1)
        self.assertEqual(client.head(root_head.name).tip, answer.receipt.snapshot)

        resumed = client.continue_(root_head.name, answer.receipt.branch.revision,
                                   "resume-op", 2)
        self.assertEqual(resumed.receipt.branch.revision, 3)
        self.assertEqual(resumed.answer["snapshot"], resumed.receipt.snapshot)
        self.assertEqual(resumed.answer["tokens"], [258, 299])
        self.assertEqual(resumed.answer["text"], "!")
        resumed_history = self.coordinator.store.lineage(resumed.receipt.snapshot)[1]
        self.assertEqual(tuple(resumed_history[-len(resumed.answer["tokens"]):]),
                         tuple(resumed.answer["tokens"]))
        self.assertEqual(self.coordinator.store.get_snapshot(resumed.receipt.snapshot)[
            "controller"]["status"], "stopped")
        resumed_head = client.head(root_head.name)
        appended = client.append_user(root_head.name, resumed_head.revision,
                                      "user-op", "Observed tool result: done", 2)
        self.assertEqual(appended.receipt.branch.revision, 4)
        self.assertEqual(appended.answer["snapshot"], appended.receipt.snapshot)
        self.assertEqual(appended.answer["tokens"], [260, 299])
        self.assertEqual(appended.answer["text"], "next")
        appended_history = self.coordinator.store.lineage(appended.receipt.snapshot)[1]
        self.assertEqual(tuple(appended_history[-len(appended.answer["tokens"]):]),
                         tuple(appended.answer["tokens"]))
        if transport == "http":
            self.assertEqual("".join(appended.provisional_text), "next")
        else:
            self.assertEqual(appended.provisional_text, ())
        final_history = client.history(root_head.name)
        self.assertEqual(final_history.tip, appended.receipt.snapshot)
        self.assertTrue(any(row.get("text") == "Observed tool result: done"
                            for row in final_history.messages))

    def test_http_client_prepare_fork_continue_history_tool_observation(self):
        self._exercise("http")

    def test_actual_cli_subprocess_conforms_to_http_client_flow(self):
        self._exercise("cli")

    def test_http_stale_revision_reaches_server_and_is_rejected_before_inference(self):
        from urllib.parse import parse_qs, urlsplit
        from types import SimpleNamespace

        client = self._client("http", "stale-winner")
        namespace = client.create_namespace("stale CAS", "stale-ns")
        prepared = client.prepare("stale-branch", namespace["namespace_id"],
                                  "Solve the task.", "stale-root")
        old_head = client.head("stale-branch")
        winner = client.answer("stale-branch", old_head.revision, "answer-op", 1)
        trace_count = len(self.trace)

        stale_client = CowClient.http(
            self.base_url,
            journal=OperationJournal(Path(self.temp.name) / "journal-stale-cas"),
            api_key="cpu-flow-secret", endpoint_pin="flow-model-free")
        actual_transport = stale_client.transport

        class StaleObservedHead:
            name = "http-stale-head-test"

            def __init__(self):
                self.used = False

            def request(self, method, path, body=None, *, stream=False):
                parsed = urlsplit(path)
                if (not self.used and method == "GET" and parsed.path == "/cow/head"
                        and parse_qs(parsed.query).get("branch") == ["stale-branch"]):
                    self.used = True
                    return SimpleNamespace(json_value={
                        "branch": {"name": old_head.name, "revision": old_head.revision,
                                   "tip": old_head.tip, "root": old_head.root}})
                return actual_transport.request(method, path, body, stream=stream)

        stale_client.transport = StaleObservedHead()
        with self.assertRaises(RequestRejected):
            stale_client.answer("stale-branch", old_head.revision, "stale-op", 1)
        self.assertTrue(stale_client.transport.used)
        self.assertEqual(len(self.trace), trace_count)
        self.assertEqual(client.head("stale-branch").tip, winner.receipt.snapshot)
        self.assertNotEqual(prepared.receipt.snapshot, winner.receipt.snapshot)


if __name__ == "__main__":
    unittest.main()
