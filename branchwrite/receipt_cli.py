"""Offline inspection of one complete client-retained Context COW generation receipt."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from .cow_client import CowClient, CowClientError, OperationJournal


def inspect_receipt(state, operation_id, *, show_answer=False):
    """Read and validate one locally journaled text-generation receipt; never call COW."""
    journal = OperationJournal(Path(state) / "cow-operations")
    record = journal.read(operation_id)
    if record is None:
        return 2, {"schema": 1, "status": "NOT_FOUND", "operation_id": operation_id}

    if record.get("method") != "POST" or "/cow/text/" not in str(record.get("path", "")):
        raise ValueError("receipt inspection currently supports text-generation operations only")

    if record.get("state") != "complete":
        return 3, {
            "schema": 1,
            "status": "UNRESOLVED",
            "operation_id": operation_id,
            "request": {
                "path": record.get("path"),
                "branch": record.get("branch"),
                "revision": record.get("revision"),
                "body_sha256": record.get("body_sha256"),
            },
            "next_action": (
                "Inspect branchwrite status for this state. Keep the original operation ID; "
                "this local journal does not prove whether COW committed."
            ),
        }

    endpoint = record.get("endpoint_url")
    if type(endpoint) is not str or not endpoint:
        raise CowClientError("completed receipt has no pinned endpoint URL")
    client = CowClient.http(
        endpoint,
        journal=journal,
        endpoint_pin=record.get("endpoint_pin"),
    )
    result = client.read_completed_generation(operation_id)
    answer = dict(result.answer)
    answer_bytes = json.dumps(
        answer, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    text = answer.get("text")
    answer_view = {
        "available": True,
        "answer_sha256": hashlib.sha256(answer_bytes).hexdigest(),
        "text_bytes": len(text.encode("utf-8")) if type(text) is str else None,
        "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()
            if type(text) is str else None,
        "output_tokens": len(answer["tokens"]) if type(answer.get("tokens")) is list else None,
    }
    if show_answer and type(text) is str:
        answer_view["text"] = text

    branch = result.receipt.branch
    view = {
        "schema": 1,
        "status": "DURABLE",
        "scope": {
            "exact_saved_output": True,
            "current_gpu_residency_proven": False,
            "inference_repeated_during_inspection": False,
        },
        "operation_id": result.operation_id,
        "request": {
            "path": record["path"],
            "branch": record.get("branch"),
            "revision": record.get("revision"),
            "body_sha256": record.get("body_sha256"),
        },
        "cow_receipt": dict(result.receipt.raw),
        "branch_head": {
            "name": branch.name,
            "revision": branch.revision,
            "root": branch.root,
            "tip": branch.tip,
        },
        "model_contract_id": result.receipt.raw.get("model_contract_id"),
        "execution_profile_id": result.receipt.raw.get("execution_profile_id"),
        "answer": answer_view,
    }
    return 0, view


def command(state, operation_id, *, show_answer=False, as_json=False):
    try:
        code, view = inspect_receipt(state, operation_id, show_answer=show_answer)
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
        print("branchwrite: " + ascii(str(exc)), file=sys.stderr)
        return 2

    if as_json:
        print(json.dumps(view, sort_keys=True))
        return code

    print("Client receipt: " + view["status"])
    print("Operation: " + operation_id)
    if code == 2:
        print("No client operation with this ID is retained.")
    elif code == 3:
        print(view["next_action"])
    else:
        branch = view["branch_head"]
        print("COW branch: " + branch["name"] + " (revision " + str(branch["revision"]) + ")")
        print("Snapshot: " + branch["tip"])
        print("Model contract: " + str(view["model_contract_id"]))
        print("Execution profile: " + str(view["execution_profile_id"]))
        answer = view["answer"]
        print("Output tokens: " + str(answer["output_tokens"]))
        print("This proves a saved result, not that its KV state is currently resident on a GPU.")
        if answer["text_sha256"] is not None:
            print("Answer: " + str(answer["text_bytes"]) + " UTF-8 bytes; SHA-256 " + answer["text_sha256"])
            if not show_answer:
                print("Exact answer is withheld; add --show-answer to display it.")
            else:
                print()
                print(answer["text"])
    return code
