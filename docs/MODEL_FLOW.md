# Model requests belong to one durable invocation

The caller waits for an answer, not for an arbitrary network request to finish.
A long answer may need several requests. BranchWrite now keeps those requests
inside one model FLOW. Saving a partial answer does not tell the caller that the
answer is finished. After restart, it reads the saved result or reports the
original unresolved operation; it does not quietly ask the model again.

## Controller and native ownership

ModelAdapter, model_call/admit_model and step_model use the existing FrameKernel,
RuntimeLog and CowClient. A ModelOutput FLOW owns successive COWNativeReceipt
children: EXPAND first, then CONTINUE. Each native request closes only its own
child when the durable COW receipt is checked. The FLOW remains open across
partial requests. Only a complete output with consumed EOS can finish it and
fill its caller's named slot. No second workflow loop, slot-return ledger,
conversation transcript, model state representation or per-token Python loop
was added. Native parser/RNG/sampler/decoder state stays in COW.

Every step sends at most one native request. Host programs still decide when to
call a step and what to do with its result. Ready/Waiting/Closed ownership and
results come from the same canonical frame events. The added frames() inventory
is detached, read-only data for the owner thread, not worker authority.

The frozen model call binds an observed branch/revision/snapshot/root, actual
endpoint URL and host pin, model/execution identities, output format, settings,
request count, output-token and result-byte budgets. Its definition binds adapter,
client, action-guard and kernel source hashes. Frozen settings are passed to the
existing native request API; this does not implement another sampler.

Before send, a native child and exact request bytes are durable in the kernel.
The existing transport journal then persists original intent before HTTP/CLI send.
FrameKey binds the run, model invocation, parent, child, attempt, epoch and slot.
The result must match original source, endpoint, operation, root, revision and
model/execution profile. Native response JSON is retained as an opaque artifact,
not converted into an alternate transcript. This permits5001 output tokens without
forcing a token list through the typed codec's4096-item container limit.

## Partial answers and recovery

A partial result returns ModelStep(status='partial', value=None). The caller slot
stays empty. CONTINUE uses the last durable receipt's head, the same settings and
named grammar state. It does not append a new user message, reset the matcher,
resample old output or reinterpret a suffix. Plain text fragments combine in
request order; thinking final text comes only from completed_thinking_text's
receipt-bound view and consumed EOS guard, never parsed textual thinking tags.
Constrained output additionally requires native grammar_complete.

After the native reply is journaled but before the workflow return, restart reads
read_completed_generation locally and delivers the original result. After a
native child returns but before parent resumption, restart resumes the recorded
wait. Closed model FLOWs return their saved result without contacting COW. A bad
stored view is revalidated before any next request, so retry does not become a
hidden repair attempt. Non-EOS stops, malformed flags and exhausted byte budgets
cannot quietly launch more computation.

An absent/pending native response raises ModelReconciliationRequired with the
ORIGINAL operation ID. There is no automatic resend. Explicit original-request
replay was tested against real COW HTTP: the saved answer returns without another
CPU fixture forward invocation. Complete-only replay has no provisional token
callbacks; the client accepts its checked complete answer. When text fragments
are observed, they must still exactly match the committed answer. Fragments with
no durable completion remain indeterminate. No existing assertion was weakened.

One open model FLOW owns its branch after admitting its first native child,
including between settled partial requests. Ownership is derived from existing
parent/child records, not a new lease ledger. Another FLOW must fork or wait.
This logical ownership does not hold a GPU execution lease between requests.
Other branches can progress, and named sibling results can return in reverse order.
When the model FLOW completes, its logical branch ownership ends. Other clients
outside this interpreter remain protected by COW revision checks; this is not a
cross-process scheduler or global locking service.

## Bounds and supported interface

Initial modes explicitly name existing COW answer/ask/append-user boundaries.
There is no guessing/fallback to another route after an error. Subsequent partial
requests use the existing resume route. Budget exhaustion returns an explicit
budget_exhausted report with no complete ModelOutput and no new request. The
open turn remains owned. Budget amendment, abandonment/resource transfer and
ON handlers still need the general interpreter; do not close/drop unknown effects
merely to free the branch.

Formats are text, constrained and thinking. The last two require an explicit
named startup grammar. This uses the inspected COW grammar_state API; it does not
add inline/dynamic schema admission or attest the server's grammar configuration.
Host deployment must bind the intended static registry. Text is unstructured data,
not permission to execute a model-authored command. The tool registry/host grants
and protected verification remain independent boundaries.

The default native request limit1536 is a total-output request budget, not a new
thinking limit. NEW thinking registries still use1024 thinking tokens. Existing
512-token successes/controllers remain frozen. Request settings can name existing
samplers, but this component's executed integration scope is greedy CPU text.
Native grammar/thinking, samplers, images, seed/reseed, stops and Q4/Q8 need their
own combined checks. Existing image COW checkpoints may be sources; new-image
admission through this model adapter is not implemented.

## Evidence and remaining product work

The focused suite uses actual COW HTTP/coordinator/Store/client, with an explicitly
synthetic CPU FlowModel. It is not mocked GPU evidence. It checks partial/restart/
continue, client-reply-before-kernel-return, return-before-parent-resume, lost reply,
explicit original replay with no extra fixture work, stale sources, pending and
between-request branch ownership, reverse sibling completion, token/byte budgets,
profile incompatibility, detached inventory and5001 output tokens. Supplemental
framing fixtures check complete-only/mismatched/unterminated replies.

The generic task interpreter/program reader, model-driven tool-choice router,
protected completion verification, general CLI and core unfamiliar-task loop are
still missing. The module is a production model-invocation adapter on the single
kernel, not autonomous BranchWrite or full .bw language support. Basic H00-H06
remain bounded scripted/component passes; H07-H12/Ubuntu baseline are unrun.
GOLDEN PATH still needs its retained-answer reuse integration. Multi-process
scheduler ownership, controller matrix, server/GPU restart, long stress, power loss,
performance and original G1-G5/complete VC09 qualification remain separate.
Raw failures/results and source hashes are linked in the companion validation JSON.
Linux execution/private box-git only; chat OFF, Q8 deferred; no GPU job this ticket.
