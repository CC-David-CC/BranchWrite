"""Opening an existing ledger must not be presented as an empty session."""
import tempfile
import unittest
from pathlib import Path
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput
from branchwrite.interactive_terminal import Terminal

class OpeningService:
    running=False
    snapshot={'status':'starting','history':[],'current':{}}
    def submit(self,*args,**kwargs):
        raise AssertionError('Opening-state control must not be submitted')

class StartupHistoryTests(unittest.TestCase):
    def test_history_does_not_claim_no_saved_turns_before_ledger_is_open(self):
        with tempfile.TemporaryDirectory() as td, create_pipe_input() as pipe:
            terminal=Terminal(OpeningService(),Path(td),input=pipe,output=DummyOutput())
            messages=[];terminal.notify=messages.append
            self.assertTrue(terminal.command('/history'))
            self.assertEqual(messages,['Opening your saved session. Try this command again in a moment.'])
    def test_saved_version_controls_wait_for_authoritative_session_snapshot(self):
        with tempfile.TemporaryDirectory() as td, create_pipe_input() as pipe:
            terminal=Terminal(OpeningService(),Path(td),input=pipe,output=DummyOutput())
            messages=[];terminal.notify=messages.append
            for command in ['/preview','/edit 1 New request','/explore 1 New idea','/switch 1','/continue']:
                self.assertTrue(terminal.command(command))
            self.assertEqual(messages,['Opening your saved session. Try this command again in a moment.']*5)
