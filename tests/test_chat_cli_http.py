"""User-facing chat CLI over the canonical COW conversation tip; CPU fixture."""
import json, os, subprocess, sys, tempfile, time, threading, unittest
from collections import defaultdict
from concurrent.futures import CancelledError
from pathlib import Path

import test_cow_client_flow as fixture


class ChatCliHttpTests(unittest.TestCase):
    def setUp(self):
        self.case = fixture.CowClientFlowTests()
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        # Release fault-injection gates even when an assertion or HTTP call fails.
        for model in self.case.models.values():
            self.addCleanup(model.gate.set)
        self.base = Path(self.case.temp.name)
        self.repo = Path(fixture.__file__).resolve().parents[1]
        self.state = self.base / "user-chat"
        self.connection = self.base / "connection.json"
        self.connection.write_text(json.dumps({
            "endpoint_url": self.case.base_url,
            "endpoint_pin": "flow-model-free",
            "model_contract_id": "flow-model",
            "execution_profile_id": "flow-profile",
            "eos_tokens": [299],
        }))
        self.env = dict(os.environ, BW_COW_API_KEY="cpu-flow-secret",
                        PYTHONDONTWRITEBYTECODE="1",
                        PYTHONPATH=str(self.repo) + os.pathsep + os.environ.get("PYTHONPATH", ""),
                        COW_CLI_SCRIPT=os.environ.get("COW_CLI_SCRIPT", ""))

    def command(self, *args):
        return subprocess.run([sys.executable, "-B", "-m", "branchwrite", *map(str, args)],
                              cwd=self.repo, env=self.env, capture_output=True, text=True,
                              timeout=30)

    def test_cli_keeps_user_conversation_tip_current_and_work_fork_independent(self):
        started = self.command("chat", "init", "--connection", self.connection,
                               "--state", self.state, "--branch", "user-conversation",
                               "--title", "Current user conversation")
        self.assertEqual(started.returncode, 0, started.stderr)
        self.assertEqual(json.loads(started.stdout)["status"], "ready")

        first = self.command("chat", "send", self.state, "--message",
                             "Help me with the project.", "--operation-id", "answer-op",
                             "--max-tokens", "1")
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(first.stdout.strip(), "hi")
        premature = self.command("chat", "send", self.state, "--message",
                                 "Wait for the answer to finish.", "--operation-id",
                                 "must-not-dispatch", "--max-tokens", "1")
        self.assertEqual(premature.returncode, 2)
        self.assertIn("chat continue", premature.stderr)
        saved = json.loads((self.state / "chat.json").read_text())["chat"]
        self.assertIsNone(saved["pending"])
        finished = self.command("chat", "continue", self.state, "--operation-id",
                                "resume-op", "--max-tokens", "2")
        self.assertEqual(finished.returncode, 0, finished.stderr)
        self.assertEqual(finished.stdout.strip(), "!")

        client = self.case._client("http", "work-fork")
        conversation_head = client.head("user-conversation")
        worker = client.fork("user-conversation", conversation_head.tip,
                             "work-main", "work-fork")
        latest = self.command("chat", "send", self.state, "--message",
                              "Latest update: the COW server restarted.",
                              "--operation-id", "user-op", "--max-tokens", "2")
        self.assertEqual(latest.returncode, 0, latest.stderr)
        self.assertEqual(latest.stdout.strip(), "next")

        history = self.command("chat", "history", self.state, "--json")
        self.assertEqual(history.returncode, 0, history.stderr)
        view = json.loads(history.stdout)
        self.assertEqual(view["branch"], "user-conversation")
        self.assertIn("Latest update: the COW server restarted.",
                      "\n".join(row.get("text", "") for row in view["messages"]))
        self.assertEqual(client.head("work-main"), worker)
        status = self.command("chat", "status", self.state, "--json")
        self.assertEqual(status.returncode, 0, status.stderr)
        status_view = json.loads(status.stdout)
        self.assertTrue(status_view["live_head_matches_saved"])
        self.assertEqual(status_view["live_head"]["tip"], view["tip"])
        worker_text = "\n".join(row.get("text", "")
                                 for row in client.history("work-main").messages)
        self.assertNotIn("Latest update: the COW server restarted.", worker_text)

        receipt = self.command("receipt", self.state, "--operation-id", "user-op",
                               "--show-answer", "--json")
        self.assertEqual(receipt.returncode, 0, receipt.stderr)
        self.assertEqual(json.loads(receipt.stdout)["answer"]["text"], "next")
        saved_state = json.loads((self.state / "chat.json").read_text())
        self.assertNotIn("messages", saved_state)
        self.assertNotIn("transcript", saved_state)


    def test_local_followups_are_durable_and_sent_as_one_combined_turn(self):
        started = self.command("chat", "init", "--connection", self.connection,
                               "--state", self.state, "--branch", "user-conversation")
        self.assertEqual(started.returncode, 0, started.stderr)
        first = self.command("chat", "send", self.state, "--message", "Start the chat.",
                             "--operation-id", "answer-op", "--max-tokens", "1")
        self.assertEqual(first.returncode, 0, first.stderr)
        finish = self.command("chat", "continue", self.state, "--operation-id",
                              "resume-op", "--max-tokens", "2")
        self.assertEqual(finish.returncode, 0, finish.stderr)

        model = next(iter(self.case.models.values()))
        model.plans = defaultdict(lambda: (257, 299), model.plans)
        model.plans["active-chat-op"] = (260, 299)
        model.gate.clear()
        trace_before = len(self.case.trace)
        active = subprocess.Popen(
            [sys.executable, "-B", "-m", "branchwrite", "chat", "send", str(self.state),
             "--message", "First active request.", "--operation-id", "active-chat-op",
             "--max-tokens", "2"], cwd=self.repo, env=self.env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            try:
                self.case.coordinator.operation_status("active-chat-op")
                break
            except Exception:
                time.sleep(0.02)
        else:
            model.gate.set()
            self.fail("COW did not admit the active chat request")

        messages = [
            ("queued-chat-op-a", "Also check the page title."),
            ("queued-chat-op-b", "And change the background color to blue."),
        ]
        queued = []
        queue_path = self.state / "chat-queue.json"
        for position, (operation, message) in enumerate(messages, 1):
            queued.append(subprocess.Popen(
                [sys.executable, "-B", "-m", "branchwrite", "chat", "queue", str(self.state),
                 "--message", message, "--operation-id", operation, "--max-tokens", "2"],
                cwd=self.repo, env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True))
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                try:
                    if len(json.loads(queue_path.read_text())["queue"]) == position:
                        break
                except FileNotFoundError:
                    pass
                time.sleep(0.02)
            self.assertEqual(len(json.loads(queue_path.read_text())["queue"]), position,
                             "queued follow-up was not durably recorded")
        saved_queue = json.loads(queue_path.read_text())
        self.assertEqual([row["message"] for row in saved_queue["queue"]],
                         [message for _, message in messages])
        self.assertEqual(queue_path.stat().st_mode & 0o777, 0o600)

        model.gate.set()
        active_out, active_err = active.communicate(timeout=15)
        self.assertEqual(active.returncode, 0, active_err)
        self.assertIn("next", active_out)
        for process in queued:
            queue_out, queue_err = process.communicate(timeout=15)
            self.assertEqual(process.returncode, 0, queue_err)

        self.assertEqual(json.loads(queue_path.read_text())["queue"], [])
        self.assertEqual(len(self.case.trace) - trace_before, 2,
                         "two local follow-ups must cause one COW generation request")
        self.assertEqual(self.case.trace[trace_before][0], "active-chat-op")
        self.assertNotIn(self.case.trace[trace_before + 1][0],
                         {operation for operation, _ in messages})
        view = self.case._client("http", "coalesced-queue-check").history("user-conversation")
        combined = "\n\n".join(message for _, message in messages)
        matching_user_turns = [
            row.get("text", "") for row in view.messages
            if row.get("role") == "user" and all(message in row.get("text", "")
                                                   for _, message in messages)
        ]
        self.assertEqual(matching_user_turns, [combined])

    def test_local_queue_survives_client_death_and_drains_after_reconcile(self):
        started = self.command("chat", "init", "--connection", self.connection,
                               "--state", self.state, "--branch", "user-conversation")
        self.assertEqual(started.returncode, 0, started.stderr)
        first = self.command("chat", "send", self.state, "--message", "Start the chat.",
                             "--operation-id", "answer-op", "--max-tokens", "1")
        self.assertEqual(first.returncode, 0, first.stderr)
        finish = self.command("chat", "continue", self.state, "--operation-id",
                              "resume-op", "--max-tokens", "2")
        self.assertEqual(finish.returncode, 0, finish.stderr)

        model = next(iter(self.case.models.values()))
        model.plans = defaultdict(lambda: (257, 299), model.plans)
        model.plans["crash-active-op"] = (260, 299)
        model.gate.clear()
        active = subprocess.Popen(
            [sys.executable, "-B", "-m", "branchwrite", "chat", "send", str(self.state),
             "--message", "Question already sent.", "--operation-id", "crash-active-op",
             "--max-tokens", "2"], cwd=self.repo, env=self.env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            try:
                self.case.coordinator.operation_status("crash-active-op")
                break
            except Exception:
                time.sleep(0.02)
        else:
            model.gate.set()
            active.kill()
            active.communicate(timeout=5)
            self.fail("COW did not admit the active chat request")

        queued = subprocess.Popen(
            [sys.executable, "-B", "-m", "branchwrite", "chat", "queue", str(self.state),
             "--message", "Follow-up saved on this client.", "--operation-id",
             "crash-queued-op", "--max-tokens", "2"], cwd=self.repo, env=self.env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        queue_path = self.state / "chat-queue.json"
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and not queue_path.exists():
            time.sleep(0.02)
        self.assertTrue(queue_path.exists(), "queued input was not durably recorded")
        self.assertEqual(json.loads(queue_path.read_text())["queue"][0]["message"],
                         "Follow-up saved on this client.")
        active.kill()
        active.communicate(timeout=5)
        self.assertEqual(active.returncode, -9)

        # The request belongs to COW now. Let it finish after the client dies.
        model.gate.set()
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            try:
                if self.case.coordinator.operation_status("crash-active-op")["durable"]:
                    break
            except Exception:
                pass
            time.sleep(0.02)
        else:
            queued.kill()
            queued.communicate(timeout=5)
            self.fail("COW did not durably finish the request after client death")

        # The queued writer may wake first, but it must not send while the prior
        # client operation is unresolved. Reconciliation commits it, then drains.
        queue_out, queue_err = queued.communicate(timeout=10)
        self.assertEqual(queued.returncode, 0, queue_err)
        resumed = self.command("chat", "reconcile", self.state,
                               "--operation-id", "crash-active-op")
        self.assertEqual(resumed.returncode, 0, resumed.stderr)
        self.assertIn("next", resumed.stdout)
        self.assertEqual(json.loads(queue_path.read_text())["queue"], [])
        saved = json.loads((self.state / "chat.json").read_text())["chat"]
        self.assertEqual(saved["status"], "ready")
        self.assertIsNone(saved["pending"])
        self.assertEqual(saved["turn_count"], 3)
        self.assertIn("hi", resumed.stdout)
        history = self.case._client("http", "restart-queue-check").history("user-conversation")
        texts = "\n".join(row.get("text", "") for row in history.messages)
        self.assertLess(texts.index("Question already sent."),
                        texts.index("Follow-up saved on this client."))
        self.assertEqual(self.case.trace[-2][0], "crash-active-op")
        self.assertNotEqual(self.case.trace[-1][0], "crash-queued-op",
                            "local queue item IDs are not dispatched as separate COW requests")
        user_turns = [row.get("text", "") for row in history.messages if row.get("role") == "user"]
        self.assertIn("Follow-up saved on this client.", user_turns[-1])

    def test_stop_add_cancels_before_output_and_retries_with_both_user_inputs(self):
        started = self.command("chat", "init", "--connection", self.connection,
                               "--state", self.state, "--branch", "user-conversation")
        self.assertEqual(started.returncode, 0, started.stderr)
        first = self.command("chat", "send", self.state, "--message", "Seed the conversation.",
                             "--operation-id", "answer-op", "--max-tokens", "1")
        self.assertEqual(first.returncode, 0, first.stderr)
        finish = self.command("chat", "continue", self.state, "--operation-id",
                              "resume-op", "--max-tokens", "2")
        self.assertEqual(finish.returncode, 0, finish.stderr)

        model = next(iter(self.case.models.values()))
        model.plans["cancelled-turn-op"] = (260, 299)
        model.plans["amended-turn-op"] = (257, 299)
        model.gate.clear()
        entered = threading.Event()
        original = model.run_greedy_request
        def cancellable(sid, ids, count, *, stream, on_token, cancelled=None):
            entered.set()
            while not model.gate.wait(.01):
                if cancelled is not None and cancelled():
                    raise CancelledError()
            if cancelled is not None and cancelled():
                raise CancelledError()
            return original(sid, ids, count, stream=stream, on_token=on_token)
        model.run_greedy_request = cancellable

        active = subprocess.Popen(
            [sys.executable, "-B", "-m", "branchwrite", "chat", "send", str(self.state),
             "--message", "First question: inspect the failing test.",
             "--operation-id", "cancelled-turn-op", "--max-tokens", "2"],
            cwd=self.repo, env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertTrue(entered.wait(5), "model did not enter the held request")
        amended = subprocess.Popen(
            [sys.executable, "-B", "-m", "branchwrite", "chat", "stop-add", str(self.state),
             "--message", "Extra detail: preserve the trailing newline.",
             "--operation-id", "amended-turn-op", "--max-tokens", "2"],
            cwd=self.repo, env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            saved = json.loads((self.state / "chat.json").read_text())["chat"]
            pending = saved.get("pending") or {}
            if pending.get("operation_id") == "amended-turn-op":
                model.gate.set()
                break
            time.sleep(.02)
        amended_out, amended_err = amended.communicate(timeout=15)
        amended_result = subprocess.CompletedProcess(amended.args, amended.returncode,
                                                     amended_out, amended_err)
        active_out, active_err = active.communicate(timeout=15)
        self.assertEqual(active.returncode, 4, active_err)
        self.assertEqual(active_out, "")
        self.assertEqual(amended_result.returncode, 0, amended_result.stderr)
        self.assertEqual(amended_result.stdout.strip(), "hi")

        old_status = self.case._client("http", "cancel-check").operation("cancelled-turn-op")
        self.assertEqual(old_status.state, "cancelled")
        self.assertFalse(old_status.durable)
        view = self.case._client("http", "amend-check").history("user-conversation")
        user_rows = [row for row in view.messages if row.get("role") == "user"]
        self.assertIn("First question: inspect the failing test.", user_rows[-1].get("text", ""))
        self.assertIn("Extra detail: preserve the trailing newline.", user_rows[-1].get("text", ""))
        self.assertEqual([entry[0] for entry in self.case.trace[-1:]], ["amended-turn-op"])

    def test_stop_add_before_first_answer_preserves_old_attempt_as_a_sibling(self):
        started = self.command("chat", "init", "--connection", self.connection,
                               "--state", self.state, "--branch", "user-conversation")
        self.assertEqual(started.returncode, 0, started.stderr)
        model = next(iter(self.case.models.values()))
        model.plans["first-answer-op"] = (260, 299)
        model.plans["first-amended-op"] = (257, 299)
        model.gate.clear()
        entered = threading.Event()
        original = model.run_greedy_request
        def cancellable(sid, ids, count, *, stream, on_token, cancelled=None):
            entered.set()
            while not model.gate.wait(.01):
                if cancelled is not None and cancelled(): raise CancelledError()
            if cancelled is not None and cancelled(): raise CancelledError()
            return original(sid, ids, count, stream=stream, on_token=on_token)
        model.run_greedy_request = cancellable
        active = subprocess.Popen(
            [sys.executable, "-B", "-m", "branchwrite", "chat", "send", str(self.state),
             "--message", "Initial question without all the facts.",
             "--operation-id", "first-answer-op", "--max-tokens", "2"],
            cwd=self.repo, env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertTrue(entered.wait(5))
        old_branch = "user-conversation"
        amended = subprocess.Popen(
            [sys.executable, "-B", "-m", "branchwrite", "chat", "stop-add", str(self.state),
             "--message", "Add the missing constraint before answering.",
             "--operation-id", "first-amended-op", "--max-tokens", "2"],
            cwd=self.repo, env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            saved = json.loads((self.state / "chat.json").read_text())["chat"]
            if saved["branch"] != old_branch and (saved.get("pending") or {}).get("operation_id") == "first-amended-op":
                model.gate.set()
                break
            time.sleep(.02)
        active_out, active_err = active.communicate(timeout=15)
        amended_out, amended_err = amended.communicate(timeout=15)
        self.assertEqual(active.returncode, 4, active_err)
        self.assertEqual(active_out, "")
        self.assertEqual(amended.returncode, 0, amended_err)
        self.assertEqual(amended_out.strip(), "hi")
        saved = json.loads((self.state / "chat.json").read_text())["chat"]
        self.assertNotEqual(saved["branch"], old_branch)
        self.assertLessEqual(len(saved["branch"].encode()), 128)
        old_status = self.case._client("http", "first-cancel-check").operation("first-answer-op")
        self.assertEqual(old_status.state, "cancelled")
        view = self.case._client("http", "first-amend-check").history(saved["branch"])
        text = "\n".join(row.get("text", "") for row in view.messages)
        self.assertIn("Initial question without all the facts.", text)
        self.assertIn("Add the missing constraint before answering.", text)
        self.assertNotEqual(self.case._client("http", "old-attempt-check").head(old_branch).tip,
                            view.tip)

    def test_cli_accepts_full_128_byte_branch_and_operation_names(self):
        branch = "b" + "x" * 127
        operation = "o" + "x" * 127
        next(iter(self.case.models.values())).plans[operation] = (257, 299)
        started = self.command("chat", "init", "--connection", self.connection,
                               "--state", self.state, "--branch", branch)
        self.assertEqual(started.returncode, 0, started.stderr)
        result = self.command("chat", "send", self.state, "--message", "Long identifiers work.",
                              "--operation-id", operation, "--max-tokens", "2")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "hi")
        self.assertEqual(self.case._client("http", "long-chat").head(branch).name, branch)
        self.assertEqual((self.state / "chat.json").stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.state.stat().st_mode & 0o777, 0o700)

    def test_lost_cli_ack_reconciles_the_same_saved_user_turn(self):
        next(iter(self.case.models.values())).plans["seed-answer"] = (257, 299)
        next(iter(self.case.models.values())).plans["lost-ack-op"] = (260, 299)
        started = self.command("chat", "init", "--connection", self.connection,
                               "--state", self.state, "--branch", "user-conversation")
        self.assertEqual(started.returncode, 0, started.stderr)
        seed = self.command("chat", "send", self.state, "--message", "Start the discussion.",
                            "--operation-id", "seed-answer", "--max-tokens", "2")
        self.assertEqual(seed.returncode, 0, seed.stderr)

        hook = self.base / "crash-hook"
        hook.mkdir()
        (hook / "sitecustomize.py").write_text(
            "import os\n"
            "from branchwrite.cow_client import OperationJournal\n"
            "_complete = OperationJournal.complete\n"
            "def _crash(self, record, receipt, **kwargs):\n"
            "    if record.get('operation_id') == 'lost-ack-op': os._exit(79)\n"
            "    return _complete(self, record, receipt, **kwargs)\n"
            "OperationJournal.complete = _crash\n", encoding="utf-8")
        env = dict(self.env, PYTHONPATH=str(hook) + os.pathsep + self.env["PYTHONPATH"])
        lost = subprocess.run(
            [sys.executable, "-B", "-m", "branchwrite", "chat", "send", str(self.state),
             "--message", "Latest update: the COW server restarted.",
             "--operation-id", "lost-ack-op", "--max-tokens", "2"],
            cwd=self.repo, env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(lost.returncode, 79)
        self.assertEqual(lost.stdout, "next")
        self.assertIn("provisional", lost.stderr)
        before = len(self.case.trace)
        recovered = self.command("chat", "reconcile", self.state,
                                 "--operation-id", "lost-ack-op")
        self.assertEqual(recovered.returncode, 0, recovered.stderr)
        self.assertEqual(recovered.stdout.strip(), "next")
        self.assertEqual(len(self.case.trace), before)
        history = self.case._client("http", "lost-ack-check").history("user-conversation")
        text = "\n".join(row.get("text", "") for row in history.messages)
        self.assertIn("Latest update: the COW server restarted.", text)
        state = json.loads((self.state / "chat.json").read_text())
        self.assertIsNone(state["chat"]["pending"])
        self.assertEqual(state["chat"]["turn_count"], 2)
        receipt = self.command("receipt", self.state, "--operation-id", "lost-ack-op",
                               "--show-answer", "--json")
        self.assertEqual(receipt.returncode, 0, receipt.stderr)
        self.assertEqual(json.loads(receipt.stdout)["answer"]["text"], "next")



if __name__ == "__main__":
    unittest.main()
