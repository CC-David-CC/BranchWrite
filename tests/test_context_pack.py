from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from branchwrite import context_pack as cp

class ContextPackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / "approved"
        self.root.mkdir()
        self.out = self.base / "packs"
        (self.root / "examples").mkdir()
        (self.root / "examples" / "a.txt").write_text("Example: report exit 7 honestly.\n", encoding="utf-8")
        (self.root / "facts").mkdir()
        (self.root / "facts" / "host.txt").write_text("Recorded host: training-box.\n", encoding="utf-8")

    def build(self, **kw):
        options = dict(root=self.root, examples=["examples"], facts=["facts"],
                       output=self.out, as_of="2026-10-18T12:00:00Z")
        options.update(kw)
        return cp.build_pack(**options)

    def path(self, receipt):
        return self.out / receipt["pack_id"]

    def test_stable_identity_excludes_capture_clock_and_mtime(self):
        first = self.build()
        os.utime(self.root / "examples" / "a.txt", (1_000_000_000, 1_000_000_000))
        with mock.patch.object(cp, "_captured_at", return_value="2099-01-01T00:00:00Z"):
            second = self.build()
        self.assertEqual(first["pack_id"], second["pack_id"])
        self.assertEqual(second["status"], "reused")
        self.assertEqual(first["captured_at"], second["captured_at"])
        self.assertEqual(cp.verify_pack(self.path(first))["status"], "fresh")

    def test_same_text_at_different_paths_has_distinct_identity(self):
        first = self.build()
        old = self.root / "examples" / "a.txt"
        old.rename(old.with_name("b.txt"))
        second = self.build()
        self.assertNotEqual(first["pack_id"], second["pack_id"])

    def test_sections_and_as_of_are_part_of_identity(self):
        first = self.build()
        second = self.build(examples=["facts"], facts=["examples"])
        third = self.build(as_of="2026-10-19T12:00:00Z")
        self.assertEqual(len({first["pack_id"], second["pack_id"], third["pack_id"]}), 3)

    def test_sections_provenance_and_no_authority_warning(self):
        result = self.build()
        prefix = cp.load_verified_prefix(self.path(result))
        self.assertIn("WORKED EXAMPLES", prefix)
        self.assertIn("RECORDED ENVIRONMENT FACTS", prefix)
        self.assertIn("not live observation", prefix)
        self.assertIn("does not grant", prefix)
        self.assertIn("2026-10-18T12:00:00Z", prefix)
        self.assertIn("training-box", prefix)

    def test_addition_modification_deletion_are_stale_and_old_pack_retained(self):
        old = self.build()
        old_path = self.path(old)
        snapshot = {p.name: p.read_bytes() for p in old_path.iterdir()}
        (self.root / "examples" / "new.txt").write_text("new", encoding="utf-8")
        changed = self.root / "examples" / "a.txt"
        changed.write_text("changed", encoding="utf-8")
        (self.root / "facts" / "host.txt").unlink()
        check = cp.verify_pack(old_path)
        self.assertEqual(check["status"], "stale")
        self.assertEqual({x["kind"] for x in check["changes"]}, {"added", "modified", "deleted"})
        with self.assertRaises(cp.StalePackError):
            cp.load_verified_prefix(old_path)
        newer = self.build()
        self.assertNotEqual(old["pack_id"], newer["pack_id"])
        self.assertEqual(snapshot, {p.name: p.read_bytes() for p in old_path.iterdir()})

    def test_explicit_file_selection_does_not_crawl_siblings(self):
        receipt = self.build(examples=["examples/a.txt"], facts=[])
        (self.root / "unselected-secret.txt").write_bytes(b"\xff")
        self.assertEqual(cp.verify_pack(self.path(receipt))["status"], "fresh")
        self.assertEqual(receipt["source_files"], 1)

    def test_absolute_and_parent_selections_rejected(self):
        for selection in ["../outside.txt", str(self.root / "examples/a.txt")]:
            with self.subTest(selection=selection), self.assertRaises(cp.SourceError):
                self.build(examples=[selection])

    def test_file_directory_and_root_symlinks_rejected(self):
        for name, target in [("file-link", self.root/"examples/a.txt"), ("dir-link", self.root/"examples")]:
            link = self.root / "facts" / name
            link.symlink_to(target)
            with self.subTest(name=name), self.assertRaises(cp.SourceError):
                self.build()
            link.unlink()
        alias = self.base / "root-alias"
        alias.symlink_to(self.root)
        with self.assertRaises(cp.SourceError):
            self.build(root=alias)

    def test_invalid_utf8_rejected_without_partial_pack(self):
        (self.root / "examples" / "bad.txt").write_bytes(b"bad\xff")
        with self.assertRaises(cp.SourceError):
            self.build()
        self.assertFalse(self.out.exists())

    def test_nonregular_file_rejected_without_opening_fifo(self):
        os.mkfifo(self.root / "examples" / "pipe")
        with self.assertRaises(cp.SourceError):
            self.build()

    def test_each_limit_fails_without_truncation(self):
        cases = [
            cp.Limits(max_files=1),
            cp.Limits(max_file_bytes=2),
            cp.Limits(max_total_bytes=2),
        ]
        for limits in cases:
            with self.subTest(limits=limits), self.assertRaises(cp.SourceError):
                self.build(limits=limits)
        self.assertFalse(self.out.exists())

    def test_duplicate_overlapping_selection_deduplicated_but_cross_section_rejected(self):
        result = self.build(examples=["examples", "examples/a.txt"])
        self.assertEqual(result["source_files"], 2)
        with self.assertRaises(cp.SourceError):
            self.build(facts=["examples/a.txt"])

    def test_output_under_source_root_rejected(self):
        with self.assertRaises(cp.SourceError):
            self.build(output=self.root / "packs")

    def test_read_mutation_rejected(self):
        original = cp._read_source_file
        changed = False
        def race(path, limit):
            nonlocal changed
            value = original(path, limit)
            if not changed:
                changed = True
                (self.root/"examples"/"late.txt").write_text("changed during capture", encoding="utf-8")
            return value
        with mock.patch.object(cp, "_read_source_file", side_effect=race):
            with self.assertRaises(cp.SourceChangedError):
                self.build()

    def test_file_mutation_inside_read_detected(self):
        target = self.root / "examples" / "a.txt"
        real_read = os.read
        touched = False
        def racing_read(fd, size):
            nonlocal touched
            data = real_read(fd, size)
            if not touched and data:
                touched = True
                with target.open("ab") as stream:
                    stream.write(b"mutation")
            return data
        with mock.patch.object(cp.os, "read", side_effect=racing_read):
            with self.assertRaises(cp.SourceChangedError):
                self.build(examples=["examples/a.txt"], facts=[])

    def test_pack_payload_corruption_rejected(self):
        result = self.build()
        path = self.path(result) / "prefix.txt"
        path.chmod(0o600)
        path.write_text("wrong", encoding="utf-8")
        with self.assertRaises(cp.PackError):
            cp.verify_pack(self.path(result))

    def test_manifest_corruption_rejected(self):
        result = self.build()
        path = self.path(result) / "manifest.json"
        path.chmod(0o600)
        data = json.loads(path.read_text())
        data["identity"]["as_of"] = "2099-01-01T00:00:00Z"
        path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(cp.PackError):
            cp.verify_pack(self.path(result))

    def test_source_failure_becomes_explicit_stale_status(self):
        result = self.build()
        (self.root/"facts"/"host.txt").write_bytes(b"\xff")
        check = cp.verify_pack(self.path(result))
        self.assertEqual(check["status"], "stale")
        self.assertIn("UTF-8", check["reason"])

    def test_cli_build_and_stale_verify_exit_codes(self):
        argv = [sys.executable, "-B", "-m", "branchwrite.context_pack"]
        built = subprocess.run(argv + ["build", "--root", str(self.root), "--examples", "examples",
            "--facts", "facts", "--output", str(self.out), "--as-of", "2026-10-18T12:00:00Z"],
            capture_output=True, text=True)
        self.assertEqual(built.returncode, 0, built.stderr)
        receipt = json.loads(built.stdout)
        okay = subprocess.run(argv + ["verify", str(self.path(receipt))], capture_output=True, text=True)
        self.assertEqual(okay.returncode, 0, okay.stderr)
        (self.root/"facts"/"host.txt").unlink()
        stale = subprocess.run(argv + ["verify", str(self.path(receipt))], capture_output=True, text=True)
        self.assertEqual(stale.returncode, 2)
        self.assertEqual(json.loads(stale.stdout)["status"], "stale")

    def test_large_text_pack_exact_bytes_and_freshness(self):
        text = "An independent worked example with Unicode \u0394 and exit status.\n" * 10000
        (self.root/"examples"/"large.txt").write_text(text, encoding="utf-8")
        result = self.build()
        self.assertTrue(any(ord(char) > 127 for char in text))
        self.assertGreater(len(text.encode("utf-8")), len(text))
        self.assertGreater(result["source_bytes"], 500_000)
        prefix = cp.load_verified_prefix(self.path(result))
        self.assertIn(text, prefix)
        self.assertEqual(cp.verify_pack(self.path(result))["status"], "fresh")


    def test_selection_order_does_not_churn_identity(self):
        (self.root/"examples"/"b.txt").write_text("other", encoding="utf-8")
        first = self.build(examples=["examples/b.txt", "examples/a.txt"])
        second = self.build(examples=["examples/a.txt", "examples/b.txt"])
        self.assertEqual(first["pack_id"], second["pack_id"])

    def test_unzoned_asof_and_accidental_string_selector_rejected(self):
        for kw in ({"as_of": "2026-10-18"}, {"examples": "examples"}):
            with self.subTest(kw=kw), self.assertRaises(cp.SourceError):
                self.build(**kw)

    def test_output_symlink_is_rejected(self):
        elsewhere = self.base/"elsewhere"
        elsewhere.mkdir()
        self.out.symlink_to(elsewhere)
        with self.assertRaises(cp.SourceError):
            self.build()
        self.assertEqual(list(elsewhere.iterdir()), [])

    def test_failed_publication_has_no_partial_visible_pack(self):
        real_write = cp._write_durable
        count = 0
        def fail_second(path, payload):
            nonlocal count
            count += 1
            if count == 2:
                raise OSError(28, "No space left on device")
            return real_write(path, payload)
        with mock.patch.object(cp, "_write_durable", side_effect=fail_second):
            with self.assertRaises(cp.PackError):
                self.build()
        self.assertEqual(list(self.out.iterdir()), [])
        self.assertEqual(self.build()["status"], "built")

    def test_rechecks_identity_schema_even_with_updated_manifest_checksum(self):
        result = self.build()
        directory = self.path(result)
        manifest = directory/"manifest.json"
        data = json.loads(manifest.read_text())
        data["identity"]["selections"][0]["path"] = "../unapproved"
        data["pack_id"] = hashlib.sha256(cp._json(data["identity"])).hexdigest()
        altered = cp._json(data) + b"\n"
        manifest.chmod(0o600)
        manifest.write_bytes(altered)
        checksum = directory/"manifest.sha256"
        checksum.chmod(0o600)
        checksum.write_text(hashlib.sha256(altered).hexdigest()+"\n", encoding="ascii")
        newer = directory.with_name(data["pack_id"])
        directory.rename(newer)
        with self.assertRaises(cp.PackError):
            cp.verify_pack(newer)

    def test_missing_root_explicitly_stale(self):
        result = self.build()
        self.root.rename(self.root.with_name("moved"))
        self.assertEqual(cp.verify_pack(self.path(result))["status"], "stale")
        with self.assertRaises(cp.StalePackError):
            cp.load_verified_prefix(self.path(result))


    def test_load_can_pin_expected_identity(self):
        result = self.build()
        prefix = cp.load_verified_prefix(self.path(result), expected_id=result["pack_id"])
        self.assertIn("training-box", prefix)
        with mock.patch.object(cp, "_verify_sources", side_effect=AssertionError("must reject pin first")):
            with self.assertRaises(cp.PackError):
                cp.load_verified_prefix(self.path(result), expected_id="0"*64)

    def test_load_returns_the_same_bytes_that_were_integrity_checked(self):
        result = self.build()
        directory = self.path(result)
        expected = (directory/"prefix.txt").read_text(encoding="utf-8")
        original = cp._verify_sources
        def replace_after_read(manifest, pack_path):
            path = directory/"prefix.txt"
            path.chmod(0o600)
            path.write_text("replaced after validation", encoding="utf-8")
            return original(manifest, pack_path)
        with mock.patch.object(cp, "_verify_sources", side_effect=replace_after_read):
            actual = cp.load_verified_prefix(directory, expected_id=result["pack_id"])
        self.assertEqual(actual, expected)
        with self.assertRaises(cp.PackError):
            cp.verify_pack(directory)


    def test_unicode_normalization_is_not_silently_applied(self):
        path = self.root/"examples"/"accent.txt"
        path.write_text(chr(0xe9), encoding="utf-8")
        first = self.build()
        path.write_text("e"+chr(0x301), encoding="utf-8")
        second = self.build()
        self.assertNotEqual(first["pack_id"], second["pack_id"])
        self.assertEqual(cp.verify_pack(self.path(first))["status"], "stale")

    def test_four_byte_unicode_and_no_final_newline_are_retained(self):
        text = chr(0x1f42e)+" "+chr(0x394)
        path = self.root/"examples"/"emoji.txt"
        path.write_text(text, encoding="utf-8")
        result = self.build(examples=["examples/emoji.txt"], facts=[])
        self.assertEqual(result["source_bytes"], len(text.encode("utf-8")))
        self.assertEqual(result["source_bytes"], 7)
        self.assertIn(text, cp.load_verified_prefix(self.path(result)))

if __name__ == "__main__":
    unittest.main()
