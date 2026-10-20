# BranchWrite dev32 status-tail evidence

Source client code: `38abad675a24da773a3be1df8367d576b0be45ea`
Test assertion follow-up: `d7ec1a8b90882240cf8fa63287173e0876e4243b`
Private branch: `feat/explicit-model-reconciliation-20261019`

A user can now inspect where a run stopped with:

~~~bash
branchwrite status RUN_DIRECTORY --tail 12
~~~

This uses the existing workflow ledger. The default shows the last 12 committed
steps; the accepted range is 0-64. It reports step names, frame IDs and original
operation IDs, but omits prompts, model responses, command output and artifact
contents. JSON has the same information under `recent_activity`. This is a
bounded user-facing recovery view, not a new event store.

Executed evidence:

- 87 focused BranchWrite CPU tests passed; no failures, errors or skips.
- 8 Context COW HTTP integration tests passed; no failures, errors or skips.
- A clean dev32 wheel install passed CLI, status and receipt help checks.
- The installed wheel's status command was exercised against an ephemeral
  typed-ledger fixture and returned the exact ordered event tail and original
  operation ID without payloads.
- The client doctor passed. No inference was run; llm-60 GPU0 remained idle.

The HTTP integration uses a deterministic CPU fake and does not restart the
Context COW coordinator, Store or native process. It does not certify Q4/Q8
inference, model quality, speed, power-loss recovery or all BranchWrite workloads.
For exact saved model output, use `branchwrite receipt`; status activity omits
output contents by design.

See `result.json` and the raw test logs here. Wheel:
`/home/dflanag3/spatial-artifacts/branchwrite-dev32-package-20261020-v1/wheel/`.
