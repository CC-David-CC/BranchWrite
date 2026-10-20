"""Real client-side Chromium and filesystem checks; no model or mock screenshots."""
import hashlib
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib
import unittest
from unittest.mock import patch

from branchwrite.execution import Executor, Grant, ToolRejected


PAGE = (b'<!doctype html><meta charset="utf-8"><style>body{margin:0;background:white}'
        b'.square{position:absolute;top:80px;left:64px;width:80px;height:80px;'
        b'background:#16a34a}</style><div class="square"></div>')


class BrowserCaptureTests(unittest.TestCase):
    def setUp(self):
        from branchwrite.browser_capture import BrowserConfig
        self.temp = tempfile.TemporaryDirectory(prefix="bw-browser-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        (self.source / "index.html").write_bytes(PAGE)
        self.config = BrowserConfig(executable=Path(os.environ["BW_BROWSER_EXECUTABLE"]))
        self.executor = Executor.create(self.source, self.root / "run", browser=self.config)
        self.grant = Grant((), False, capture_paths=("index.html",))
        self.sha = hashlib.sha256(PAGE).hexdigest()

    def capture(self, *, grant=None, digest=None):
        return self.executor.capture_page("capture", grant or self.grant, "index.html", digest or self.sha)

    def test_real_page_pixels_and_bound_source(self):
        from PIL import Image
        result = self.capture()
        self.assertEqual(result.source.read_bytes(), PAGE)
        self.assertEqual(result.source.sha256, self.sha)
        self.assertEqual(result.served_sha256, self.sha)
        self.assertEqual(result.viewport, (640, 480))
        self.assertEqual(result.source_path, "index.html")
        self.assertTrue(result.chromium_sandbox)
        self.assertTrue(result.browser_version)
        self.assertEqual(result.http_status, 200)
        self.assertTrue(result.url.startswith("http://127.0.0.1:"))
        with Image.open(io.BytesIO(result.image.read_bytes())) as image:
            self.assertEqual((image.format, image.size), ("PNG", (640, 480)))
            rgb = image.convert("RGB")
            self.assertEqual(rgb.getpixel((64, 80)), (22, 163, 74))
            self.assertEqual(rgb.getpixel((143, 159)), (22, 163, 74))
            self.assertEqual(rgb.getpixel((144, 160)), (255, 255, 255))
        self.assertEqual((self.source / "index.html").read_bytes(), PAGE)
        self.assertEqual((self.executor.workspace / "index.html").read_bytes(), PAGE)

    def test_read_or_edit_permission_is_not_capture_permission(self):
        with patch("branchwrite.browser_capture.render_snapshot") as render:
            with self.assertRaises(ToolRejected):
                self.capture(grant=Grant(("index.html",), True, read_paths=("index.html",)))
        render.assert_not_called()
        self.assertEqual(list(self.executor.artifacts.iterdir()), [])

    def test_stale_revision_rejects_before_browser_launch(self):
        with patch("branchwrite.browser_capture.render_snapshot") as render:
            with self.assertRaisesRegex(ToolRejected, "stale"):
                self.capture(digest="0" * 64)
        render.assert_not_called()
        self.assertEqual(list(self.executor.artifacts.iterdir()), [])

    def test_symlink_cannot_be_rendered(self):
        target = self.executor.workspace / "index.html"
        target.unlink()
        target.symlink_to(self.source / "index.html")
        with patch("branchwrite.browser_capture.render_snapshot") as render:
            with self.assertRaises(ToolRejected):
                self.capture()
        render.assert_not_called()

    def test_bad_configuration_does_not_disable_sandbox(self):
        from branchwrite.browser_capture import BrowserConfig
        for kwargs in ({"width": 0}, {"height": True}, {"timeout": float("nan")},
                       {"timeout": 0}, {"width": 10000}, {"executable": Path("relative")}):
            arguments = dict(executable=self.config.executable)
            arguments.update(kwargs)
            with self.assertRaises(ValueError):
                BrowserConfig(**arguments)

    def test_missing_browser_fails_without_capture(self):
        from branchwrite.browser_capture import BrowserConfig
        other = Executor.create(self.source, self.root / "other", browser=BrowserConfig(
            executable=self.root / "missing-chromium"))
        with self.assertRaises(ToolRejected):
            other.capture_page("missing", self.grant, "index.html", self.sha)
        self.assertEqual(list(other.artifacts.iterdir()), [])

    def test_external_resource_is_blocked_and_not_silently_accepted(self):
        payload = PAGE + b'<img src="https://example.invalid/forbidden.png">'
        (self.executor.workspace / "index.html").write_bytes(payload)
        with self.assertRaisesRegex(ToolRejected, "resource"):
            self.capture(digest=hashlib.sha256(payload).hexdigest())
        self.assertEqual(list(self.executor.artifacts.iterdir()), [])

    def test_javascript_failure_is_not_a_capture_pass(self):
        payload = PAGE + b'<script>throw new Error("intentional page failure")</script>'
        (self.executor.workspace / "index.html").write_bytes(payload)
        with self.assertRaisesRegex(ToolRejected, "page"):
            self.capture(digest=hashlib.sha256(payload).hexdigest())
        self.assertEqual(list(self.executor.artifacts.iterdir()), [])

    def test_cli_returns_the_actual_image_and_source_receipt(self):
        root = Path(__file__).resolve().parents[1]
        output = self.root / "cli-capture"
        observed = subprocess.run([sys.executable, "-B", str(root / "tools/capture_page.py"),
            "--source", str(self.source), "--entry", "index.html", "--expected-sha256", self.sha,
            "--browser", str(self.config.executable), "--output", str(output)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30, check=False)
        self.assertEqual(observed.returncode, 0, observed.stderr.decode())
        receipt = tomllib.loads(observed.stdout.decode())
        self.assertEqual(receipt, tomllib.loads((output / "capture.toml").read_text()))
        self.assertEqual(receipt["source_sha256"], self.sha)
        self.assertEqual(receipt["served_sha256"], self.sha)
        self.assertEqual(receipt["image_sha256"], hashlib.sha256((output / "capture.png").read_bytes()).hexdigest())
        self.assertEqual((receipt["width"], receipt["height"]), (640, 480))
        self.assertTrue(receipt["chromium_sandbox"])


if __name__ == "__main__":
    unittest.main()
