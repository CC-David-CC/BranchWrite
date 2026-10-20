"""Ordinary branchwrite launches the steerable current-directory session."""
from pathlib import Path
import unittest
from unittest.mock import patch

class DefaultSessionCliTests(unittest.TestCase):
    def invoke(self,args):
        from branchwrite.__main__ import main
        with patch('branchwrite.interactive_cli.run',return_value=130) as interactive, \
             patch('branchwrite.guided_cli.run',return_value=0) as wizard:
            code=main(args)
        return code,interactive,wizard

    def test_no_arguments_opens_interactive_current_directory_without_saving_key(self):
        code,interactive,wizard=self.invoke([])
        self.assertEqual(code,130)
        interactive.assert_called_once_with(project=Path.cwd(),state=None,save_api=False)
        wizard.assert_not_called()

    def test_save_api_shorthand_keeps_interactive_session_and_requires_explicit_flag(self):
        code,interactive,wizard=self.invoke(['--save-api'])
        self.assertEqual(code,130)
        interactive.assert_called_once_with(project=Path.cwd(),state=None,save_api=True)
        wizard.assert_not_called()

    def test_explicit_saved_session_keeps_exact_project_and_state(self):
        code,interactive,wizard=self.invoke(['session','/tmp/my-project','--state','/tmp/my-saved-session'])
        self.assertEqual(code,130)
        interactive.assert_called_once_with(project=Path('/tmp/my-project'),state=Path('/tmp/my-saved-session'),save_api=False)
        wizard.assert_not_called()

    def test_explicit_sampler_and_shorthand_reach_interactive_launcher(self):
        for args in [['session','--sampler','min-p'],['--sampler','min-p']]:
            with self.subTest(args=args):
                code,interactive,wizard=self.invoke(args)
                self.assertEqual(code,130)
                interactive.assert_called_once_with(project=Path.cwd(),state=None,save_api=False,sampler='min-p')
                wizard.assert_not_called()
