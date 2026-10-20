"""User-visible results must preserve the task answer and current controller state."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from branchwrite import guided_cli
from branchwrite.records import RuntimeLog, encode
from branchwrite.kernel import FrameKernel, ResultContract
import test_guided_conversation as conversation_tests
from collections import defaultdict

class OutcomeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.state = self.root / "run"
    def finish(self, text, verified=True):
        with RuntimeLog(self.state / "ledger") as log:
            kernel = FrameKernel(log)
            ref = log.put_artifact(text.encode())
            kernel.create_root("program", "attempt", log.put_artifact(b"program"),
                log.put_artifact(encode({})), ResultContract("ProgramResult", "record"))
            kernel.finish("program", {"schema": 1, "verified": verified, "bindings": {
                "outcome": ("ToolOutcome", {"tool": "finish", "requested_finish": True,
                    "stdout": (ref.sha256, ref.size_bytes)})}})
    def test_checks_cannot_hide_the_actual_not_done_answer(self):
        answer = "Not done. SSH failed. The file was NOT copied."
        self.finish(answer)
        before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in self.state.rglob("*") if p.is_file()}
        output = []
        with patch("branchwrite.coding_review.inspect_changes", return_value={"complete_project_patch":True,"changes":[]}):
            guided_cli._verified_summary(0, {"verified":True}, project=self.root,
                state=self.state, branch="bw-task-123", runs_dir=self.root,
                input_fn=lambda _: self.fail("no copy prompt without changes"), output_fn=output.append)
        self.assertIn(answer, "\n".join(output))
        self.assertIn("not independent acceptance", "\n".join(output).lower())
        self.assertEqual(before, {p:hashlib.sha256(p.read_bytes()).hexdigest() for p in before})
    def test_failed_checks_still_show_the_final_explanation(self):
        self.finish("A dependency is unavailable; here is what remains.", False)
        output=[]
        code=guided_cli._verified_summary(3, {"verified":False}, project=self.root,
            state=self.state, branch="bw-task-123", runs_dir=self.root,
            input_fn=lambda _: self.fail("no prompt"), output_fn=output.append)
        self.assertEqual(code,3)
        self.assertIn("A dependency is unavailable", "\n".join(output))
    def test_terminal_controls_from_model_are_rendered_as_text(self):
        self.finish("Result: \x1b[2Jhidden\x00")
        from branchwrite.run_report import read_report, terminal_text
        report=read_report(self.state)
        self.assertEqual(report["answer"], "Result: \x1b[2Jhidden\x00")
        text=terminal_text(report["answer"])
        self.assertNotIn("\x1b",text); self.assertNotIn("\x00",text)
        self.assertIn("hidden",text)

    def test_initial_context_reads_the_saved_request_boundary_without_writes(self):
        head=dict(name='prepared',tip='a'*64,root='b'*64,revision=3)
        with RuntimeLog(self.state/'ledger') as log:
            kernel=FrameKernel(log)
            kernel.create_root('program','attempt',log.put_artifact(b'program'),
                log.put_artifact(encode(dict(bindings={'current':('COWSource',dict(head=head,mode='ask'))}))),
                ResultContract('ProgramResult','record'))
        before={p:p.read_bytes() for p in self.state.rglob('*') if p.is_file()}
        from branchwrite.run_report import initial_context
        context=initial_context(self.state,dict(model_contract_id='model',execution_profile_id='profile'))
        self.assertEqual(context,dict(branch='prepared',tip='a'*64,root='b'*64,revision=3,
            model_contract_id='model',execution_profile_id='profile',mode='ask'))
        self.assertEqual(before,{p:p.read_bytes() for p in before})

class ControllerNoticeTests(unittest.TestCase):
    setUp=conversation_tests.GuidedConversationTests.setUp
    run_chat=conversation_tests.GuidedConversationTests.run_chat
    chat_state=conversation_tests.GuidedConversationTests.chat_state
    def test_continue_and_reconcile_repeat_the_current_paused_notice(self):
        self.model.plans=defaultdict(lambda:(257,))
        code,out,coding=self.run_chat(["Explain this.","/continue","/reconcile","/exit"],mode="chat")
        self.assertEqual(code,0,out); coding.assert_not_called()
        self.assertEqual(out.count("answer is paused at its token budget"),3,out)
    def test_eof_at_code_prompt_preserves_the_existing_conversation(self):
        self.run_chat(["We already talked.","/exit"],mode="chat")
        state=self.chat_state(); output=[]; answers=iter(["/code"])
        def answer(prompt):
            try:return next(answers)
            except StopIteration:raise EOFError
        code=guided_cli.run(cwd=self.project,home=self.home,environ=self.env,
            input_fn=answer,output_fn=output.append,mode="chat",chat_state=state)
        self.assertEqual(code,0,output)
        self.assertNotIn("Nothing was sent", "\n".join(output))
        self.assertIn("Resume this conversation", "\n".join(output))
