"""COW HTTP process restart and original-operation recovery; CPU fixture."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest


class CowHttpProcessRestartTests(unittest.TestCase):
    def test_lost_answer_ack_recovers_after_cow_process_restart_without_forward_work(self):
        from branchwrite.cow_client import CowClient, OperationJournal

        repo = Path(__file__).resolve().parents[1]
        worker = Path(__file__).with_name("cow_process_restart_server.py")
        self.assertTrue(worker.is_file())
        with tempfile.TemporaryDirectory(prefix="bw-cow-process-restart-") as tmp:
            base = Path(tmp)
            ready = base / "server-ready.json"
            counters = base / "forward-counters.json"
            journal_path = base / "client-journal"
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1",
                       BW_COW_API_KEY="process-restart-key",
                       PYTHONPATH=str(repo) + os.pathsep + os.environ.get("PYTHONPATH", ""))
            processes = []

            def start_server(port):
                ready.unlink(missing_ok=True)
                proc = subprocess.Popen(
                    [sys.executable, "-B", str(worker), str(base), str(port),
                     str(ready), str(counters)],
                    cwd=repo, env=env, stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE, text=True)
                processes.append(proc)
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    if ready.exists():
                        identity = json.loads(ready.read_text())
                        self.assertEqual(identity["pid"], proc.pid)
                        return proc, identity["port"], identity["pid"]
                    if proc.poll() is not None:
                        stderr = proc.stderr.read() if proc.stderr else ""
                        self.fail("COW service process exited before readiness: " + stderr)
                    time.sleep(0.02)
                proc.kill()
                _, stderr = proc.communicate(timeout=5)
                self.fail("COW service process did not become ready: " + (stderr or ""))

            def kill_server(proc):
                if proc.poll() is None:
                    proc.kill()
                proc.communicate(timeout=10)
                self.assertEqual(proc.returncode, -9)

            try:
                first, port, first_pid = start_server(0)
                url = f"http://127.0.0.1:{port}"
                client = CowClient.http(url, journal=OperationJournal(journal_path),
                                        api_key="process-restart-key",
                                        endpoint_pin="cpu-process-restart")
                namespace = client.create_namespace("Process restart", "process-ns")["namespace_id"]
                prepared = client.prepare("ProcessRestart", namespace,
                                          "Keep the saved prefix.", "process-prepare")
                head = client.head("ProcessRestart")
                self.assertEqual(prepared.receipt.branch.tip, head.tip)

                # The child dies after COW has committed and returned its stream,
                # but before the client journal records the answer receipt.
                crash = r'''
import os
from branchwrite.cow_client import CowClient, OperationJournal
original = OperationJournal.complete
def exit_before_receipt(self, record, receipt, *, answer=None):
    if record.get("operation_id") == "process-answer":
        os._exit(79)
    return original(self, record, receipt, answer=answer)
OperationJournal.complete = exit_before_receipt
client = CowClient.http(URL, journal=OperationJournal(JOURNAL),
                        api_key="process-restart-key",
                        endpoint_pin="cpu-process-restart")
client.answer("ProcessRestart", REVISION, "process-answer", 2)
'''
                crash = crash.replace("URL", repr(url)).replace("JOURNAL", repr(str(journal_path)))
                crash = crash.replace("REVISION", repr(head.revision))
                stopped = subprocess.run([sys.executable, "-B", "-c", crash], cwd=repo,
                                         env=env, capture_output=True, text=True, timeout=30)
                self.assertEqual(stopped.returncode, 79, stopped.stderr)
                record = OperationJournal(journal_path).read("process-answer")
                self.assertEqual(record["state"], "pending")
                self.assertNotIn("answer", record)
                operation_before_restart = client.operation("process-answer")
                self.assertTrue(operation_before_restart.durable)
                forward_before_restart = json.loads(counters.read_text())["forward_tokens"]
                self.assertGreater(forward_before_restart, 0)

                # SIGKILL the actual COW service process, then reopen its Store
                # and serve the same endpoint from a new process.
                kill_server(first)
                second, restarted_port, second_pid = start_server(port)
                self.assertEqual(restarted_port, port)
                self.assertNotEqual(second_pid, first_pid)
                operation_after_restart = client.operation("process-answer")
                self.assertTrue(operation_after_restart.durable)
                before_receipt = dict(operation_before_restart.receipt.raw)
                after_receipt = dict(operation_after_restart.receipt.raw)
                self.assertEqual(before_receipt["branch"], after_receipt["branch"])
                self.assertEqual(before_receipt["snapshot"], after_receipt["snapshot"])
                for field in before_receipt.keys() & after_receipt.keys():
                    self.assertEqual(before_receipt[field], after_receipt[field],
                                     "shared receipt field changed across COW restart: " + field)
                recovered = client.reconcile_generation("process-answer")
                self.assertEqual(recovered.operation_id, "process-answer")
                self.assertEqual(recovered.receipt.snapshot,
                                 operation_before_restart.receipt.snapshot)
                self.assertEqual(recovered.answer["tokens"], [257, 299])
                self.assertEqual(OperationJournal(journal_path).read("process-answer")["state"],
                                 "complete")
                self.assertEqual(json.loads(counters.read_text())["forward_tokens"],
                                 forward_before_restart)
                self.assertEqual(client.head("ProcessRestart").tip, recovered.receipt.snapshot)

                # Continue the same conversation after the service process died.
                # Only the appended user suffix and selected output may be new
                # forward work; the saved prefix must come from its checkpoint.
                followup_text = "Add one detail."
                suffix = ("\nuser:" + followup_text.strip() + "\nassistant:").encode()
                followup = client.append_user(
                    "ProcessRestart", client.head("ProcessRestart").revision,
                    "post-restart-user", followup_text, 2)
                self.assertEqual(followup.answer["tokens"], [260, 299])
                self.assertEqual(
                    json.loads(counters.read_text())["forward_tokens"] - forward_before_restart,
                    len(suffix) + 2)
                self.assertNotEqual(client.head("ProcessRestart").tip,
                                    recovered.receipt.snapshot)
                kill_server(second)
            finally:
                for proc in processes:
                    if proc.poll() is None:
                        proc.kill()
                    proc.communicate(timeout=10)


if __name__ == "__main__":
    unittest.main()

