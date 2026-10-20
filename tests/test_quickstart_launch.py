"""Common first-run mistakes should explain the next action before connection."""
import contextlib
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

class QuickstartLaunchTests(unittest.TestCase):
    def test_home_folder_explains_project_folder_before_connection(self):
        from branchwrite.interactive_cli import run
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp)
            output=io.StringIO()
            with patch("sys.stdin.isatty",return_value=True),patch("pathlib.Path.home",return_value=home),patch.dict(os.environ,{},clear=True),patch("branchwrite.interactive_cli.connection_path",side_effect=AssertionError("connection must not start")),contextlib.redirect_stdout(output):
                result=run(project=home)
            self.assertEqual(result,2)
            self.assertIn("Choose a project folder",output.getvalue())
            self.assertIn("mkdir -p",output.getvalue())
            self.assertNotIn("Traceback",output.getvalue())
