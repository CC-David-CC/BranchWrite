# Retain a committed model answer before the interpreter returns it

A model can finish and save its answer while BranchWrite has not yet recorded
the typed return in its workflow ledger. Restarting at that moment must recover
the same answer. It must not ask the model to do the work again or accept an
empty answer merely because a receipt survived.

## Changed boundary

The existing OperationJournal now atomically publishes the committed answer
object with its receipt, in its existing operation file. This is an additive
optional answer field in schema1, covered by record_sha256. Intent identity and
original request bytes do not change. Existing receipt-only records stay valid
for metadata recovery; they cannot prove exact answer recovery. No checkpoint,
native controller, COW history, workflow ledger or server format changed.

CowClient.read_completed_generation(operation_id) reads exact retained output
locally. It validates the operation receipt, source owner/branch/revision and
endpoint URL/pin, and checks any answer snapshot against the durable snapshot.
An absent/pending operation remains indeterminate. A receipt-only completion
raises ReceiptError. Neither path sends a request, rebuilds a transcript or
regenerates missing output. The normal completed request/replay paths now also
return saved answer bytes when present. They retain historical receipt-only
behavior for metadata callers; control consumers must use the strict read.

Only a checked durable complete response enters this cache. Provisional streamed
text is not replayed to the UI on local recovery. A durable partial model answer
remains partial: storing its tokens does not create EOS, finish a thinking result,
reset grammar or authorize a tool. completed_thinking_text still decides whether
a receipt-bound final with consumed EOS is eligible as control data. The host
continues to validate schema, relevant state, permissions and effects separately.

Conflicting repeat completions cannot replace an existing answer/receipt. Returned
objects are detached from journal data. Failing the completion write does not
produce a receipt-only local success. The native server may already have committed;
the exact original intent remains the reconciliation key, never a fresh work ID.

## Executed checks and limits

Ten focused checks use the actual COW CPU FlowModel coordinator, canonical Store,
HTTP server, client and actual CLI subprocess. No GPU/model is simulated as native
qualification. One test starts a separate producer Python process, receives/saves
its real HTTP result, and exits immediately with code73 before caller delivery.
A new Python process then reads exact output with its transport disabled. Native
CPU fixture trace remains unchanged. This tests a client-process boundary, not
inference-server restart, GPU numerical correctness or physical power loss.

The tests retain partial state, exact text/tokens/source receipt, detached reads,
wrong snapshot/endpoint/owner rejection, conflicting completions, legacy receipt
refusal and injected completion-write failure. A new wrong-owner test failed
before revalidation was added. Earlier failures remain in the private raw archive.
No existing test, tolerance or reference equation was edited.

## Remaining interpreter work

This is a necessary boundary for the general step/run interpreter, not that
interpreter itself. FrameKernel remains the one workflow authority. The model
invocation must retain its exact transport request before dispatch and record
partial native receipts without returning a complete ModelProposal to its caller.
A bounded FLOW can own successive EXPAND/CONTINUE native calls; only an actual
complete typed final may finish that FLOW. Do not add a second slot-return ledger
or use this response cache as conversation state.

The existing COW routes select named startup grammar states; no inline schema
admission endpoint was found. Use the inspected contract or implement a versioned
primitive before claiming dynamically generated per-call grammar support. A live
parser cannot be replaced when continuing a partial generation.

Receipt-only legacy records or a metadata-only recover() after a lost response
still cannot provide answer bytes through the strict local reader. Server-side
original-request reconciliation is a separate explicit operation; do not silently
send when reading. GOLDEN PATH currently refuses client-journal summary reuse at
its existing guard and still needs integration with retained answers. A caller
must establish the intended server/store/model identity; an out-of-band endpoint
pin is a host binding, not an independently verified attestation by this client.
Broad concurrent-writer, filesystem power-loss, Q8 and full VC/G qualification
remain outstanding. This change adds bytes to the existing atomic completion write,
not an extra model call or completion round trip; no performance claim was measured.

New thinking defaults remain1024; frozen512 successes are unchanged. Linux work,
private LAN Git only, chat server OFF, Q8 deferred.
