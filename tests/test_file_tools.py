"""Real Linux filesystem checks for the H00 host create/read boundary."""
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from branchwrite.execution import Executor, Grant, ToolRejected, _MAX_FILE_BYTES


class FileToolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="bw-file-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        (self.source / "sub").mkdir(parents=True)
        self.executor = Executor.create(self.source, self.root / "run")
        self.grant = Grant((), False, create_paths=("hello.txt", "sub/hello.txt"),
                           read_paths=("hello.txt", "sub/hello.txt"))

    def test_create_and_read_exact_bytes_with_separate_artifacts(self):
        payload = b"Hello, loop.\n"
        created = self.executor.create_file("create", self.grant, "hello.txt", payload)
        self.assertEqual((created.disposition, created.exit_code), ("created", 0))
        self.assertEqual((self.executor.workspace / "hello.txt").read_bytes(), payload)
        read = self.executor.read_file("read", self.grant, "hello.txt")
        self.assertEqual((read.disposition, read.exit_code), ("read", 0))
        self.assertEqual(read.stdout.read_bytes(), payload)
        self.assertEqual(read.stdout.sha256, hashlib.sha256(payload).hexdigest())
        self.assertEqual(read.stderr.read_bytes(), b"")
        self.assertFalse((self.source / "hello.txt").exists())
        self.assertNotEqual(created.stdout.path, read.stdout.path)

    def test_nested_file_and_empty_payload(self):
        self.executor.create_file("create", self.grant, "sub/hello.txt", b"")
        self.assertEqual(self.executor.read_file("read", self.grant,
                                              "sub/hello.txt").stdout.read_bytes(), b"")

    def test_grants_are_separate_and_reject_before_effects(self):
        target = self.executor.workspace / "hello.txt"
        target.write_bytes(b"existing")
        for grant in (Grant(("hello.txt",), True),
                      Grant((), False, read_paths=("hello.txt",)), None):
            with self.assertRaises(ToolRejected):
                self.executor.create_file("denied", grant, "hello.txt", b"new")
        for grant in (Grant(("hello.txt",), True),
                      Grant((), False, create_paths=("hello.txt",)), None):
            with self.assertRaises(ToolRejected):
                self.executor.read_file("denied", grant, "hello.txt")
        self.assertEqual(target.read_bytes(), b"existing")
        self.assertEqual(list(self.executor.artifacts.iterdir()), [])

    def test_existing_target_is_never_overwritten(self):
        target = self.executor.workspace / "hello.txt"
        target.write_bytes(b"first owner")
        with self.assertRaises(ToolRejected):
            self.executor.create_file("collision", self.grant, "hello.txt", b"second")
        self.assertEqual(target.read_bytes(), b"first owner")
        self.assertEqual(sorted(p.name for p in target.parent.iterdir()), ["hello.txt", "sub"])
        self.assertEqual(list(self.executor.artifacts.iterdir()), [])

    def test_symlink_leaf_and_parent_cannot_escape(self):
        outside = self.root / "outside"
        outside.mkdir()
        sentinel = outside / "hello.txt"
        sentinel.write_bytes(b"outside")
        (self.executor.workspace / "hello.txt").symlink_to(sentinel)
        (self.executor.workspace / "sub").rmdir()
        (self.executor.workspace / "sub").symlink_to(outside, target_is_directory=True)
        for path in ("hello.txt", "sub/hello.txt"):
            with self.subTest(path=path):
                with self.assertRaises(ToolRejected):
                    self.executor.create_file("create", self.grant, path, b"changed")
                with self.assertRaises(ToolRejected):
                    self.executor.read_file("read", self.grant, path)
        self.assertEqual(sentinel.read_bytes(), b"outside")
        self.assertEqual(list(self.executor.artifacts.iterdir()), [])

    def test_hardlink_is_not_a_private_read_target(self):
        outside = self.root / "private"
        outside.write_bytes(b"private")
        os.link(outside, self.executor.workspace / "hello.txt")
        with self.assertRaises(ToolRejected):
            self.executor.read_file("read", self.grant, "hello.txt")
        self.assertEqual(list(self.executor.artifacts.iterdir()), [])

    def test_directory_fifo_missing_and_oversize_reads_reject(self):
        target = self.executor.workspace / "hello.txt"
        with self.assertRaises(ToolRejected):
            self.executor.read_file("read", self.grant, "hello.txt")
        target.mkdir()
        with self.assertRaises(ToolRejected):
            self.executor.read_file("read", self.grant, "hello.txt")
        target.rmdir()
        os.mkfifo(target)
        with self.assertRaises(ToolRejected):
            self.executor.read_file("read", self.grant, "hello.txt")
        target.unlink()
        with target.open("wb") as stream:
            stream.truncate(_MAX_FILE_BYTES + 1)
        with self.assertRaises(ToolRejected):
            self.executor.read_file("read", self.grant, "hello.txt")
        self.assertEqual(list(self.executor.artifacts.iterdir()), [])

    def test_bad_payloads_paths_and_ids_reject_without_creation(self):
        for payload in ("text", bytearray(b"text"), b"x" * (_MAX_FILE_BYTES + 1)):
            with self.assertRaises(ToolRejected):
                self.executor.create_file("create", self.grant, "hello.txt", payload)
        for path in ("../outside", "/tmp/outside", "./hello.txt", "sub//hello.txt"):
            with self.assertRaises(ToolRejected):
                self.executor.create_file("create", self.grant, path, b"text")
        for operation_id in ("", "bad\nname", "x" * 129):
            with self.assertRaises(ToolRejected):
                self.executor.create_file(operation_id, self.grant, "hello.txt", b"text")
        self.assertFalse((self.executor.workspace / "hello.txt").exists())
        self.assertEqual(list(self.executor.artifacts.iterdir()), [])

    def test_grant_validation_and_legacy_defaults(self):
        legacy = Grant(("hello.txt",), True)
        self.assertEqual((legacy.create_paths, legacy.read_paths), ((), ()))
        for field in ("create_paths", "read_paths"):
            for paths in ("hello.txt", ("../outside",), ("hello.txt", "hello.txt"), None):
                with self.subTest(field=field, paths=paths):
                    with self.assertRaises(ToolRejected):
                        Grant((), False, **{field: paths})

    def test_failed_write_leaves_no_target_or_temporary_file(self):
        with mock.patch("branchwrite.execution.os.fsync", side_effect=OSError("injected fsync")):
            with self.assertRaises(OSError):
                self.executor.create_file("create", self.grant, "hello.txt", b"data")
        self.assertEqual(sorted(p.name for p in self.executor.workspace.iterdir()), ["sub"])
        self.assertEqual(list(self.executor.artifacts.iterdir()), [])

    def test_competing_create_does_not_overwrite_other_owner(self):
        original_link = os.link
        target = self.executor.workspace / "hello.txt"

        def race_link(*args, **kwargs):
            target.write_bytes(b"other owner")
            return original_link(*args, **kwargs)

        with mock.patch("branchwrite.execution.os.link", side_effect=race_link):
            with self.assertRaises(ToolRejected):
                self.executor.create_file("create", self.grant, "hello.txt", b"ours")
        self.assertEqual(target.read_bytes(), b"other owner")
        self.assertEqual(sorted(p.name for p in target.parent.iterdir()), ["hello.txt", "sub"])

    def test_changed_read_is_not_published_as_stable_content(self):
        target = self.executor.workspace / "hello.txt"
        target.write_bytes(b"before")
        original_read = os.read

        def race_read(fd, count):
            data = original_read(fd, count)
            target.write_bytes(b"changed and longer")
            return data

        with mock.patch("branchwrite.execution.os.read", side_effect=race_read):
            with self.assertRaises(ToolRejected):
                self.executor.read_file("read", self.grant, "hello.txt")
        self.assertEqual(list(self.executor.artifacts.iterdir()), [])

    def test_replaced_workspace_root_rejects_read_and_create(self):
        moved = self.root / "owned-workspace"
        self.executor.workspace.rename(moved)
        self.executor.workspace.mkdir()
        (self.executor.workspace / "hello.txt").write_bytes(b"replacement owner")
        with self.assertRaises(ToolRejected):
            self.executor.read_file("read", self.grant, "hello.txt")
        with self.assertRaises(ToolRejected):
            self.executor.create_file("create", self.grant, "sub/hello.txt", b"ours")
        self.assertEqual(list(self.executor.artifacts.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
