"""Actual H02: existing capture tool -> BranchWrite CLI client -> COW -> GPU.

The oracle/source metadata stay host-side. Each observer receives only its image
and the same neutral question in a fresh context. No automatic model retry.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import random
import sys
from types import SimpleNamespace
import uuid


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def verify_capture_delivery(canonical_spans, original_sha256):
    """Store.input_lineage returns canonical span records as a list, not a view."""
    if not isinstance(canonical_spans, (list, tuple)):
        raise ValueError("canonical input records must be a span sequence")
    images = [dict(span) for span in canonical_spans if span["kind"] == "image"]
    if len(images) != 1 or images[0]["original_sha256"] != original_sha256:
        raise ValueError("canonical image input did not match captured/uploaded bytes")
    return images


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cow-runtime", type=Path, required=True)
    parser.add_argument("--dependency-root", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--vision-config", type=Path, required=True)
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--browser", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    runtime = args.cow_runtime.resolve(strict=True)
    pack = args.pack.resolve(strict=True)
    sys.path[:0] = [str(root), str(runtime), str(runtime / "tools"),
        str(runtime / "experimental/branching_context/src"),
        str(runtime / "experimental/branching_context/scripts"), str(args.dependency_root)]
    from run_cli_grammar_probe import GrammarProbe, _atomic_json
    from branchwrite.browser_capture import BrowserConfig
    from branchwrite.execution import Executor, Grant
    from branchwrite.cow_client import CowClient, OperationJournal
    from validation.run_cow_coding_campaign import native_executable_identity

    manifest = pack / "FILES.sha256"
    if sha(manifest.read_bytes()) != "12a60740aeb1eee5f6cc23071bb54583f94f5cb633f574e355d6f39e0c0631a3":
        raise ValueError("unreviewed workload manifest")
    expected = {}
    for row in manifest.read_text().splitlines():
        digest, relative = row.split("  ", 1)
        path = pack / relative
        if (relative in expected or path.is_symlink() or not path.resolve(strict=True).is_relative_to(pack)
                or sha(path.read_bytes()) != digest):
            raise ValueError("changed workload source")
        expected[relative] = digest
    if {p.relative_to(pack).as_posix() for p in pack.rglob("*") if p.is_file()} != set(expected) | {"FILES.sha256"}:
        raise ValueError("changed workload inventory")
    # Expected labels and original filenames never enter model-facing messages.
    question = (pack / "tasks/H02.md").read_text().split("\n", 1)[1].strip()
    variants = ["01", "02", "03"]
    random.Random(1702).shuffle(variants)
    output = args.output.absolute()
    output.mkdir(mode=0o700, exist_ok=False)
    class ImageOwner(GrammarProbe):
        def _bootstrap(self, registry_path):
            path = super()._bootstrap(registry_path)
            body = path.read_text()
            marker = "sys.argv=['cow-http',*sys.argv[5:]]\n"
            if body.count(marker) != 1:
                raise ValueError("existing service bootstrap contract changed")
            body = body.replace(marker, "sys.argv=['cow-http','--vision-config',"
                + repr(str(args.vision_config.resolve(strict=True))) + ",*sys.argv[5:]]\n")
            path.write_text(body, encoding="utf-8", newline="\n")
            return path

    probe = ImageOwner(SimpleNamespace(runtime_root=runtime, profile=args.profile,
        store=output / "store", run_dir=output, dependency_root=args.dependency_root,
        ram_gib=96, disk_gib=128))
    probe.record.update(status="RUNNING", scope=__doc__, inference_host="llm-60",
        numerical_qualification="NOT_RUN", cases=[], failures=[], order_seed=1702,
        chat_server="NOT_STARTED", question_sha256=sha(question.encode()),
        pack_manifest_sha256=sha(manifest.read_bytes()),
        vision_config=dict(path=str(args.vision_config), sha256=sha(args.vision_config.read_bytes())))
    error = None
    try:
        probe._imports()
        profile = json.loads(args.profile.read_bytes())
        probe.runtime_closure(profile, runtime)
        probe.record.update(profile_sha256=sha(args.profile.read_bytes()),
            execution_profile_id=profile["execution_profile_id"], model_contract_id=profile["model_contract_id"],
            native_executable=native_executable_identity(profile),
            branchwrite_source_sha256={str(p.relative_to(root)): sha(p.read_bytes())
                for folder in ("branchwrite", "tools", "validation") for p in (root / folder).rglob("*.py")})
        registry = output / "grammar-registry.json"
        _atomic_json(registry, {"schema": 1, "states": {"H02_LABEL": {
            "format": "gbnf", "source": 'root ::= "LEFT" | "RIGHT" | "NOT_VISIBLE"'}}})
        probe.tracker = probe.ProgressTracker(output, "branchwrite-h02").start()
        probe.start_service(registry)
        url = probe.ready_url(probe.service.ready)
        pin = sha((probe.record["profile_sha256"] + str(output / "store")).encode())
        probe.record["endpoint_binding"] = dict(pin=pin, scope="host launch provenance; not HTTP-attested")
        sys.path.insert(0, str(pack))
        from protected import checks
        for variant in variants:
            opaque = "bw-" + uuid.uuid4().hex
            case = output / opaque
            case.mkdir(mode=0o700)
            probe.phase("observe-" + opaque)
            entry = variant + ".html"
            source = pack / "fixtures/starter/H02"
            original = (source / entry).read_bytes()
            executor = Executor.create(source, case / "capture", browser=BrowserConfig(args.browser))
            capture = executor.capture_page(opaque + "-capture", Grant((), False, capture_paths=(entry,)),
                                             entry, sha(original))
            image = capture.image.read_bytes()
            expected_label = checks.position(capture.image.path)
            (case / "image.png").write_bytes(image)
            client = CowClient.cli(url, runtime / "tools/cow_cli.py", state_dir=case / "cli-state",
                journal=OperationJournal(case / "journal"), api_key=probe.secret, endpoint_pin=pin, timeout=180)
            namespace = client.create_namespace("Visual observation", opaque + "-namespace")["namespace_id"]
            upload = client.upload_image(namespace, image)
            prepared = client.prepare(opaque, namespace, question, opaque + "-prepare", images=(upload,))
            _, inputs = probe.store.input_lineage(prepared.receipt.snapshot)
            spans = verify_capture_delivery(inputs, sha(image))
            answer = client.answer(opaque, prepared.receipt.branch.revision, opaque + "-answer", 16,
                                   settings={"temperature": 0.0}, grammar_state="H02_LABEL")
            text = answer.answer.get("text")
            tokens = answer.answer.get("tokens", [])
            complete = bool(tokens) and tokens[-1] in profile["execution"]["eos_tokens"]
            if (source / entry).read_bytes() != original:
                raise ValueError("protected source changed")
            row = dict(opaque_id=opaque, host_only_variant=variant, source_sha256=sha(original),
                capture=dict(image_sha256=capture.image.sha256, image_bytes=capture.image.size_bytes,
                    source_sha256=capture.source.sha256, served_sha256=capture.served_sha256,
                    width=capture.viewport[0], height=capture.viewport[1],
                    browser_version=capture.browser_version, chromium_sandbox=capture.chromium_sandbox),
                upload_receipt=dict(upload.raw), prepare_receipt=dict(prepared.receipt.raw),
                image_spans=spans, answer=answer.answer, answer_receipt=dict(answer.receipt.raw),
                delivered_image="PASS", expected_host_only=expected_label, completed=complete,
                interpretation="PASS" if complete and text == expected_label else "FAIL")
            probe.record["cases"].append(row)
            _atomic_json(case / "result.json", row)
            probe.publish()
            if row["interpretation"] != "PASS":
                raise ValueError("H02 interpretation mismatch; retained first attempt, no automatic retry")
        probe.record["status"] = "H02_IMAGE_DELIVERY_AND_INTERPRETATION_PASS"
    except BaseException as exc:
        error = exc
        probe.record["status"] = "H02_FAIL"
        probe.record["failures"].append(dict(type=type(exc).__name__, message=str(exc)))
    finally:
        if probe.service is not None:
            try:
                probe.stop_service()
            except BaseException as exc:
                error = error or exc
                probe.record["status"] = "CLEANUP_FAIL"
                probe.record["failures"].append(dict(type=type(exc).__name__, message=str(exc)))
        probe.publish()
        if probe.tracker:
            probe.tracker.finish(probe.record["status"], None if error is None else type(error).__name__)
            probe.tracker.close()
    return 1 if error else 0


if __name__ == "__main__":
    raise SystemExit(main())
