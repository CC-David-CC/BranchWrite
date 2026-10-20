"""Real binary HTTP and CLI argument binding; CPU fixtures, not GPU evidence."""
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from branchwrite.cow_client import CowClient, OperationJournal, ReceiptError, _Response


class CowImageTests(unittest.TestCase):
    def setUp(self):
        from PIL import Image
        self.temp = tempfile.TemporaryDirectory(prefix="bw-image-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        data = io.BytesIO()
        Image.new("RGB", (7, 3), "green").save(data, format="PNG")
        self.raw = data.getvalue()
        self.namespace = "a" * 32
        self.requests = []
        self.bad_ack = False
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                data = self.rfile.read(int(self.headers["Content-Length"]))
                owner.requests.append((self.path, dict(self.headers), data))
                if self.path.startswith("/cow/images?"):
                    value = dict(namespace_id=owner.namespace,
                        image_id="0" * 64 if owner.bad_ack else hashlib.sha256(data).hexdigest(),
                        bytes=len(data), expires_ns=9999999999999999999,
                        width=7, height=3, media_type="image/png")
                    output = json.dumps(value).encode()
                else:
                    body = json.loads(data)
                    receipt = dict(operation_id=body["operation_id"], snapshot="b" * 64,
                        branch=dict(name=body["branch"], revision=1, tip="b" * 64, root="a" * 64))
                    output = json.dumps(dict(event="complete", answer=dict(text="", snapshot="b" * 64),
                                             receipt=receipt)).encode() + b"\n"
                self.send_response(200)
                self.send_header("Content-Length", str(len(output)))
                self.end_headers()
                self.wfile.write(output)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.close_server)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        self.client = CowClient.http(self.url, journal=OperationJournal(self.root / "journal"),
                                     api_key="test-image-key", endpoint_pin="image-fixture")

    def close_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(3)

    def test_binary_upload_and_prepare_bind_bytes_namespace_and_order(self):
        uploaded = self.client.upload_image(self.namespace, self.raw)
        self.assertEqual(uploaded.image_id, hashlib.sha256(self.raw).hexdigest())
        path, headers, data = self.requests[0]
        headers = {key.lower(): value for key, value in headers.items()}
        self.assertEqual(path, "/cow/images?namespace=" + self.namespace)
        self.assertEqual(headers["content-type"], "application/octet-stream")
        self.assertEqual(headers["x-cow-content-sha256"], uploaded.image_id)
        self.assertEqual(data, self.raw)
        self.client.prepare("image-branch", self.namespace, "Inspect the image.", "image-prepare",
                            images=(uploaded,))
        body = json.loads(self.requests[-1][2])
        self.assertEqual(body["messages"], [dict(role="user", content=[
            dict(type="image", image_id=uploaded.image_id), dict(type="text", text="Inspect the image.")])])
        saved = self.client.journal.read("image-prepare")
        self.assertEqual(saved["state"], "complete")
        self.assertNotIn("test-image-key", json.dumps(saved))

    def test_missing_empty_truncated_and_nonimage_reject_before_network(self):
        for raw in (None, b"", b"not an image", self.raw[:20]):
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    self.client.upload_image(self.namespace, raw)
        self.assertEqual(self.requests, [])

    def test_changed_upload_acknowledgment_is_rejected(self):
        self.bad_ack = True
        with self.assertRaises(ReceiptError):
            self.client.upload_image(self.namespace, self.raw)
        self.assertEqual(len(self.requests), 1)

    def test_upload_receipt_cannot_cross_namespace(self):
        uploaded = self.client.upload_image(self.namespace, self.raw)
        before = len(self.requests)
        with self.assertRaises(ValueError):
            self.client.prepare("wrong", "c" * 32, "Inspect.", "wrong-namespace", images=(uploaded,))
        self.assertEqual(len(self.requests), before)
        self.assertIsNone(self.client.journal.read("wrong-namespace"))

    def test_exif_dimensions_match_server_normalization_without_changing_bytes(self):
        from PIL import Image
        from branchwrite.cow_client import _image_metadata
        stream = io.BytesIO()
        exif = Image.Exif()
        exif[274] = 6
        Image.new("RGB", (2, 3), "red").save(stream, format="JPEG", exif=exif)
        raw = stream.getvalue()
        self.assertEqual(_image_metadata(raw), (3, 2, "image/jpeg"))
        self.assertEqual(raw, stream.getvalue())

    def test_delivery_audit_accepts_store_span_lists_and_rejects_missing_or_swapped_image(self):
        from validation.run_basic_loop_images import verify_capture_delivery
        digest = hashlib.sha256(self.raw).hexdigest()
        span = dict(kind="image", original_sha256=digest)
        # Only audit the ownership binding here. Canonical span validity belongs
        # to Store/InputHistory tests; no synthetic GPU qualification is claimed.
        inputs = [dict(kind="text", tokens=[1]), span]
        self.assertEqual(verify_capture_delivery(inputs, digest), [span])
        for invalid in (inputs[:1], inputs + [span], [dict(kind="image", original_sha256="0" * 64)]):
            with self.assertRaises(ValueError):
                verify_capture_delivery(invalid, digest)

    def test_cli_upload_and_prepare_pass_bound_inputs_and_clean_temporary_files(self):
        client = CowClient.cli(self.url, self.root / "cow_cli.py", state_dir=self.root / "cli-state",
            journal=OperationJournal(self.root / "cli-journal"), api_key="test-image-key", endpoint_pin="image-fixture")
        temporary = []

        def invoke(command, arguments, **kwargs):
            if command == "prepare":
                file = Path(arguments[arguments.index("--parts-file") + 1])
                temporary.append(file)
                self.assertEqual(json.loads(file.read_text()), [
                    dict(type="image", image_id=hashlib.sha256(self.raw).hexdigest()),
                    dict(type="text", text="Inspect.")])
                receipt = dict(operation_id="cli-image-prepare", snapshot="b" * 64,
                    branch=dict(name="image", revision=1, tip="b" * 64, root="a" * 64))
                return _Response(events=(dict(event="complete", answer=dict(text="", snapshot="b" * 64),
                                               receipt=receipt),), transport="cli")
            self.assertEqual(command, "upload-image")
            file = Path(arguments[arguments.index("--file") + 1])
            temporary.append(file)
            self.assertEqual(file.read_bytes(), self.raw)
            return _Response(json_value=dict(namespace_id=self.namespace,
                image_id=hashlib.sha256(self.raw).hexdigest(), bytes=len(self.raw),
                expires_ns=9999999999999999999, width=7, height=3, media_type="image/png"), transport="cli")

        with patch.object(client.transport, "_run", side_effect=invoke):
            uploaded = client.upload_image(self.namespace, self.raw)
            client.prepare("image", self.namespace, "Inspect.", "cli-image-prepare", images=(uploaded,))
        self.assertEqual(len(temporary), 2)
        self.assertTrue(all(not path.exists() for path in temporary))


if __name__ == "__main__":
    unittest.main()
