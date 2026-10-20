"""Run client/server setup regressions with exact per-method evidence; no GPU."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

MODULES = [
    "tests.test_project_scope_review", "tests.test_project_file_scope", "tests.test_project_checks", "tests.test_guided_project_start",
    "tests.test_client_setup", "tests.test_client_setup_cow", "tests.test_guided_cli", "tests.test_default_session_cli", "tests.test_unfinished_task", "tests.test_model_pause", "tests.test_model_dispatch",
    "tests.test_coding_launcher", "tests.test_coding_launcher_http", "tests.test_coding_reconciliation",
    "tests.test_generation_stream_uncertainty", "tests.test_cow_client_flow", "tests.test_full_project_review", "tests.test_project_export",
    "tests.test_project_apply", "tests.test_apply_reconciliation", "tests.test_project_baseline",
    "tests.test_file_tools", "tests.test_program_cli", "tests.test_base_catalog_publication",
    "tests.test_base_pack_freshness", "tests.test_shell_admission",
    "serve.test_cow_connection_info", "serve.test_cow_http", "serve.test_cow_http_pause", "serve.test_cow_http_publication_errors",
    "serve.test_cow_http_pool_trace",
]
MODULES += [
    "tests.test_base_project_prepare", "tests.test_project_context_receipt",
    "tests.test_project_context_real_cow_restart", "tests.test_cow_http_process_restart",
    "tests.test_chat_cli_http", "tests.test_receipt_cli", "tests.test_coding_status",
    "tests.test_coding_sampler_choice", "tests.test_cow_client", "tests.test_base_choice_http",
    "tests.test_workspace_versions", "tests.test_session_ledger", "tests.test_interactive_control",
    "tests.test_interactive_terminal", "tests.test_interactive_session", "tests.test_plan_mode",
    "tests.test_interactive_outcomes", "tests.test_guided_conversation", "serve.test_cow_grammar_canonical_flow",
    "serve.test_cow_history_counts", "test_store_branch_catalog",
]



class Results(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.outcomes = []
    def addSuccess(self, test):
        super().addSuccess(test)
        self.outcomes.append(dict(id=test.id(), status="PASS"))
    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.outcomes.append(dict(id=test.id(), status="FAIL", detail=self._exc_info_to_string(err, test)))
    def addError(self, test, err):
        super().addError(test, err)
        self.outcomes.append(dict(id=test.id(), status="ERROR", detail=self._exc_info_to_string(err, test)))
    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.outcomes.append(dict(id=test.id(), status="SKIP", detail=reason))
    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err is not None:
            self.outcomes.append(dict(id=subtest.id(), status="FAIL", detail=self._exc_info_to_string(err, test)))


def sources(root, cow):
    files = list((root / "branchwrite").rglob("*.py"))
    files += [root / "pyproject.toml", Path(__file__).resolve()]
    for name in MODULES:
        folder = cow if name.startswith("serve.") else root
        if name == "test_store_branch_catalog":
            folder = cow / "experimental/branching_context/tests/implementation"
        files.append(folder / (name.replace(".", "/") + ".py"))
    files += list((cow / "experimental/branching_context/src/context_time_travel").rglob("*.py"))
    files += list((cow / "serve").glob("cow*.py"))
    return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(files)) if p.is_file()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cow-source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    cow = args.cow_source.resolve(strict=True)
    output = args.output.absolute()
    output.mkdir(parents=True, exist_ok=True)
    extra = [str(p) for p in (root, root / "tests", cow, cow / "tools",
                              cow / "experimental/branching_context/src", cow / "experimental/branching_context/tests/implementation")]
    sys.path[:0] = extra
    os.environ["PYTHONPATH"] = os.pathsep.join(extra + [os.environ.get("PYTHONPATH", "")])
    os.environ["COW_CLI_SCRIPT"] = str(cow / "tools/cow_cli.py")
    os.environ.pop("BW_COW_API_KEY", None)
    os.environ.pop("BW_COW_CONNECTION", None)
    os.chdir(root)
    before = sources(root, cow)
    start = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="bw-setup-check-config-") as config, (output / "tests.txt").open("w") as stream:
        os.environ["XDG_CONFIG_HOME"] = config
        suite = unittest.defaultTestLoader.loadTestsFromNames(MODULES)
        result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=Results).run(suite)
    stable = sources(root, cow) == before
    report = dict(schema=1, status="PASS" if result.wasSuccessful() and not result.skipped and stable else "FAIL",
                  scope="Client setup, real PTY, CLI subprocess, CPU COW HTTP/admission/recovery. No language model, GPU or G1-G5 qualification.",
                  tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors), skips=len(result.skipped),
                  elapsed_seconds=time.monotonic()-start, python=sys.version, executable=sys.executable,
                  source_unchanged_during_tests=stable, source_sha256=before,
                  branchwrite_base=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
                  cow_base=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=cow, text=True).strip(),
                  tests=result.outcomes)
    (output / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k:v for k,v in report.items() if k not in ("tests", "source_sha256")}, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
