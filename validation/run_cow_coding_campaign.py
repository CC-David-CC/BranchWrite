"""Own a real COW service for the bounded four-arm coding pilot.

This validation harness imports COW's tested process lifecycle helpers. The
application client still uses only HTTP/CLI, not COW model/store internals.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import sys
import subprocess
from types import SimpleNamespace


def campaign_status(cases):
    expected = {task + "-" + arm for task in ("add", "multiply")
                for arm in ("baseline", "example", "gbnf", "both")}
    if not cases:
        return "NO_MODEL_OUTCOMES"
    labels = [item.get("label") for item in cases]
    if len(set(labels)) != len(labels) or not set(labels) <= expected:
        return "INVALID_CAMPAIGN_OUTCOMES"
    if not all(item.get("result", {}).get("status") == "TASK_PASS"
               and item.get("result", {}).get("report_truthful") is True for item in cases):
        return "MODEL_OUTCOMES_RECORDED"
    return ("BOUNDED_CODING_PILOT_PASS" if set(labels) == expected
            else "BOUNDED_CODING_SUBSET_PASS")


def tracker_error(error):
    # Progress is a separate persistence path from the redacted result writer.
    return None if error is None else type(error).__name__


def native_executable_identity(profile):
    command = profile.get("execution", {}).get("sut_command")
    if (not isinstance(command, list) or not command
            or not isinstance(command[0], str) or not Path(command[0]).is_absolute()):
        raise ValueError("campaign requires an absolute pinned native executable")
    path = Path(command[0])
    expected = profile.get("native_build", {}).get("sha256", {}).get(str(path))
    if (not isinstance(expected, str) or len(expected) != 64
            or any(character not in "0123456789abcdef" for character in expected)):
        raise ValueError("selected native executable is not in the declared file fingerprints")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    actual = digest.hexdigest()
    if actual != expected:
        raise ValueError("selected native executable fingerprint differs from its profile")
    return {"path": str(path), "sha256": actual}


def campaign_client(transport, url, cli_script, case_root, api_key, endpoint_pin):
    if transport not in ("http", "cli"):
        raise ValueError("unknown campaign transport")
    from branchwrite.cow_client import CowClient, OperationJournal
    options = dict(journal=OperationJournal(case_root / "journal"),
        api_key=api_key, endpoint_pin=endpoint_pin, timeout=180)
    if transport == "cli":
        return CowClient.cli(url, cli_script, state_dir=case_root / "cli-state", **options)
    return CowClient.http(url, **options)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cow-runtime", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--dependency-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--transport", choices=("http", "cli"), default="http")
    parser.add_argument("--arms", nargs="+", default=["baseline", "example", "gbnf", "both"])
    parser.add_argument("--tasks", nargs="+", default=["add", "multiply"])
    parser.add_argument("--basic-loop-pack", type=Path,
                        help="Use the supplied immutable pack for the H00 create/read target")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    runtime = args.cow_runtime.resolve(strict=True)
    dependency = args.dependency_root.resolve(strict=True)
    sys.path[:0] = [str(root), str(root / "tools"), str(dependency), str(runtime),
        str(runtime / "tools"), str(runtime / "experimental/branching_context/src"),
        str(runtime / "experimental/branching_context/scripts")]
    from run_cli_workflow_probe import _Campaign, _atomic_write, redact_sensitive_value, sha256_file
    from run_cow_coding_pilot import ARMS, CodingPilot, FileTask, Task, create_file_schema
    from branchwrite.coding_contract import LiteralContract
    if any(arm not in (*ARMS, "json_schema") for arm in args.arms) or len(set(args.arms)) != len(args.arms):
        raise ValueError("unknown or duplicate arm")
    basic_pack = None
    if args.basic_loop_pack is not None:
        if args.tasks != ["H00"] or args.arms not in (["gbnf"], ["json_schema"]):
            raise ValueError("basic-loop integration requires only H00 and one gbnf or json_schema arm")
        basic_pack = args.basic_loop_pack.resolve(strict=True)
        # Pin the owner-supplied pack; never import its verifier into model context.
        manifest = basic_pack / "FILES.sha256"
        if sha256_file(manifest) != "12a60740aeb1eee5f6cc23071bb54583f94f5cb633f574e355d6f39e0c0631a3":
            raise ValueError("basic-loop pack manifest is not the reviewed input")
        expected = {}
        for line in manifest.read_text(encoding="utf-8").splitlines():
            digest, relative = line.split("  ", 1)
            path = basic_pack / relative
            if (not path.resolve(strict=True).is_relative_to(basic_pack) or path.is_symlink()
                    or sha256_file(path) != digest or relative in expected):
                raise ValueError("basic-loop input is changed or unsafe")
            expected[relative] = digest
        actual = {str(path.relative_to(basic_pack)) for path in basic_pack.rglob("*") if path.is_file()}
        if actual != set(expected) | {"FILES.sha256"}:
            raise ValueError("basic-loop input file inventory changed")
        if any((basic_pack / "fixtures/starter/H00").iterdir()):
            raise ValueError("H00 starter must be empty")
    elif any(task not in ("add", "multiply") for task in args.tasks) or len(set(args.tasks)) != len(args.tasks):
        raise ValueError("unknown or duplicate fixed task")
    elif "json_schema" in args.arms:
        raise ValueError("JSON Schema is currently an H00-only experiment")

    class Campaign(_Campaign):
        def _bootstrap(self, ordinal):
            path = self.run_dir / f"server-bootstrap-{ordinal}.py"
            body = (
                "import hashlib,importlib,json,sys\nfrom pathlib import Path\n"
                f"runtime=Path({str(runtime)!r})\n"
                f"sys.path[:0]=[{str(dependency)!r},str(runtime),str(runtime/'tools'),str(runtime/'experimental/branching_context/src')]\n"
                "rows={}\n"
                "for name in ('context_time_travel.coordinator','context_time_travel.real','context_time_travel.store','context_time_travel.grammar_first','serve.cow_http'):\n"
                " m=importlib.import_module(name);p=Path(m.__file__).resolve();rows[name]={'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}\n"
                "print(json.dumps({'event':'runtime_imports','modules':rows}),flush=True)\n"
                f"sys.argv=['cow-http','--grammar-registry',{str(self.run_dir / 'grammar-registry.json')!r},*sys.argv[3:]]\n"
                "importlib.import_module('serve.cow_http').main()\n"
            )
            with path.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(body)
            return path

        def stop_service(self):
            try:
                super().stop_service()
            finally:
                self.record = redact_sensitive_value(self.record, (self.api_key,))
                self.publish()

    output = args.output.absolute()
    output.mkdir(mode=0o700, parents=False, exist_ok=False)
    owner = Campaign(SimpleNamespace(runtime_root=runtime, profile=args.profile,
        store=output / "store", run_dir=output))
    owner.record = {"schema": "bw-coding-campaign-v1", "status": "RUNNING",
        "services": [], "cases": [], "failures": [], "chat_server": "NOT_STARTED",
        "transport": args.transport,
        "requested_arms": args.arms, "requested_tasks": args.tasks,
        "scope": "bounded Q4 coding pilot, no full product/gate qualification"}
    owner.profile = json.loads(args.profile.read_bytes())
    owner.profile_path = args.profile.resolve(strict=True)
    owner.cli_path = runtime / "tools/cow_cli.py"
    error = None
    try:
        owner._runtime_imports()
        owner.record["cow_runtime_closure"] = owner._runtime_closure(owner.profile, runtime)
        owner.record["profile_sha256"] = sha256_file(owner.profile_path)
        owner.record["model_contract_id"] = owner.profile["model_contract_id"]
        owner.record["execution_profile_id"] = owner.profile["execution_profile_id"]
        native_identity = native_executable_identity(owner.profile)
        owner.record["native_executable"] = native_identity["path"]
        owner.record["native_binary_sha256"] = native_identity["sha256"]
        owner.record["branchwrite_source_sha256"] = {
            str(path.relative_to(root)): sha256_file(path)
            for directory in ("branchwrite", "tools", "validation")
            for path in (root / directory).rglob("*.py")}
        registry = {"schema": 1, "states": {
            "BW_REPLACEMENT": {"format": "gbnf", "source": LiteralContract("replacement", 32768, 256, 4096).gbnf()},
            "BW_REPORT": {"format": "gbnf", "source": LiteralContract("report", 8192, 64, 4096).gbnf()}}}
        if basic_pack is not None and args.arms == ["json_schema"]:
            registry["states"]["BW_H00_JSON"] = {
                "format": "json_schema", "source": create_file_schema("hello.txt")}
        _atomic_write(output / "grammar-registry.json", registry)
        owner.record["registry_sha256"] = sha256_file(output / "grammar-registry.json")
        owner.tracker = owner._ProgressTracker(output, "bw-coding-campaign").start()
        owner.publish()
        owner.start_service()
        url = owner._ready_url(owner.service.ready)
        binding = hashlib.sha256((owner.record["profile_sha256"] + str(output / "store")).encode()).hexdigest()
        owner.record["endpoint_binding"] = {"pin": binding, "attestation": "root-owned launch; not HTTP-attested"}
        for task_name in args.tasks:
            if task_name == "H00":
                arm = args.arms[0]
                label = "H00-" + arm
                owner.phase(label)
                case_root = output / label
                case_root.mkdir(mode=0o700)
                client = campaign_client(args.transport, url, owner.cli_path,
                    case_root, owner.api_key, binding)
                before = owner._status()
                task_file = basic_pack / "tasks/H00.md"
                task = FileTask("H00", basic_pack / "fixtures/starter/H00", "hello.txt",
                                task_file.read_text(encoding="utf-8"))
                result = CodingPilot(client, case_root / "case",
                    eos_tokens=tuple(owner.profile["execution"]["eos_tokens"]),
                    max_tokens=128).run_create_read(task, output_format=arm)
                check = {"status": "NOT_RUN"}
                if result.status == "FILE_CREATED_AND_READ":
                    command = [sys.executable, "-B", str(basic_pack / "tools/lab.py"), "check", "H00",
                        "--work", str(case_root / "case/tool/workspace"),
                        "--out", str(case_root / "protected-check")]
                    observed = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE, timeout=30, check=False)
                    (case_root / "protected-check.stdout").write_bytes(observed.stdout)
                    (case_root / "protected-check.stderr").write_bytes(observed.stderr)
                    check = {"status": "PASS" if observed.returncode == 0 else "FAIL",
                        "exit_code": observed.returncode, "argv": command}
                owner.record["cases"].append({"label": label, "model_output_format": arm,
                    "result": asdict(result),
                    "protected_check": check, "task_sha256": sha256_file(task_file),
                    "pack_manifest_sha256": sha256_file(basic_pack / "FILES.sha256"),
                    "status_before": before, "status_after": owner._status()})
                owner.record["status"] = ("BOUNDED_H00_PASS" if result.status == "FILE_CREATED_AND_READ"
                                          and check["status"] == "PASS" else "H00_OUTCOME_RECORDED")
                owner.publish()
                continue
            instruction = ("Make add return the sum of its arguments." if task_name == "add"
                           else "Make multiply return the product of its arguments.")
            task = Task(task_name, root / "fixtures/coding" / task_name, "src/arith.py", instruction)
            for arm in args.arms:
                label = task_name + "-" + arm
                owner.phase(label)
                case_root = output / label
                case_root.mkdir(mode=0o700)
                client = campaign_client(args.transport, url, owner.cli_path,
                    case_root, owner.api_key, binding)
                before = owner._status()
                result = CodingPilot(client, case_root / "case",
                    eos_tokens=tuple(owner.profile["execution"]["eos_tokens"]),
                    max_tokens=512).run(task, arm)
                owner.record["cases"].append({"label": label, "result": asdict(result),
                    "status_before": before, "status_after": owner._status()})
                owner.publish()
        if basic_pack is None:
            owner.record["status"] = campaign_status(owner.record["cases"])
    except BaseException as exc:
        error = exc
        owner.record["status"] = "INFRASTRUCTURE_FAIL"
        owner.record["failures"].append({"type": type(exc).__name__, "message": str(exc)})
    finally:
        if owner.service is not None:
            try:
                owner.stop_service()
            except BaseException as exc:
                error = error or exc
                owner.record["status"] = "CLEANUP_FAIL"
                owner.record["failures"].append({"type": type(exc).__name__, "message": str(exc)})
        owner.publish()
        if owner.tracker:
            owner.tracker.finish(owner.record["status"], tracker_error(error))
            owner.tracker.close()
    return 1 if error else 0


if __name__ == "__main__":
    raise SystemExit(main())
