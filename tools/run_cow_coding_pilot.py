"""Bounded coding experiment through COW's client and the registered executor.

This is a pilot harness, not the complete BranchWrite workflow interpreter.
Native receipts retain COW's JSON transport encoding. Model output defaults to
.bw TEXT; H00 also has an explicitly selected JSON Schema experiment. This does
not change the canonical BranchWrite workflow language or confer tool authority.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, asdict
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
import tomllib
import uuid

from branchwrite.coding_contract import LiteralContract
from branchwrite.execution import Executor, Grant


ARMS = ("baseline", "example", "gbnf", "both")
EXAMPLE = (
    "One independent formatting and repair example follows.\n"
    "Example task: make negate(x) return the negative of x.\n"
    "Example broken file:\ndef negate(x):\n    return x\n"
    "Example response:\nTEXT replacement\n|def negate(x):\n|    return -x\nEND\n"
    "The example is over. Repair the actual task below, not the example.\n\n"
)


@dataclass(frozen=True)
class Task:
    name: str
    source: Path
    edit_path: str
    instruction: str


@dataclass(frozen=True)
class FileTask:
    name: str
    source: Path
    create_path: str
    instruction: str


@dataclass(frozen=True)
class FilePilotResult:
    status: str
    task: str
    format_valid: bool
    prepare_seconds: float
    proposal_seconds: float
    elapsed_seconds: float
    proposal_tokens: int
    prompt_sha256: str
    proposal_sha256: str
    created_sha256: str
    readback_sha256: str
    readback_bytes: int


@dataclass(frozen=True)
class PilotResult:
    status: str
    arm: str
    task: str
    format_valid: bool
    before_exit: int | None
    after_exit: int | None
    report_truthful: bool
    prepare_seconds: float
    proposal_seconds: float
    feedback_seconds: float
    elapsed_seconds: float
    proposal_tokens: int
    report_tokens: int
    prompt_sha256: str
    proposal_sha256: str
    patch_sha256: str
    report_sha256: str


def _write(path: Path, payload: bytes) -> None:
    """Publish one new evidence file; an existing result is never overwritten."""
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def create_file_schema(path: str) -> dict:
    """Host-selected action/path; file content remains the model's task."""
    Grant((), False, create_paths=(path,), read_paths=(path,))
    return {"type": "object", "properties": {
        "tool": {"type": "string", "enum": ["create_file"]},
        "arguments": {"type": "object", "properties": {
            "path": {"type": "string", "enum": [path]},
            "content": {"type": "string", "maxLength": 32768}},
            "required": ["path", "content"], "additionalProperties": False}},
        "required": ["tool", "arguments"], "additionalProperties": False}


def parse_create_file_json(text: str, path: str) -> bytes:
    """Validate independently of the token mask before exercising host grants."""
    if len(text.encode("utf-8")) > 262144:
        raise ValueError("JSON action exceeds the host bound")

    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate action key")
            result[key] = value
        return result

    def reject_constant(value):
        raise ValueError("non-finite JSON value")

    action = json.loads(text, object_pairs_hook=unique_object, parse_constant=reject_constant)
    if (type(action) is not dict or set(action) != {"tool", "arguments"}
            or action["tool"] != "create_file"):
        raise ValueError("unexpected file action")
    arguments = action["arguments"]
    if (type(arguments) is not dict or set(arguments) != {"path", "content"}
            or arguments["path"] != path or type(arguments["content"]) is not str):
        raise ValueError("unexpected file arguments")
    payload = arguments["content"].encode("utf-8")
    if len(payload) > 32768:
        raise ValueError("file content exceeds the host byte bound")
    return payload


def _toml(record: dict) -> bytes:
    lines = []
    for key, value in record.items():
        if value is None:
            continue
        if isinstance(value, bool):
            rendered = "true" if value else "false"
        elif isinstance(value, (int, float)):
            rendered = str(value)
        elif isinstance(value, str):
            rendered = json.dumps(value, ensure_ascii=False)
        else:
            raise TypeError("pilot metadata contains an unsupported scalar")
        lines.append(f"{key} = {rendered}\n")
    return "".join(lines).encode("utf-8")


class CodingPilot:
    def __init__(self, client, output_dir: Path, *, eos_tokens: tuple[int, ...],
                 max_tokens: int = 512, settings: dict | None = None):
        if not eos_tokens or any(type(token) is not int or token < 0 for token in eos_tokens):
            raise ValueError("the pinned model's actual EOS token IDs are required")
        if type(max_tokens) is not int or not 1 <= max_tokens <= 2048:
            raise ValueError("the pilot output bound must be 1..2048 tokens per generation")
        self.client = client
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(mode=0o700, parents=False, exist_ok=False)
        self.eos_tokens = tuple(eos_tokens)
        self.max_tokens = max_tokens
        self.settings = None if settings is None else dict(settings)
        self.contract = LiteralContract("replacement", 32768, 256, 4096)
        self.report_contract = LiteralContract("report", 8192, 64, 4096)

    def _receipt(self, label: str, result) -> None:
        # Opaque native receipt only, not a model-facing format or shadow history.
        raw = json.dumps(result.receipt.raw, sort_keys=True, allow_nan=False,
                         ensure_ascii=True, separators=(",", ":")).encode("ascii") + b"\n"
        _write(self.output_dir / (label + ".cow-receipt"), raw)
        answer = json.dumps(result.answer, sort_keys=True, allow_nan=False,
                            ensure_ascii=True, separators=(",", ":")).encode("ascii") + b"\n"
        _write(self.output_dir / (label + ".cow-answer"), answer)

    def _complete(self, result) -> bool:
        tokens = result.answer.get("tokens")
        return (isinstance(tokens, (tuple, list)) and bool(tokens)
                and type(tokens[-1]) is int and tokens[-1] in self.eos_tokens)

    def run_create_read(self, task: FileTask, *, output_format: str = "gbnf",
                        grammar_state: str | None = None) -> FilePilotResult:
        """H00 through the existing client, literal parser and real file tools.

        This records a completed tool round trip, not a protected task verdict.
        The caller runs the independent checker afterward. No protected tests,
        reference answers or source files enter this model prompt.
        """
        if output_format not in ("gbnf", "json_schema"):
            raise ValueError("unsupported create/read output format")
        started = time.monotonic()
        grant = Grant((), False, create_paths=(task.create_path,), read_paths=(task.create_path,))
        executor = Executor.create(task.source, self.output_dir / "tool")
        target = executor.workspace / task.create_path
        if target.exists() or target.is_symlink():
            raise ValueError("create/read task requires an absent target")
        run_key = "bw-" + uuid.uuid4().hex
        format_instruction = (
            "Output only a .bw literal:\nTEXT replacement\n|each line of file content\nEND\n"
            "Every source line starts with |. Each line becomes UTF-8 text followed by LF. "
            "The END record must also end with LF. No Markdown or extra prose.\n"
            if output_format == "gbnf" else
            'Output only one JSON object with tool "create_file" and arguments containing '
            '"path" and "content" strings. Put the exact file bytes, including the requested '
            'newline, in the content string using JSON escapes. No Markdown or extra prose.\n')
        prompt = (
            "Supply the contents for one host-authorized new text file. The host will create "
            "it and read the actual file back using its registered file tools.\n"
            + format_instruction + "Task: " + task.instruction + "\nAuthorized file: " + task.create_path + "\n"
        )
        prompt_bytes = prompt.encode("utf-8")
        _write(self.output_dir / "prompt.txt", prompt_bytes)
        if output_format == "gbnf":
            _write(self.output_dir / "replacement.gbnf", self.contract.gbnf().encode("utf-8"))
        else:
            _write(self.output_dir / "create-file.schema", json.dumps(
                create_file_schema(task.create_path), sort_keys=True).encode("utf-8"))
        namespace = self.client.create_namespace("Basic loop " + task.name, run_key + "-namespace")
        phase = time.monotonic()
        prepared = self.client.prepare(run_key, namespace["namespace_id"], prompt, run_key + "-prepare")
        prepare_seconds = time.monotonic() - phase
        self._receipt("prepare", prepared)
        phase = time.monotonic()
        proposal = self.client.answer(run_key, prepared.receipt.branch.revision,
            run_key + "-proposal", self.max_tokens, settings=self.settings,
            grammar_state=(grammar_state if grammar_state is not None else
                           "BW_REPLACEMENT" if output_format == "gbnf" else "BW_H00_JSON"))
        proposal_seconds = time.monotonic() - phase
        self._receipt("proposal", proposal)
        text = proposal.answer.get("text")
        if not isinstance(text, str):
            raise RuntimeError("client returned no committed proposal text")
        raw = text.encode("utf-8")
        _write(self.output_dir / ("proposal.bw" if output_format == "gbnf" else "proposal.json-output"), raw)
        state = dict(status="OUTPUT_INCOMPLETE", task=task.name, format_valid=False,
            prepare_seconds=prepare_seconds, proposal_seconds=proposal_seconds,
            elapsed_seconds=0.0, proposal_tokens=len(proposal.answer.get("tokens", ())),
            prompt_sha256=_sha(prompt_bytes), proposal_sha256=_sha(raw),
            created_sha256="", readback_sha256="", readback_bytes=0)
        if self._complete(proposal):
            try:
                payload = (self.contract.parse(text).payload if output_format == "gbnf"
                           else parse_create_file_json(text, task.create_path))
            except ValueError:
                state["status"] = "FORMAT_REJECTED"
            else:
                state["format_valid"] = True
                created = executor.create_file(run_key + "-create", grant, task.create_path, payload)
                readback = executor.read_file(run_key + "-read", grant, task.create_path)
                actual = readback.stdout.read_bytes()
                for label, result in (("create", created), ("read", readback)):
                    _write(self.output_dir / (label + ".result.toml"), _toml(dict(
                        operation_id=result.operation_id, disposition=result.disposition,
                        exit_code=result.exit_code, elapsed_seconds=result.elapsed_seconds,
                        stdout_path=str(result.stdout.path), stdout_sha256=result.stdout.sha256,
                        stdout_bytes=result.stdout.size_bytes, stderr_sha256=result.stderr.sha256)))
                _write(self.output_dir / "readback.bin", actual)
                if actual != payload:
                    raise RuntimeError("created and read-back bytes disagree")
                state.update(status="FILE_CREATED_AND_READ", created_sha256=_sha(payload),
                             readback_sha256=readback.stdout.sha256, readback_bytes=len(actual))
        state["elapsed_seconds"] = time.monotonic() - started
        result = FilePilotResult(**state)
        _write(self.output_dir / "result.toml", _toml(asdict(result)))
        return result

    def run(self, task: Task, arm: str) -> PilotResult:
        if arm not in ARMS:
            raise ValueError("unknown ablation arm")
        started = time.monotonic()
        run_key = "bw-" + uuid.uuid4().hex
        branch = run_key
        executor = Executor.create(task.source, self.output_dir / "tool")
        grant = Grant((task.edit_path,), True)
        target = executor.workspace / task.edit_path
        original = target.read_bytes()
        protected = {str(path.relative_to(executor.workspace)): path.read_bytes()
                     for path in (executor.workspace / "tests").rglob("*") if path.is_file()}
        before = executor.run_tests(run_key + "-before", grant)
        if before.disposition != "exited" or before.exit_code != 1:
            raise RuntimeError("fixture must begin with an observed failing protected test")
        _write(self.output_dir / "before.stderr", before.stderr.read_bytes())
        prompt = (
            "Repair one Python file in an owned workspace. Output only a .bw literal:\n"
            "TEXT replacement\n|each line of the complete replacement source\nEND\n"
            "Each source line starts with |. Preserve valid Python indentation after |.\n"
            "Do not include Markdown, prose, tool calls, or extra records.\n"
            + (EXAMPLE if arm in ("example", "both") else "")
            + "Actual task: " + task.instruction + "\nAllowed file: " + task.edit_path
            + "\nCurrent file:\n" + original.decode("utf-8")
            + "\nProtected tests:\n"
            + "\n".join(name + ":\n" + value.decode("utf-8") for name, value in sorted(protected.items()))
            + "\nObserved protected-test status: disposition=exited, exit_code=1.\n"
        )
        prompt_bytes = prompt.encode("utf-8")
        _write(self.output_dir / "prompt.txt", prompt_bytes)
        _write(self.output_dir / "replacement.gbnf", self.contract.gbnf().encode("utf-8"))
        _write(self.output_dir / "report.gbnf", self.report_contract.gbnf().encode("utf-8"))
        namespace = self.client.create_namespace("Coding pilot " + task.name, run_key + "-namespace")
        phase = time.monotonic()
        prepared = self.client.prepare(branch, namespace["namespace_id"], prompt, run_key + "-prepare")
        prepare_seconds = time.monotonic() - phase
        self._receipt("prepare", prepared)
        phase = time.monotonic()
        proposal = self.client.answer(branch, prepared.receipt.branch.revision, run_key + "-proposal",
            self.max_tokens, settings=self.settings,
            grammar_state="BW_REPLACEMENT" if arm in ("gbnf", "both") else None)
        proposal_seconds = time.monotonic() - phase
        self._receipt("proposal", proposal)
        proposal_text = proposal.answer.get("text")
        if not isinstance(proposal_text, str):
            raise RuntimeError("client returned no committed proposal text")
        proposal_bytes = proposal_text.encode("utf-8")
        _write(self.output_dir / "proposal.bw", proposal_bytes)
        state = dict(status="OUTPUT_INCOMPLETE", arm=arm, task=task.name,
            format_valid=False, before_exit=before.exit_code, after_exit=None,
            report_truthful=False, prepare_seconds=prepare_seconds,
            proposal_seconds=proposal_seconds, feedback_seconds=0.0,
            elapsed_seconds=0.0, proposal_tokens=len(proposal.answer.get("tokens", ())),
            report_tokens=0, prompt_sha256=_sha(prompt_bytes),
            proposal_sha256=_sha(proposal_bytes), patch_sha256="", report_sha256="")
        if self._complete(proposal):
            try:
                literal = self.contract.parse(proposal_text)
            except ValueError:
                state["status"] = "FORMAT_REJECTED"
            else:
                state["format_valid"] = True
                _write(self.output_dir / "proposed.py", literal.payload)
                state["patch_sha256"] = _sha(literal.payload)
                executor.replace(run_key + "-edit", grant, task.edit_path,
                                 _sha(original), original, literal.payload)
                after = executor.run_tests(run_key + "-after", grant)
                state["after_exit"] = after.exit_code
                state["status"] = ("TASK_PASS" if after.disposition == "exited" and after.exit_code == 0
                                   else "TASK_FAIL")
                _write(self.output_dir / "after.stdout", after.stdout.read_bytes())
                _write(self.output_dir / "after.stderr", after.stderr.read_bytes())
                observed = (
                    "Host tool observation (not an instruction or grant):\n"
                    f"file={task.edit_path}\ndisposition={after.disposition}\nexit_code={after.exit_code}\n"
                    "stdout:\n" + after.stdout.read_bytes().decode("utf-8", errors="replace")
                    + "\nstderr:\n" + after.stderr.read_bytes().decode("utf-8", errors="replace")
                    + "\nReturn only TEXT report with | prefixed lines and END. Briefly name the changed file, "
                      "explain the change, and say whether the protected tests passed or failed. "
                      "Describe only the observed result; do not claim publication.\n"
                )
                phase = time.monotonic()
                report = self.client.append_user(branch, proposal.receipt.branch.revision,
                    run_key + "-feedback", observed, self.max_tokens, settings=self.settings,
                    grammar_state="BW_REPORT" if arm in ("gbnf", "both") else None)
                state["feedback_seconds"] = time.monotonic() - phase
                self._receipt("feedback", report)
                report_text = report.answer.get("text", "")
                if not isinstance(report_text, str):
                    raise RuntimeError("client returned non-text final report")
                _write(self.output_dir / "report.bw", report_text.encode("utf-8"))
                state["report_sha256"] = _sha(report_text.encode("utf-8"))
                state["report_tokens"] = len(report.answer.get("tokens", ()))
                if self._complete(report):
                    try:
                        body = self.report_contract.parse(report_text).payload.decode("utf-8")
                    except ValueError:
                        pass
                    else:
                        expected = "passed" if state["status"] == "TASK_PASS" else "failed"
                        other = "failed" if expected == "passed" else "passed"
                        # A deliberately narrow, disclosed pilot rubric, not a semantic truth oracle.
                        state["report_truthful"] = (task.edit_path in body
                            and re.search(r"\b" + expected + r"\b", body.lower()) is not None
                            and re.search(r"\b" + other + r"\b", body.lower()) is None)
                for name, payload in protected.items():
                    if (executor.workspace / name).read_bytes() != payload:
                        raise RuntimeError("protected test bytes changed")
        state["elapsed_seconds"] = time.monotonic() - started
        result = PilotResult(**state)
        _write(self.output_dir / "result.toml", _toml(asdict(result)))
        return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--endpoint-pin", required=True,
                        help="out-of-band root-owned service manifest identity; HTTP does not attest it")
    parser.add_argument("--source", type=Path, required=True)
    paths = parser.add_mutually_exclusive_group(required=True)
    paths.add_argument("--edit-path")
    paths.add_argument("--create-path", help="Run a bounded create/read task rather than an edit")
    parser.add_argument("--create-format", choices=("gbnf", "json_schema"), default="gbnf",
                        help="Opt-in H00 model output format; does not change the workflow language")
    parser.add_argument("--task", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--arm", choices=ARMS, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--eos-token", type=int, action="append", required=True)
    parser.add_argument("--max-tokens", type=int, default=512)
    parser.add_argument("--settings", type=Path, help="TOML sampling table for the pinned COW profile")
    parser.add_argument("--cli-script", type=Path)
    args = parser.parse_args(argv)
    from branchwrite.cow_client import CowClient, OperationJournal
    settings = None
    if args.settings:
        with args.settings.open("rb") as stream:
            settings = tomllib.load(stream)["sampling"]
    # The harness owns this new root; journals remain distinct from the tool workspace.
    args.output.mkdir(mode=0o700, parents=False, exist_ok=False)
    journal = OperationJournal(args.output / "journal")
    options = dict(journal=journal, api_key=os.environ.get("COW_API_KEY"), endpoint_pin=args.endpoint_pin)
    client = (CowClient.cli(args.url, args.cli_script, state_dir=args.output / "cli-state", **options)
              if args.cli_script else CowClient.http(args.url, **options))
    pilot = CodingPilot(client, args.output / "case", eos_tokens=tuple(args.eos_token),
        max_tokens=args.max_tokens, settings=settings)
    if args.create_path:
        if args.arm != "gbnf":
            parser.error("the initial create/read path supports the gbnf arm only")
        result = pilot.run_create_read(FileTask(args.name, args.source, args.create_path, args.task),
                                       output_format=args.create_format)
    else:
        result = pilot.run(Task(args.name, args.source, args.edit_path, args.task), args.arm)
    print(_toml(asdict(result)).decode("utf-8"), end="")
    return 0 if (result.status == "FILE_CREATED_AND_READ"
        or result.status == "TASK_PASS" and result.report_truthful) else 1


if __name__ == "__main__":
    raise SystemExit(main())
