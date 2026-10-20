# Implementation discipline

## Private work and publication

Routine commits and backups may go to private LAN box-git at
`git@box-git:/srv/data/git/BranchWrite.git`. Workers commit locally; the primary
agent reviews and pushes explicit private refs. Do not infer a destination from
`origin`. Any GitHub push, pull request, release or other publication requires
the owner's explicit approval and applicable review/checks first. Existing
public repositories or credentials do not authorize publication. Any proposed
Strata upstream contribution also waits for Niko's approval, confirmed by the
owner; do not contact Niko on the owner's behalf.

## One system

Use the actual repository. Follow inherited instructions. One local interpreter owns
admission, calls/returns, scheduling, grant checks, joins, budgets and dispositions.
Workers return observations, not workflow mutations. No daemon, frontend, distributed
control plane, transcript database or container stack is required. Prefer stdlib and
small existing native bindings; introduce a dependency only at a justified boundary.

The active contract is v0.6. Old seven-verb spellings are migration intent labels, not
a compatibility runtime. The model cannot define tools, grant capabilities, choose a
trusted continuation address, mark acceptance, or secretly change a decoder profile.
Do not claim universal test-time-compute optimality. Measure a stated budget objective.

## Native state

COW owns model context, snapshots, numerical state and native request receipts.
BW owns its workflow ledger and references to that state. No stateless chat/responses
replay fallback and no local shadow transcript as dispatch authority. No guessed wire
API. Record original intent before send; reconcile using original IDs and bytes.
Do not rerun a non-repeatable operation after a lost acknowledgment.

All mutable decode state belongs to one continuation. Share immutable weights and
compiled grammar tables only when the native backend proves the sharing safe. Fork,
rewind, restart, profile changes, active partial continuation, RNG and feedback require
explicit tests. Unsupported snapshot serialization is a blocker for the claimed exact
recovery mode, not permission to silently reset state.

## World boundaries

Inference placement grants no execution authority. Observe the actual llm-60 capacity
and lifecycle ownership; do not assume it is free or terminate unknown PIDs. Allocate
owned workspaces, scratch, caches, process identities and leases. Enforce isolation at
the OS/backend boundary, including links, inherited handles, credentials, descendants,
network and shared Git administration. Never treat a working directory as containment.

COMMIT publishes only through a configured guarded boundary. Never rewrite the user's
live checkout as if it were an atomic publication. ABANDON preserves already happened
effects and unresolved ownership. Release budgets/resources only with real settlement.

## LoRA failure-class collection

David requests that generalizable model failures be captured in the sibling
`branchwrite-lora-examples/candidates/` collection, even when longer prompts,
examples, grammar constraints or harness improvements work around them. Follow
that collection's README.md and COLLECTION-RULE.md. Preserve actual failures and
separate mitigation outcomes, exact provenance and a generator brief describing
new variants and independent checks. Label single observations honestly. Do not
export protected diagnostic answers, silently approve training pairs, train or
publish. Infrastructure/tool failures belong in engineering evidence, not a
mislabelled model-training pair.

## Evidence integrity

Keep source input bytes immutable. All 211 prior product obligations remain traceable.
JSON is supported for transport, evidence and explicitly selected schema-constrained
model output. The JSON bans were explicitly retired on 2026-10-17 because JSON
is now supported.
The canonical v0.6 workflow remains typed text; JSON support does not introduce a
second workflow ledger. Do not keep incompatible runtime formats merely to make old tests pass. Never weaken
an oracle because a design fails. Fix the abstraction, write the distinguishing test,
and disclose any remaining mismatch.

The reference package is a test oracle, not an implementation scaffold to ship as a
second runtime. Production tests must use real filesystem/process/native boundaries
where the catalogue requires them. Test count does not establish product quality.
Do not add a license on the owner's behalf. Keep private prompts, receipts and secrets
out of public artifacts and commits.

## Active execution placement (owner, 2026-10-17)

Windows steers SSH only. Edit, test, build, collect evidence and package on the
authorized Linux hosts. New model tasks use4096 thinking tokens (owner update2026-10-18).
The owner's newer ladder instruction advances on a verified task failure,even if
thinking closed naturally;budget exhaustion is recorded separately. Standard
budgets are4K/8K/16K/32K. Lite mode starts256 and is opt-in;its live retests are
deferred. Tool progress,infrastructure faults and unresolved effects do not
trigger automatic task retries. No no-thinking comparisons without request.
Keep the chat server OFF and Q8 deferred. Private LAN Git only.

Keep recorded512-token successes and frozen inputs unchanged. The new default
applies only at new generation admission, never to resumed controller state.
Natural-cutoff and broader end-to-end data collection are deferred.
