# Local queued-message recovery after client death

The test saves a follow-up message into the BranchWrite-local FIFO while a previous request is active, kills the sending client after COW has accepted the request, lets COW commit the answer, then starts a new BranchWrite process. Reconcile uses the original operation ID; once the earlier answer is recorded locally, BranchWrite drains the waiting message as the next turn.

The queue case passed three independent process-death runs. The complete chat CLI/HTTP suite passed 7 tests, the separate COW HTTP process-restart test passed once, and the COW client suite passed 17 tests: 28 executions, 25 distinct methods, no failures or skips.

This uses real client processes and real COW Store/coordinator/HTTP code with a deterministic synthetic CPU model. It does not test GPU/native KV restore or power-loss durability. See tests.log and result.json.
