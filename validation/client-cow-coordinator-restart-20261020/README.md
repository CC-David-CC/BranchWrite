# BranchWrite client receipts and conversation tip ? bounded integration evidence

This campaign exercises the user-side durable receipt path against the real Context COW Store, coordinator and HTTP server using deterministic CPU inference fixtures. The client is killed after COW commits an answer but before its local answer receipt is published. Both the BranchWrite client and the full COW coordinator/Store are restarted; `branchwrite reconcile` recovers the original operation under the same ID, records the exact answer locally, and adds no forward-token work. The receipt can then be inspected offline.

The flow also keeps a `user-conversation` tip current while a separate work branch remains pinned to the earlier shared snapshot. BranchWrite?s coding CLI captures that conversation tip into frozen project context. The flow accepts and persists 128-byte ASCII COW branch/operation identifiers; 129-byte identifiers are rejected. Grammar-state restart coverage accepts the existing 128-byte UTF-8 limit.

The logs contain the client receipt/status suite (33 tests), full BranchWrite/COW CLI and HTTP integration (13), focused conversation/name flow (5), COW branch catalog (10), and COW grammar canonical flow (10). The focused 5-test flow is also included in the 13-test integration run.

This is bounded CPU fixture evidence, not a GPU or native KV restart qualification, power-loss test, disk-full campaign, or full G2 certification. It does not establish that a general interactive chat command or GUI exists yet. Structured counts and source fingerprints are in `result.json`.
