# Inspect a saved coding run

Use branchwrite status /path/to/run-state for a short summary.
Add --json for machine-readable output.

Status reads the canonical ledger locally. It requires no inference credentials,
server, GPU, original checkout or tool execution. It does not advance the run.
If another process owns the writer lock, wait for that process to finish and try
again. Status does not attach to a live writer or attempt to repair corrupt data.

recorded_verified is the verification result recorded at completion. It is null
for incomplete work. workspace_rechecked is always false: inspect/test the
current files separately before publication. Pending external operations are
listed by original operation identity; status does not retry them.

The internal FrameKernel replays the same canonical records used by execution.
No second workflow or status database is created. Large-ledger replay performance
remains unmeasured. Patch review/export and guarded application remain planned.

## Pending tool effects (source dev20)

JSON status adds `pending_tool_recovery` alongside the existing pending-operation
and model-recovery fields. `outcome_unknown` means a dispatched tool has no
durable result; it does not mean success or failure. `awaiting_settlement` means
a result is recorded but resource settlement remains incomplete. Both report
`automatic_replay: false` and retain the original operation ID. Human status
explains that model-reply reconciliation does not recover a tool effect, and
matching file contents alone do not prove the outcome. No tool receipt, process
or network is opened by status. Existing live-writer exclusion remains in force.

Three new red-first controls and21 combined source checks passed. This read-only
explanation does not implement tool reconciliation and is not yet packaged.


## Recent activity after a crash

`branchwrite status STATE --tail 12` prints a bounded summary of the latest
committed events from the existing workflow ledger. It identifies actions and
original operation IDs without printing prompts, model output, shell output or
artifact contents. Use `branchwrite receipt` for a committed model answer and
the relevant review/receipt command for tool results. A missing event is not
evidence that an uncertain external effect did not happen.
