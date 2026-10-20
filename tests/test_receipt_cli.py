"""Read-only local inspection of the client's durable generation receipt."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from branchwrite.__main__ import main
from branchwrite.cow_client import OperationIntent, OperationJournal


class ReceiptCommandTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state = Path(self.tmp.name) / "state"
        self.state.mkdir(mode=0o700)
        self.journal = OperationJournal(self.state / "cow-operations")

    def invoke(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(["receipt", str(self.state), *args])
        return code, out.getvalue(), err.getvalue()

    def test_missing_operation_is_reported_without_creating_state(self):
        before = sorted(str(path.relative_to(self.state)) for path in self.state.rglob("*"))
        code, out, err = self.invoke("--operation-id", "missing-op", "--json")
        self.assertEqual(code, 2, err)
        self.assertEqual(json.loads(out)["status"], "NOT_FOUND")
        self.assertEqual(sorted(str(path.relative_to(self.state)) for path in self.state.rglob("*")), before)

    def test_pending_intent_is_unresolved_and_never_queries_endpoint(self):
        operation = "pending-receipt"
        body = json.dumps({"operation_id": operation}, sort_keys=True,
                          separators=(",", ":")).encode()
        intent = OperationIntent(operation, "POST", "/cow/text/answer", body,
                                 "main", 2, None, "endpoint-pin")
        self.journal.begin(intent, "http://127.0.0.1:1")
        directory = self.state / "cow-operations"
        before = {path.name: path.read_bytes() for path in directory.glob("*.json")}
        code, out, err = self.invoke("--operation-id", operation, "--json")
        self.assertEqual(code, 3, err)
        view = json.loads(out)
        self.assertEqual(view["status"], "UNRESOLVED")
        self.assertNotIn("cow_receipt", view)
        self.assertIn("original operation ID", view["next_action"])
        after = {path.name: path.read_bytes() for path in directory.glob("*.json")}
        self.assertEqual(after, before)

    def test_tampered_journal_is_rejected(self):
        operation = "pending-tamper"
        body = json.dumps({"operation_id": operation}, sort_keys=True,
                          separators=(",", ":")).encode()
        intent = OperationIntent(operation, "POST", "/cow/text/answer", body,
                                 "main", 2, None, "endpoint-pin")
        self.journal.begin(intent, "http://127.0.0.1:1")
        path = next((self.state / "cow-operations").glob("*.json"))
        value = json.loads(path.read_text())
        value["branch"] = "other"
        path.write_text(json.dumps(value))
        code, out, err = self.invoke("--operation-id", operation, "--json")
        self.assertEqual(code, 2)
        self.assertIn("integrity", err.lower())


if __name__ == "__main__":
    unittest.main()
