# BranchWrite durable client receipt recovery

This campaign extends the source-context crash test with the critical client-side
receipt gap: Context COW has durably committed a generated answer and BranchWrite
has fsynced the exact answer plus COW receipt into its local operation journal,
but the BranchWrite process dies before the workflow ledger records the returned
value.

## What the test proves

test_client_recovers_source_and_committed_answer_receipts uses a real BranchWrite
CLI process against the Context COW HTTP API and canonical Store with a deterministic
CPU model fixture.

1. The client is killed with exit 78 after the selected project/branch snapshot is
   durable but before the outer source receipt is published.
2. branchwrite context-status reports a recoverable snapshot candidate. With the
   HTTP server stopped, a new client process verifies the embedded receipt and
   reuses the pre-crash frozen files and COW branch tip. Changed project bytes are
   excluded.
3. The test restarts the HTTP server on the same coordinator/store. A second client
   is killed with exit 79 immediately after OperationJournal.complete durably
   stores a bwnative-* generation answer and receipt, before the workflow ledger
   receives that return.
4. branchwrite status identifies the exact pending operation. The journal record
   reopens with a validated complete answer and matching COW snapshot receipt.
5. The HTTP server is stopped and BW_COW_API_KEY is removed. A new process runs
   branchwrite reconcile STATE --operation-id ORIGINAL_ID successfully from the
   client journal; it reports the committed snapshot and does not advance workflow.
6. The HTTP server is recreated against the same still-running coordinator/store.
   branchwrite resume records the original result into the workflow. The COW
   branch head and fake backend forward-token counter do not change during this
   recovery; the saved source branch also remains unchanged.

The CLI code and COW receipt path are exercised. The deliberate failure is placed
after the journal's file and directory fsync, not before it.

## Results and limits

The focused BranchWrite suite passed 71 tests. The real local COW HTTP integration
suite passed 8 tests, including this expanded process-crash scenario. Raw logs and
machine-readable counts are beside this file.

The model backend is deterministic CPU test machinery. This is not Q4/Q8 inference,
model-quality evidence or a GPU run. BranchWrite processes are killed/restarted;
the COW HTTP server is stopped/recreated, but its coordinator, Store and fake native
backend remain alive in the test process. This does not prove a COW/native process
restart, host reboot, power-loss durability, state-directory loss, disk-full
recovery, tool-effect reconciliation, or broad coding-task reliability.
