# BranchWrite human conversation controls

This bounded CPU fixture run validates the BranchWrite-local queue and
stop-and-amend path through the real Context COW Store, coordinator and HTTP
handler. The FIFO lives in one private BranchWrite chat state directory and is
sent to COW as subsequent turns after the current answer completes. The test
also exercises cancellation/publication races and recovery receipts.

Run from a BranchWrite checkout with its matching Context COW source available:

    PYTHONPATH="$BRANCHWRITE:$COW/experimental/branching_context/src:$COW" \
      python3 -m unittest discover -s tests -p "test_chat_cli_http.py" -v

Result: 6 passed, 0 failed, 0 skipped. This is not GPU cancellation, native
process restart, or installed-wheel evidence. See result.json and tests.log.

## Rerun on llm-60+ßuÁ‚ùÁT 2026-10-20

The exact private BranchWrite commit b1cd5578 and Context COW commit cffc8225
passed 12/12 combined chat-control and COW client-flow tests on llm-60, with
zero failures or skips. This includes the added client-death/local-queue case.
The test uses the real COW Store, coordinator, HTTP handler and CLI process with
a CPU FlowModel fixture; it does not run a model or GPU. The earlier six-test
result and its raw log remain unchanged. See rerun-result.json and
rerun-llm60-tests.log for this execution.
