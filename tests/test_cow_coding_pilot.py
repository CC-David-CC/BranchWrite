"""The pilot must execute real protected tests; scripted model output is CPU-only."""
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from tools.run_cow_coding_pilot import ARMS, CodingPilot, FileTask, Task


class ScriptedClient:
    def __init__(self, proposal):
        self.proposal = proposal
        self.calls = []
        self.revision = 0

    def _result(self, text, *, complete=True):
        self.revision += 1
        return SimpleNamespace(
            answer={"text": text, "tokens": [10, 99 if complete else 11]},
            receipt=SimpleNamespace(
                branch=SimpleNamespace(revision=self.revision, tip="a" * 64),
                raw={"snapshot": "a" * 64}),
            operation_id=f"op-{self.revision}")

    def create_namespace(self, title, operation_id):
        self.calls.append(("namespace", title))
        return {"namespace_id": "namespace"}

    def prepare(self, branch, namespace, text, operation_id, **kwargs):
        self.calls.append(("prepare", text, kwargs))
        return self._result("")

    def answer(self, branch, revision, operation_id, max_tokens, **kwargs):
        self.calls.append(("answer", kwargs))
        return self._result(self.proposal)

    def append_user(self, branch, revision, operation_id, content, max_tokens, **kwargs):
        self.calls.append(("feedback", content, kwargs))
        return self._result("TEXT report\n|Changed src/arith.py. The protected tests passed.\nEND\n")


class CreateReadPilotTests(unittest.TestCase):
    """Scripted model output tests host mechanics, not Q4 capability."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="bw-h00-pilot-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        self.task = FileTask("H00", self.source, "hello.txt",
                             "Create hello.txt containing a greeting followed by LF; read it back.")

    def run_case(self, text, *, complete=True):
        client = ScriptedClient(text)
        normal = client._result
        client._result = lambda text, **kwargs: normal(text, complete=complete)
        pilot = CodingPilot(client, self.root / "run", eos_tokens=(99,), max_tokens=128)
        return client, pilot.run_create_read(self.task)

    def test_completed_literal_is_created_and_read_using_real_tools(self):
        client, result = self.run_case("TEXT replacement\n|Hello, loop.\nEND\n")
        self.assertEqual(result.status, "FILE_CREATED_AND_READ")
        self.assertEqual((self.root / "run/tool/workspace/hello.txt").read_bytes(), b"Hello, loop.\n")
        self.assertEqual((self.root / "run/readback.bin").read_bytes(), b"Hello, loop.\n")
        self.assertFalse((self.source / "hello.txt").exists())
        self.assertEqual(result.created_sha256, result.readback_sha256)
        self.assertEqual(result.readback_bytes, 13)
        self.assertEqual(len([row for row in client.calls if row[0] == "answer"]), 1)
        prompt = next(row[1] for row in client.calls if row[0] == "prepare")
        self.assertNotIn("Protected tests", prompt)
        self.assertNotIn("Hello, loop.", prompt)

    def test_malformed_and_incomplete_proposals_create_nothing(self):
        client, result = self.run_case("Here is your file\n")
        self.assertEqual(result.status, "FORMAT_REJECTED")
        self.assertFalse((self.root / "run/tool/workspace/hello.txt").exists())
        self.assertNotIn("feedback", [row[0] for row in client.calls])

    def test_incomplete_well_framed_literal_creates_nothing(self):
        _, result = self.run_case("TEXT replacement\n|hello\nEND\n", complete=False)
        self.assertEqual(result.status, "OUTPUT_INCOMPLETE")
        self.assertFalse((self.root / "run/tool/workspace/hello.txt").exists())

    def test_existing_target_rejects_before_any_model_call(self):
        (self.source / "hello.txt").write_bytes(b"existing")
        client = ScriptedClient("TEXT replacement\n|new\nEND\n")
        pilot = CodingPilot(client, self.root / "run", eos_tokens=(99,))
        with self.assertRaises(ValueError):
            pilot.run_create_read(self.task)
        self.assertEqual(client.calls, [])
        self.assertEqual((self.source / "hello.txt").read_bytes(), b"existing")

    def test_bad_path_rejects_before_any_model_call(self):
        client = ScriptedClient("TEXT replacement\n|hello\nEND\n")
        pilot = CodingPilot(client, self.root / "run", eos_tokens=(99,))
        with self.assertRaises(ValueError):
            pilot.run_create_read(FileTask("H00", self.source, "../outside", "create"))
        self.assertEqual(client.calls, [])


class CodingPilotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="bw-coding-pilot-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        source = self.root / "source"
        (source / "src").mkdir(parents=True)
        (source / "tests").mkdir()
        (source / "src/__init__.py").write_bytes(b"")
        (source / "tests/__init__.py").write_bytes(b"")
        self.original = b"def add(a, b):\n    return a - b\n"
        (source / "src/arith.py").write_bytes(self.original)
        (source / "tests/test_arith.py").write_bytes(
            b"import unittest\nfrom src.arith import add\n"
            b"class Check(unittest.TestCase):\n"
            b"    def test_add(self): self.assertEqual(add(4, 3), 7)\n"
            b"    def test_negative(self): self.assertEqual(add(-2, 5), 3)\n")
        self.task = Task("add", source, "src/arith.py", "Make add return the sum of its arguments.")
        self.proposal = "TEXT replacement\n|def add(a, b):\n|    return a + b\nEND\n"

    def pilot(self, client, name="run"):
        return CodingPilot(client, self.root / name, eos_tokens=(99,), max_tokens=512)

    def test_real_edit_test_feedback_preserves_source(self):
        client = ScriptedClient(self.proposal)
        result = self.pilot(client).run(self.task, "baseline")
        self.assertEqual(result.status, "TASK_PASS")
        self.assertEqual(result.before_exit, 1)
        self.assertEqual(result.after_exit, 0)
        self.assertTrue(result.format_valid)
        self.assertEqual((self.task.source / self.task.edit_path).read_bytes(), self.original)
        feedback = next(row[1] for row in client.calls if row[0] == "feedback")
        self.assertIn("exit_code=0", feedback)
        self.assertIn("OK", feedback)
        self.assertTrue((self.root / "run/result.toml").is_file())

    def test_malformed_proposal_never_becomes_an_edit(self):
        client = ScriptedClient("Here is the patch:\n" + self.proposal)
        result = self.pilot(client).run(self.task, "baseline")
        self.assertEqual(result.status, "FORMAT_REJECTED")
        self.assertFalse(result.format_valid)
        self.assertIsNone(result.after_exit)
        self.assertNotIn("feedback", [row[0] for row in client.calls])

    def test_legal_wrong_patch_is_not_task_success(self):
        client = ScriptedClient(self.proposal.replace("a + b", "a * b"))
        result = self.pilot(client).run(self.task, "gbnf")
        self.assertTrue(result.format_valid)
        self.assertEqual(result.status, "TASK_FAIL")
        self.assertEqual(result.after_exit, 1)
        self.assertFalse(result.report_truthful)

    def test_four_arms_change_only_example_and_grammar(self):
        observed = {}
        for arm in ARMS:
            client = ScriptedClient(self.proposal)
            self.pilot(client, arm).run(self.task, arm)
            prompt = next(row[1] for row in client.calls if row[0] == "prepare")
            options = next(row[1] for row in client.calls if row[0] == "answer")
            observed[arm] = prompt, options
        self.assertEqual(observed["baseline"][0], observed["gbnf"][0])
        self.assertEqual(observed["example"][0], observed["both"][0])
        self.assertNotEqual(observed["baseline"][0], observed["example"][0])
        self.assertIsNone(observed["baseline"][1].get("grammar_state"))
        self.assertIsNone(observed["example"][1].get("grammar_state"))
        self.assertEqual(observed["gbnf"][1]["grammar_state"], "BW_REPLACEMENT")
        self.assertEqual(observed["both"][1]["grammar_state"], "BW_REPLACEMENT")
        self.assertEqual(len({repr(row[1].get("settings")) for row in observed.values()}), 1)

    def test_consumed_partial_output_is_not_executable(self):
        client = ScriptedClient(self.proposal)
        normal = client._result
        client._result = lambda text, **kwargs: normal(text, complete=False)
        result = self.pilot(client).run(self.task, "both")
        self.assertEqual(result.status, "OUTPUT_INCOMPLETE")
        self.assertIsNone(result.after_exit)
        self.assertNotIn("feedback", [row[0] for row in client.calls])

    def test_existing_output_directory_is_never_reused(self):
        directory = self.root / "existing"
        directory.mkdir()
        sentinel = directory / "keep"
        sentinel.write_bytes(b"owned elsewhere")
        with self.assertRaises(FileExistsError):
            self.pilot(ScriptedClient(self.proposal), "existing")
        self.assertEqual(sentinel.read_bytes(), b"owned elsewhere")

    def test_escaping_task_path_is_rejected_before_model_submission(self):
        client = ScriptedClient(self.proposal)
        task = Task("escape", self.task.source, "../../private.txt", "Read this")
        with self.assertRaises(ValueError):
            self.pilot(client).run(task, "baseline")
        self.assertEqual(client.calls, [])

    def test_subset_cannot_claim_full_campaign_pass(self):
        from validation.run_cow_coding_campaign import campaign_status
        one = [{"label": "add-gbnf", "result": {"status": "TASK_PASS", "report_truthful": True}}]
        self.assertEqual(campaign_status(one), "BOUNDED_CODING_SUBSET_PASS")
        self.assertEqual(campaign_status([]), "NO_MODEL_OUTCOMES")
        full = [{"label": task + "-" + arm,
                 "result": {"status": "TASK_PASS", "report_truthful": True}}
                for task in ("add", "multiply") for arm in ARMS]
        self.assertEqual(campaign_status(full), "BOUNDED_CODING_PILOT_PASS")
        self.assertEqual(campaign_status(full + full[:1]), "INVALID_CAMPAIGN_OUTCOMES")

    def test_progress_error_does_not_persist_exception_secrets(self):
        from validation.run_cow_coding_campaign import tracker_error
        self.assertEqual(tracker_error(RuntimeError("do-not-persist-this-secret")), "RuntimeError")
        self.assertIsNone(tracker_error(None))

    def test_campaign_cli_transport_uses_exact_machine_client_and_own_journal(self):
        from unittest.mock import patch
        from branchwrite.cow_client import CowClient, OperationJournal
        from validation.run_cow_coding_campaign import campaign_client
        case = self.root / "cli-case"
        case.mkdir()
        with patch.object(CowClient, "cli") as cli, patch.object(CowClient, "http") as http:
            client = campaign_client("cli", "http://127.0.0.1:1234",
                self.root / "cow_cli.py", case, "secret", "a" * 64)
        self.assertIs(client, cli.return_value)
        http.assert_not_called()
        self.assertEqual(cli.call_args.args,
                         ("http://127.0.0.1:1234", self.root / "cow_cli.py"))
        self.assertEqual(cli.call_args.kwargs["state_dir"], case / "cli-state")
        self.assertIsInstance(cli.call_args.kwargs["journal"], OperationJournal)
        self.assertEqual(cli.call_args.kwargs["endpoint_pin"], "a" * 64)
        self.assertEqual(cli.call_args.kwargs["api_key"], "secret")

    def test_campaign_transport_is_explicit_and_invalid_choice_fails_before_journal(self):
        from validation.run_cow_coding_campaign import campaign_client
        case = self.root / "invalid-case"
        case.mkdir()
        with self.assertRaises(ValueError):
            campaign_client("unknown", "http://127.0.0.1:1234",
                self.root / "cow_cli.py", case, "secret", "a" * 64)
        self.assertEqual(list(case.iterdir()), [])

    def test_campaign_fingerprints_the_selected_executable_from_declared_files(self):
        import hashlib
        from validation.run_cow_coding_campaign import native_executable_identity
        executable = self.root / "native-worker"
        executable.write_bytes(b"bounded native fingerprint fixture")
        digest = hashlib.sha256(executable.read_bytes()).hexdigest()
        profile = {"execution": {"sut_command": [str(executable), "--model", "fixture"]},
                   "native_build": {"sha256": {str(executable): digest}}}
        self.assertEqual(native_executable_identity(profile),
                         {"path": str(executable), "sha256": digest})
        executable.write_bytes(b"different executable bytes")
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            native_executable_identity(profile)

    def test_campaign_rejects_an_unpinned_executable_before_server_launch(self):
        import hashlib
        from validation.run_cow_coding_campaign import native_executable_identity
        executable = self.root / "native-worker"
        executable.write_bytes(b"bounded native fingerprint fixture")
        profile = {"execution": {"sut_command": [str(executable)]},
                   "native_build": {"binary_sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
                                    "sha256": {}}}
        with self.assertRaisesRegex(ValueError, "declared"):
            native_executable_identity(profile)


if __name__ == "__main__":
    unittest.main()
