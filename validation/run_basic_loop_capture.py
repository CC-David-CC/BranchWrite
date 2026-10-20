"""Exercise H01 through the actual browser CLI, then the protected pixel oracle.

No model runs here. Capture, attachment delivery and interpretation are separate
obligations. The supplied verifier is used only as a checker of our actual image;
its independent browser path is never invoked.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tomllib


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--browser", type=Path, required=True)
    args = parser.parse_args(argv)
    pack = args.pack.resolve(strict=True)
    manifest = pack / "FILES.sha256"
    if sha(manifest.read_bytes()) != "12a60740aeb1eee5f6cc23071bb54583f94f5cb633f574e355d6f39e0c0631a3":
        raise ValueError("workload manifest is not the reviewed pack")
    expected = {}
    for row in manifest.read_text().splitlines():
        digest, name = row.split("  ", 1)
        path = pack / name
        if (name in expected or path.is_symlink() or not path.resolve(strict=True).is_relative_to(pack)
                or sha(path.read_bytes()) != digest):
            raise ValueError("workload bytes changed or escaped the pack")
        expected[name] = digest
    actual = {path.relative_to(pack).as_posix() for path in pack.rglob("*") if path.is_file()}
    if actual != set(expected) | {"FILES.sha256"}:
        raise ValueError("workload inventory changed")
    root = Path(__file__).resolve().parents[1]
    output = args.output.absolute()
    output.mkdir(mode=0o700, exist_ok=False)
    fixture = pack / "fixtures/starter/H01"
    payload = (fixture / "index.html").read_bytes()
    # This stage intentionally supports the reviewed one-file trusted fixture.
    if sorted(path.name for path in fixture.iterdir()) != ["index.html"]:
        raise ValueError("H01 fixture shape changed")
    command = [sys.executable, "-B", str(root / "tools/capture_page.py"),
        "--source", str(fixture), "--entry", "index.html", "--expected-sha256", sha(payload),
        "--browser", str(args.browser), "--output", str(output / "capture")]
    record = dict(status="RUNNING", target="H01", argv=command,
        pack_manifest_sha256=sha(manifest.read_bytes()), native_image_delivery="NOT_RUN",
        model_interpretation="NOT_RUN", source_sha256=sha(payload),
        scope="actual trusted fixture browser capture; no model/VC/G certification")
    try:
        observed = subprocess.run(command, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=45, check=False)
        (output / "capture.stdout").write_bytes(observed.stdout)
        (output / "capture.stderr").write_bytes(observed.stderr)
        record["capture_exit_code"] = observed.returncode
        if observed.returncode != 0:
            raise RuntimeError("browser CLI failed; retain stderr")
        receipt = tomllib.loads(observed.stdout.decode())
        image = output / "capture/capture.png"
        if (receipt != tomllib.loads((output / "capture/capture.toml").read_text())
                or receipt["source_sha256"] != sha(payload)
                or receipt["served_sha256"] != sha(payload)
                or receipt["image_sha256"] != sha(image.read_bytes())
                or Path(receipt["source_artifact"]).read_bytes() != payload
                or (receipt["width"], receipt["height"]) != (640, 480)
                or receipt["chromium_sandbox"] is not True):
            raise ValueError("capture/source receipt did not match actual artifacts")
        sys.path.insert(0, str(pack))
        from protected import checks
        checks.pixels(image, None, "H01", "01")
        # Reuse only the supplied source-identity functions, never browser_check.
        spec = importlib.util.spec_from_file_location("h01_protected_identity", pack / "tools/lab.py")
        lab = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(lab)
        revision = lab.tree_hash(lab.snapshot(fixture))
        if (fixture / "index.html").read_bytes() != payload:
            raise ValueError("original H01 source changed")
        if (output / "capture/workspace/index.html").read_bytes() != payload:
            raise ValueError("owned source copy changed")
        record.update(status="H01_CAPTURE_PASS", capture_receipt=receipt,
                      protected_pixel_check="PASS", source_revision=revision,
                      source_unchanged=True, image=str(image), image_sha256=sha(image.read_bytes()))
    except BaseException as error:
        record.update(status="H01_CAPTURE_FAIL", error_type=type(error).__name__, error=str(error))
        raise
    finally:
        (output / "result.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(json.dumps(record, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
