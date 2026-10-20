"""Installation must preserve admitted runtimes and publish only a working client."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

class LinuxBootstrapTests(unittest.TestCase):
    def factory(self):
        path=Path(__file__).parents[1]/"tools/bootstrap_client.py"
        spec=importlib.util.spec_from_file_location("bw_bootstrap",path)
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_launcher_resolves_release_before_exec_and_keeps_project_cwd(self):
        module=self.factory()
        with tempfile.TemporaryDirectory(prefix="bw home ' ") as tmp:
            home=Path(tmp)
            release=home/"releases"/"one"
            (release/"venv/bin").mkdir(parents=True)
            python=release/"venv/bin/branchwrite"
            python.write_text("#!/bin/sh\nprintf '%s\\n' \"$PWD\" \"$@\"\n")
            python.chmod(0o700)
            target=module.publish_launcher(home,release,home/"bin")
            result=__import__("subprocess").run([str(target),"hello world"],cwd="/tmp",capture_output=True,text=True,check=True)
            self.assertEqual(result.stdout.splitlines(),["/tmp","hello world"])
            self.assertEqual(target.stat().st_mode&0o777,0o700)

    def test_failed_release_does_not_replace_existing_launcher(self):
        module=self.factory()
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp)
            (home/"bin").mkdir()
            old=home/"bin/bw"
            old.write_text("existing launcher")
            with self.assertRaises(ValueError):
                module.publish_launcher(home,home/"missing",home/"bin")
            self.assertEqual(old.read_text(),"existing launcher")
