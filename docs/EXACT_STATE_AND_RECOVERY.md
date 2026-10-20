# Exact state means exact dependencies, not a global revision

Example: A and B both derive from source S. A later records an observation in its own
scope. B's frozen plan depends on S, its native snapshot, grammar/profile and its world
lease—not on “the latest event anywhere.” A's unrelated progress must not stale B.
Changing S, B's relevant preimage, policy, lease or model state must stale B.

A plan binds typed dependency keys and immutable values/versions. A grant binds plan hash,
resources and policy. Dispatch validation and the resource mutation need a real checked
boundary. Process action dependencies include effects beyond explicit file reads: executable,
environment, config, protected tests and authorized external state.

A conditional result needed by a later action is not known when the earlier FLOW is authored.
Freeze that later computation after the result is observed. Keep the program definition
immutable while its distinct invocation plans bind actual values. No skip-staleness flag.

## Required durable return test

Admit parent P, child C and named slot S under epoch E atomically. Record the child's exact
native/effect request and resulting receipt/artifact. Validate typed result R. Publish its
artifact, then durably record eligible return binding (C,E,S,R). Kill the campaign-owned
runtime **before** parent resumption. Reopen from ledger/artifacts and the real native owner.

The recovered P has the same locals, program location, slot and epoch. It consumes R once,
does not redispatch C or regenerate R, retains C's original history, and resumes only once.
Repeat with two siblings completing in the reverse order and a duplicate delivery. A late
old-epoch result remains history but cannot satisfy a current slot. Wrong-child, wrong-type,
wrong-result or conflicting duplicate are explicit failures.

The offline reducer/codec test models this contract without performing a native request.
The product test must use the actual native session and a real child effect.

## Required decoder recovery test

Generate a committed active partial that stops in the middle of a `.bw` record or UTF-8
sequence as supported by the native token contract. Snapshot its grammar progress, sampling
state, native numerical state, stop/turn state and original receipt identity. Fork exact
replay branches, continue in interleaved order, restore after a client/process restart,
and compare against the declared native equivalence oracle.

Test serialization incompatibility, missing checkpoint, failed receipt recovery and changed
model/tokenizer/profile. Never silently reset to grammar root, reseed the sampler, clear
DRY, reset mu/EMA or rebuild a stateless conversation. Report capability unavailable when
sufficient native state cannot be recovered. New reconstructed lineages are explicit work.

## Separate failure boundaries

Before intent; after durable intent before send; during provisional stream; after native
commit before receipt; after effect before observation; after artifact before ledger;
after child return before parent resume; after publication before acknowledgment.

An unknown external effect retains its ownership and reservation. ABANDON cannot make it
nonexistent. Known process termination, reference state, idempotency receipt or other
qualified reconciliation evidence is needed. No universal exactly-once guarantee is made.

## Executed tool process boundaries, 2026-10-19

The installed dev18 package passed three real Linux SIGKILL cases (not simulated
exceptions): before dispatch, after a real file creation but before durable
return, and after durable return before parent resumption. Together with five
existing dispatch controls, eight checks pass. See
validation/TOOL-PROCESS-RECOVERY-2026-10-19/ for logs and the exact scope.

Before dispatch, restart executes once. After durable return, the existing
result supplies the exact parent slot and parent resumption occurs once. In the
middle gap, the created file is retained and the original operation stays
Waiting. Restart refuses to execute it again. This is safe refusal, NOT automatic
effect recovery. The tests never infer an acknowledgment from matching file
contents. Arbitrary shell/browser external effects are not qualified by a file
creation fixture. No original gate, full CLI crash campaign or GPU certification
is claimed from these tests.

Remaining engineering work is qualified reconciliation of original tool effects
when a complete owner receipt exists, and an explicit human-facing unresolved
status otherwise. Missing receipts must never be filled with guessed results
or a new operation ID. Keep this within the one canonical workflow and existing
tool ownership; do not create another workflow runner or shadow model history.

## Streamed errors without completion proof (source dev21)

A failed stream can leave its original model request pending. The server may have
published some consumed state before failure; an error event alone proves neither
a complete result nor a durable abort. Keep the operation ID and original request
bytes. Do not reset the journal, invent a receipt, or silently resend it.

GenerationIndeterminate is an OperationIndeterminate carrying that original ID.
Error/failure events and EOF without a complete receipt now use this type. On the
first such failure the CLI returns4, prints the original ID and known failure cause,
and points to explicit reconcile followed by resume. A recovered complete receipt
may resume normally; absent proof remains unresolved. This improves reporting,
not durable-abort recovery. HTTP rejection responses are explicitly closed.

Source validation includes5new transport/reporting/resource checks,16existing client,
13launcher,6base-selection,15model-flow and6CLI reconciliation checks. One recovery
fixture's setup expected the old RequestRejected category. Its setup now requires
GenerationIndeterminate and the exact original ID; all no-replay,ledger-integrity and
exit4 assertions remain. The initial failed run is retained. No model/backend test,
numerical equation or tolerance was weakened. Installeddev19/dev20 and their pending
runs are unchanged; source dev21 is not a migration or completed GPU qualification.
