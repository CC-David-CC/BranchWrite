# BranchWrite client context receipt recovery

BranchWrite owns the client-side workflow and frozen project-context receipt. Context COW
remains authoritative for canonical branch histories and computational checkpoints.
The native Strata-derived engine performs inference; the harness observes and verifies
the client/server boundary.

The test creates a saved branch in a local Context COW Store, starts the normal
BranchWrite code CLI, and terminates that client after its immutable source snapshot is
durable but before the outer receipt is published. The COW HTTP server is stopped. A
new client process recovers from the embedded receipt, publishes the context pack and
coding launch, and reports the saved stage through branchwrite context-status. It does
not reread changed project files or contact the stopped server.

When status reports SOURCE_SNAPSHOT_RECOVERY_CANDIDATE, rerun the original branchwrite
code command with the same state and source selections. BranchWrite verifies frozen
input hashes and reuses that snapshot. If status reports multiple orphan snapshots,
automatic recovery is deliberately not selected.

After offline recovery, the test recreates the local COW HTTP server against the same
CPU coordinator/store and runs the actual branchwrite resume command for one step. It
checks that the worker branch is created, the source branch is unchanged, and
branchwrite status can read the workflow ledger.

Executed results: 71 focused BranchWrite CPU tests passed on llm-49; 8 local Context
COW HTTP integration tests passed on llm-60, including this process-separated client
restart case. Raw logs and commands are in this directory and result.json.

The fake backend is deterministic CPU test machinery. The initial offline recovery
stubs run_saved, then the real resume command runs against the restarted HTTP server.
The COW coordinator/store and native test backend themselves remain in process. This
does not establish Q4/Q8 behavior, full server/native process restart, model quality,
or full crash certification.
