"""First-run CLI stays on the existing coding/COW path with project scope and actual checks."""
import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class GuidedCliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.project = self.root / "garden-site"
        (self.project / "src").mkdir(parents=True)
        (self.project / "src" / "main.py").write_text("before\n")
        (self.project / "tests").mkdir()
        (self.project / "tests" / "test_main.py").write_text("test\n")
        self.config_dir = self.home / ".config" / "branchwrite"
        self.config_dir.mkdir(parents=True)
        self.connection = self.config_dir / "connection.json"
        self.connection.write_text(json.dumps({
            "endpoint_url": "http://127.0.0.1:1",
            "endpoint_pin": "local-test",
            "model_contract_id": "model",
            "execution_profile_id": "profile",
            "eos_tokens": [256],
        }))
        self.state_home = self.home / ".local" / "state"
        self.answers = iter([
            "Fix the garden club page and keep it mobile-friendly.",
            "no",  # Keep review/application separate from task admission.
        ])

    def run_wizard(self, *, code=(0, {"verified": True, "status": "complete", "state": ""}), extra_env=None):
        from branchwrite import guided_cli
        env = dict(extra_env or {})
        env.update({
            "HOME": str(self.home),
            "XDG_STATE_HOME": str(self.state_home),
            "BW_COW_CONNECTION": str(self.connection),
            "BW_COW_API_KEY": "temporary-test-key",
        })
        output = io.StringIO()
        with patch("sys.stdin.isatty", return_value=True), \
             patch("branchwrite.guided_cli.input", side_effect=lambda _prompt="": next(self.answers)), \
             patch("branchwrite.guided_cli.coding_start", return_value=code) as start, \
             patch("branchwrite.coding_review.inspect_changes", return_value={"complete_project_patch":True,"changes":[]}), \
             contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            result = guided_cli.run(cwd=self.project, home=self.home, environ=env)
        return result, output.getvalue(), start, env

    def test_guided_start_defaults_to_current_project_and_existing_cow_coding_command(self):
        code, output, start, env = self.run_wizard()
        self.assertEqual(code, 0)
        args = start.call_args.args[0]
        self.assertEqual(args.project, self.project.resolve())
        self.assertEqual(args.task, "Fix the garden club page and keep it mobile-friendly.")
        self.assertEqual(args.read, [])
        self.assertEqual(args.read_dir, [])
        self.assertTrue(args.project_files)
        self.assertEqual(args.edit, [])
        self.assertEqual(args.edit_dir, [])
        self.assertEqual(args.create, [])
        self.assertEqual(args.test_command, [])
        self.assertEqual(args.sampler, "greedy")
        self.assertEqual(args.max_steps, 1024)
        self.assertTrue(args.state.is_relative_to(self.state_home))
        self.assertFalse(args.state.is_relative_to(self.project))
        self.assertTrue(args.branch.startswith("bw-"))
        self.assertIn("original project folder is unchanged", output.lower())
        self.assertIn("saved run", output.lower())
        self.assertEqual(env["BW_COW_API_KEY"], "temporary-test-key")

    def test_start_names_the_client_machine_that_owns_the_project_files(self):
        with patch("socket.gethostname",return_value="llm-49"):
            code,output,start,_=self.run_wizard()
        self.assertEqual(code,0)
        self.assertIn("Client machine: llm-49",output)
        self.assertIn("Project files are on this client machine",output)

    def test_empty_task_starts_no_model_work_and_writes_no_state(self):
        self.answers = iter([
            ""
        ])
        code, output, start, _ = self.run_wizard()
        self.assertEqual(code, 2)
        start.assert_not_called()
        self.assertFalse((self.state_home / "branchwrite" / "runs").exists())
        self.assertIn("enter a task", output.lower())

    def test_missing_api_key_uses_hidden_prompt_and_restores_process_environment(self):
        from branchwrite import guided_cli
        self.answers = iter([
            "Fix the page.", "no"
        ])
        env = {"HOME": str(self.home), "XDG_STATE_HOME": str(self.state_home),
               "BW_COW_CONNECTION": str(self.connection)}
        with patch("sys.stdin.isatty", return_value=True), \
             patch("branchwrite.guided_cli.input", side_effect=lambda _prompt="": next(self.answers)), \
             patch("branchwrite.guided_cli.getpass.getpass", return_value="secret-once") as secret, \
             patch("branchwrite.guided_cli.coding_start", return_value=(1, {"verified": False, "state": "saved"})) as start, \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            code = guided_cli.run(cwd=self.project, home=self.home, environ=env)
        self.assertEqual(code, 1)
        secret.assert_called_once()
        self.assertNotIn("BW_COW_API_KEY", env)
        self.assertEqual(start.call_args.args[0].connection, self.connection)

    def test_verified_result_is_copied_only_after_a_separate_explicit_yes(self):
        from branchwrite import guided_cli
        self.answers = iter([
            "Fix the page.", "yes"
        ])
        env = {"HOME": str(self.home), "XDG_STATE_HOME": str(self.state_home),
               "BW_COW_CONNECTION": str(self.connection), "BW_COW_API_KEY": "test"}
        review = {"complete_project_patch": True, "changes": [{"path": "src/main.py"}]}
        export = {"path": str(self.root / "review.zip"), "sha256": "a" * 64}
        apply = {"path": str(self.root / "garden-site-reviewed"), "original_checkout_modified": False}
        with patch("sys.stdin.isatty", return_value=True), \
             patch("branchwrite.guided_cli.input", side_effect=lambda _prompt="": next(self.answers)), \
             patch("branchwrite.guided_cli.coding_start", return_value=(0, {"verified": True, "state": "unused"})), \
             patch("branchwrite.coding_review.inspect_changes", return_value=review) as inspect, \
             patch("branchwrite.project_export.export_changes", return_value=export) as do_export, \
             patch("branchwrite.project_apply.apply_export", return_value=apply) as do_apply, \
             contextlib.redirect_stdout(io.StringIO()) as output, contextlib.redirect_stderr(io.StringIO()):
            code = guided_cli.run(cwd=self.project, home=self.home, environ=env)
        self.assertEqual(code, 0)
        inspect.assert_called_once()
        do_export.assert_called_once()
        do_apply.assert_called_once()
        self.assertEqual(do_apply.call_args.kwargs["expected_sha256"], "a" * 64)
        self.assertNotEqual(Path(do_apply.call_args.args[2]), self.project)
        self.assertIn("your new copy is here", output.getvalue().lower())

    def test_verified_copy_is_not_attempted_when_independent_verification_failed(self):
        from branchwrite import guided_cli
        self.answers = iter([
            "Fix the page."
        ])
        env = {"HOME": str(self.home), "XDG_STATE_HOME": str(self.state_home),
               "BW_COW_CONNECTION": str(self.connection), "BW_COW_API_KEY": "test"}
        with patch("sys.stdin.isatty", return_value=True), \
             patch("branchwrite.guided_cli.input", side_effect=lambda _prompt="": next(self.answers)), \
             patch("branchwrite.guided_cli.coding_start", return_value=(0, {"verified": False, "state": "saved"})), \
             patch("branchwrite.coding_review.inspect_changes") as inspect, \
             patch("branchwrite.project_export.export_changes") as do_export, \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            code = guided_cli.run(cwd=self.project, home=self.home, environ=env)
        self.assertEqual(code, 3)
        inspect.assert_not_called()
        do_export.assert_not_called()

    def test_interrupt_after_submission_keeps_run_and_does_not_claim_it_was_unsent(self):
        from branchwrite import guided_cli
        self.answers = iter([
            "Fix the page."
        ])
        env = {"HOME": str(self.home), "XDG_STATE_HOME": str(self.state_home),
               "BW_COW_CONNECTION": str(self.connection), "BW_COW_API_KEY": "test"}
        output = io.StringIO()
        with patch("sys.stdin.isatty", return_value=True), \
             patch("branchwrite.guided_cli.input", side_effect=lambda _prompt="": next(self.answers)), \
             patch("branchwrite.guided_cli.coding_start", side_effect=KeyboardInterrupt), \
             contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            code = guided_cli.run(cwd=self.project, home=self.home, environ=env)
        self.assertEqual(code, 130)
        self.assertIn("after submission", output.getvalue())
        self.assertIn("branchwrite status", output.getvalue())
        self.assertNotIn("nothing was sent", output.getvalue().lower())

    def test_malformed_success_cannot_exit_with_success(self):
        code, output, start, _ = self.run_wizard(code=(0, None))
        self.assertEqual(code, 2)
        self.assertIn("without a readable result", output)

    def test_explicit_start_preserves_the_one_task_wizard(self):
        from branchwrite import __main__ as cli
        with patch("branchwrite.guided_cli.run", return_value=0) as run:
            self.assertEqual(cli.main(["start"]), 0)
        run.assert_called_once_with(save_api=False)
