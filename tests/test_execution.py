"""Actual Linux process/filesystem checks for the first registered tool."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from branchwrite.execution import Executor, Grant, ToolRejected


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="bw-exec-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        (self.source / "src").mkdir(parents=True)
        (self.source / "tests").mkdir()
        (self.source / "src/__init__.py").write_bytes(b"")
        (self.source / "tests/__init__.py").write_bytes(b"")
        (self.source / "src/arith.py").write_bytes(b"def add(a, b):\n    return a - b\n")
        (self.source / "tests/test_arith.py").write_bytes(
            b"import unittest\nfrom src.arith import add\n"
            b"class Check(unittest.TestCase):\n"
            b"    def test_add(self): self.assertEqual(add(4, 3), 7)\n")
        self.executor = Executor.create(self.source, self.root / "run")
        self.grant = Grant(edit_paths=("src/arith.py",), allow_tests=True)

    def test_real_test_edit_test_loop_preserves_input_and_protected_tests(self):
        before = self.executor.run_tests("before", self.grant)
        self.assertEqual(before.disposition, "exited")
        self.assertEqual(before.exit_code, 1)
        self.assertIn(b"AssertionError", before.stderr.read_bytes())
        original = (self.source / "src/arith.py").read_bytes()
        patch = self.executor.replace("edit", self.grant, "src/arith.py",
            hashlib.sha256(original).hexdigest(), b"a - b", b"a + b")
        self.assertEqual(patch.disposition, "applied")
        after = self.executor.run_tests("after", self.grant)
        self.assertEqual(after.exit_code, 0)
        self.assertIn(b"OK", after.stderr.read_bytes())
        self.assertEqual((self.source / "src/arith.py").read_bytes(), original)
        self.assertEqual((self.executor.workspace / "tests/test_arith.py").read_bytes(),
                         (self.source / "tests/test_arith.py").read_bytes())

    def test_denied_edit_and_stale_preimage_do_not_change_file(self):
        target = self.executor.workspace / "src/arith.py"
        original = target.read_bytes()
        for grant, path, digest in (
            (Grant((), True), "src/arith.py", hashlib.sha256(original).hexdigest()),
            (self.grant, "tests/test_arith.py", "0" * 64),
            (self.grant, "../source/src/arith.py", "0" * 64),
            (self.grant, "src/arith.py", "0" * 64),
        ):
            with self.assertRaises(ToolRejected):
                self.executor.replace("denied", grant, path, digest, b"a - b", b"a + b")
        self.assertEqual(target.read_bytes(), original)

    def test_process_cannot_modify_protected_tests_or_read_host_sentinel(self):
        sentinel = self.root / "private-sentinel"
        sentinel.write_text("not mounted", encoding="utf-8")
        test = self.source / "tests/test_arith.py"
        test.write_text("import unittest\nfrom pathlib import Path\n"
            "class Boundary(unittest.TestCase):\n"
            "    def test_boundary(self):\n"
            "        with self.assertRaises(OSError): Path('tests/test_arith.py').write_text('changed')\n"
            f"        self.assertFalse(Path({str(sentinel)!r}).exists())\n", encoding="utf-8")
        isolated = Executor.create(self.source, self.root / "boundary-run")
        result = isolated.run_tests("boundary", self.grant)
        self.assertEqual(result.exit_code, 0, result.stderr.read_bytes())
        self.assertEqual((isolated.workspace / "tests/test_arith.py").read_bytes(), test.read_bytes())

    def test_absolute_deadline_stops_owned_process(self):
        (self.source / "tests/test_arith.py").write_text(
            "import unittest,time\nclass Slow(unittest.TestCase):\n"
            "    def test_slow(self): time.sleep(20)\n", encoding="utf-8")
        isolated = Executor.create(self.source, self.root / "slow-run")
        result = isolated.run_tests("slow", self.grant, timeout=0.3)
        self.assertEqual(result.disposition, "timeout")
        self.assertIsNotNone(result.exit_code)
        self.assertLess(result.elapsed_seconds, 5)

    def test_missing_test_grant_rejects_before_process_creation(self):
        with self.assertRaises(ToolRejected):
            self.executor.run_tests("denied", Grant(("src/arith.py",), False))
        # Executor.create owns an empty artifact directory before any action.
        self.assertEqual(list((self.root / "run/artifacts").iterdir()), [])

    def test_symlink_input_is_rejected(self):
        (self.source / "src/link.py").symlink_to(self.source / "src/arith.py")
        with self.assertRaises(ToolRejected):
            Executor.create(self.source, self.root / "unsafe-run")
        self.assertFalse((self.root / "unsafe-run").exists())

    def test_run_directory_collision_is_never_cleaned_up_as_owned(self):
        run_dir = self.root / "raced-run"
        original_mkdir = Path.mkdir

        def create_competing_directory(path, *args, **kwargs):
            if path == run_dir:
                original_mkdir(path, *args, **kwargs)
                (path / "owner-sentinel").write_text("other owner", encoding="utf-8")
                raise FileExistsError(str(path))
            return original_mkdir(path, *args, **kwargs)

        with mock.patch.object(Path, "mkdir", new=create_competing_directory):
            with self.assertRaises(FileExistsError):
                Executor.create(self.source, run_dir)
        self.assertEqual((run_dir / "owner-sentinel").read_text(encoding="utf-8"), "other owner")


if __name__ == "__main__":
    unittest.main()
