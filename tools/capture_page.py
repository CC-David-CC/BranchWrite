"""Capture one host-approved HTML revision with the registered browser tool.

This command is for the trusted client/supervisor. Do not forward model-selected
browser executables or invent grants from model output. Current scope is a single
self-contained document under the Linux browser-host namespace boundary.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from branchwrite.browser_capture import BrowserConfig, PageInspection
from branchwrite.execution import Executor, Grant
from tools.run_cow_coding_pilot import _toml, _write


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--entry", default="index.html")
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--browser", type=Path, required=True,
                        help="Host-selected existing Chromium; sandbox cannot be disabled")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument('--check-module', type=Path, help='Host-selected protected assertion module')
    parser.add_argument('--check-sha256', help='Exact reviewed assertion module identity')
    parser.add_argument('--check-target', choices=('H03', 'H04', 'H05', 'H06'))
    args = parser.parse_args(argv)
    values = (args.check_module, args.check_sha256, args.check_target)
    if any(value is not None for value in values) and any(value is None for value in values):
        parser.error('page inspection requires module, SHA256 and target together')
    inspection = None if args.check_module is None else PageInspection(*values)
    config = BrowserConfig(executable=args.browser, inspection=inspection)
    grant = Grant((), False, capture_paths=(args.entry,))
    executor = Executor.create(args.source, args.output, browser=config)
    result = executor.capture_page("capture", grant, args.entry, args.expected_sha256)
    png = result.image.read_bytes()
    _write(executor.run_dir / "capture.png", png)
    receipt = dict(operation_id=result.operation_id, source_path=result.source_path,
        source_sha256=result.source.sha256, source_bytes=result.source.size_bytes,
        source_artifact=str(result.source.path), image_artifact=str(result.image.path),
        image_sha256=result.image.sha256, image_bytes=result.image.size_bytes,
        width=result.viewport[0], height=result.viewport[1], browser_version=result.browser_version,
        browser_executable=str(config.executable), chromium_sandbox=result.chromium_sandbox,
        url=result.url, http_status=result.http_status, served_sha256=result.served_sha256,
        elapsed_seconds=result.elapsed_seconds,
        scope="isolated single-document capture; host-selected checks; no assets or model-vision claim",
        isolation_kind=result.isolation['kind'],
        isolation_pid_namespace=result.isolation['pid_ns'],
        isolation_net_namespace=result.isolation['net_ns'],
        isolation_mount_namespace=result.isolation['mount_ns'],
        isolation_launcher_pid=result.isolation['launcher_pid'],
        isolation_worker_exited=result.isolation['worker_exited'],
        isolation_namespace_empty=result.isolation['namespace_members_after'] == [])
    if result.inspection is not None:
        receipt.update(inspection_target=result.inspection['target'],
                       inspection_sha256=result.inspection['inspector_sha256'],
                       inspection_status=result.inspection['status'], inspection_error=result.inspection['error'],
                       inspection_actions_json=json.dumps(result.inspection['actions'], separators=(',', ':')))
    data = _toml(receipt)
    _write(executor.run_dir / "capture.toml", data)
    sys.stdout.write(data.decode("utf-8"))
    return 1 if result.inspection is not None and result.inspection['status'] == 'FAIL' else 0


if __name__ == "__main__":
    raise SystemExit(main())
