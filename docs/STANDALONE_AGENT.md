# Standalone coding agent: goal and roles

Current source checkpoint (2026-10-20): BranchWrite source commit
9c275495 adds the human conversation CLI, a client-local FIFO for follow-up
messages, and stop-and-amend for an in-flight new user turn. Six CLI-to-HTTP
tests pass against the actual Context COW Store/coordinator/HTTP handler with a
synthetic CPU model; they cover queue ordering, cancellation races, durable
receipts and 128-byte identifiers. This does not qualify GPU cancellation or
native-state recovery, and the new chat flow has not been validated as an
installed wheel. The broader goal remains active: autonomous coding on unfamiliar
projects, client/server recovery, branch exploration, multi-client work and
deployment qualification remain. Earlier dated entries below are historical.

Owner direction, 2026-10-18: iterate on the client, server and harness until
BranchWrite is a reasonable standalone coding agent using Context COW's branches
and saved computation. L03 and later catalogue cases are diagnostic examples,
not the goal or a ceiling on capability. Multiple Linux client machines are
authorized; Windows only steers them.

## Keep project reference material current

For a new task, add `--refresh-context-pack` to the existing `branchwrite code`
command that supplies `--context-pack /absolute/path/to/PACK_ID` and
`--context-pack-id PACK_ID`. BranchWrite checks the original pack identity,
captures the same approved source selections and limits, and rebuilds changed
material into a new immutable pack alongside the old one. Unchanged material
keeps its exact original identity. The admitted launch records the refresh receipt
and resulting pack pin before COW bootstrap. New text requires a new prefill;
this does not make old computational state interchangeable.

Use a new `--state` directory. For interrupted work use `branchwrite resume STATE`;
resume retains the original setup and COW root even if external files changed.
A refresh request against an already admitted state fails before rebuilding.
Without this option, stale reference packs still fail new admission.

The option is explicit host policy, not automatic semantic compaction or model
authority to choose its own reference sources. Missing selected files, unsafe
paths, corrupt packs and mismatched pins fail rather than silently shrinking the
reference material. A captured statement can still be outdated or false; tools
must observe current files before editing. Existing grants and verification stay
in force. This feature is installed separately as dev24 on llm-49; dev23 is unchanged.
Dev24 has50 installed checks and a bounded two-task real-Q8 refresh workflow.
Its scope and timings are in CURRENT_STATE.md; this is not full certification.

## What each piece owns

| Piece | Role | Source of truth |
|---|---|---|
| BranchWrite CLI/client | Admit a task and grants, choose model/tool work, retain original operation IDs, run sandboxed tools, verify observations, and resume the workflow. | FrameKernel/RuntimeLog and exact artifacts. |
| Context COW HTTP server | Own immutable model histories and controllers, movable branch references, native execution leases, RAM/disk pools, expiry and checkpoints. | Canonical COW store; checkpoints are derived. |
| Strata native engine | Compute model frontiers, consume tokens/images and implement actual native state capture, sharing and restoration. | Validated backend state under the pinned execution profile. |
| VC/L audit runners | Supply independent expectations and observe effects, isolation, numerical results and work counters. | Retained executed evidence. They are not another runtime. |

BranchWrite consumes COW. A .bw file describes workflow control; it is not a
serialized KV cache. A tool returning zero or the model saying "finished" does
not independently prove the user's task complete.

## Current checkpoint: 2026-10-19, installed dev15

The current integration is feat/autonomous-inline-task-20261019 on llm-49.
The installed CLI talks to the pinned Q8/FP16-KV COW server on llm-60; it has no
model files. Older statements below about installed inference being unrun are
historical. Read CURRENT_STATE.md and validation/SC13-2026-10-19 for current facts.

The installed client now supports ordinary Git-project input without .git,
inline/file tasks, exact file or bounded directory grants, prepared-prefix reuse,
completed-context continuation, resume, status, complete review, export and guarded
new-copy apply with retry reconciliation. These all use the existing interpreter,
ledger and immutable model histories. They do not create another agent runtime.

SC13A passed autonomous code repair, six original methods and200 independent
cases plus the complete public handoff. SC13B independently repaired a different
multi-file project: eight original methods,200 generated cases and five invalid
classes passed. It reused the same15537-token generic root in a new native
process, with zero prefix forward work. Both full handoffs and stale-command
audits passed. This is bounded functional evidence, not a numerical oracle.

Broader unfamiliar repositories, several alternating clients, longer workflows,
combined cancellation/recovery/pressure, portable deployment and supported
matrix qualification remain. No GitHub publication or full certification claim.

## Current product progress

SC01-SC04 provide bounded real Q8 coding,grammar recovery,disk restore,remote CLI,new-file creation and completed offline resume evidence. code/resume are implemented and45focused CLI/HTTP controls passed. Installed client tool checks now pass;installed-agent inference remains unrun. See STANDALONE_CODING_STATUS.md and CLIENT_INSTALL.md. Broader projects,multiple clients/trees,project discovery/publication and combined qualification remain outstanding.

## Historical 2026-10-18 evidence checkpoint

At this checkpoint the implemented COW CPU suite has 669 passing methods, G0
has 51, and the split BranchWrite component rerun has 954 distinct passing
methods. The current Q4 profile's tiny, medium and 8K image/restart fixtures
have 363 exact full-vector comparisons with zero observed error. Individual
sampler families and the DRY/entropy combinations, including the 1K check,
passed their bounded GPU stages. These are executed bounded results, not full
VC or G certification.

The autonomous L00/L01/L02 reruns use frozen source c08869c and separate CLI
execution on llm-49 against llm-60. L00 completed its transport/file check but FAILED independent factual-report
acceptance: generated digits/path characters differed from actual observations.
Independent token decoding confirmed those strings were generated,not damaged
in transport. L01 passed its independent stream/status/binary audit. L02 passed
with an explicitly selected greedy profile and exact file bytes. L03 is prepared.
L00 needs a greedy rerun; no broader task reliability is claimed. Treat no prepared task as passed. The old full VC queue was deferred
at a completed-stage boundary to prioritize real agent work. Reconstruction,
pressure, fault, format, authorization and timing reruns still have explicit
pending status in the campaign admission receipt.

Keep source used by an active run frozen. Work in this separate integration
worktree while retaining the existing run's receipts. Preserve the existing
tests and original failure observations.

## Product work, not catalogue memorization

1. Establish the actual terminal/file loop and finish L00-L02 rechecks; use L03
   to probe selection of the right file, a scoped edit and truthful readback.
2. Admit an unfamiliar repository task through normal CLI configuration. Let
   the model discover files, edit, run actual tests and use failure feedback;
   the implementer supplies no patch or next tool action during the run.
3. Exercise several clients alternating independent trees on one GPU. Require
   exact operation identity, no cross-branch observations and serialized native
   execution. Later multiple GPUs may execute one request each.
4. Measure saved-prefix reuse using native work/residency counters rather than
   assuming every fork remains resident. Include branch changes and retry.
5. Repair general tool, prompt/example, grammar or recovery shortcomings exposed
   by those runs. Capture genuine model failure classes in the private LoRA
   candidates collection; protected workload answers are not training pairs.
6. Package a reproducible CLI launch and honest supported boundaries. Broader
   cancellation/crash/pressure and unfamiliar-task testing follow actual usable
   workflows; full certification remains separate.

New admissions use4096 thinking tokens and greedy first. Min-P and DRY are
explicit later fallback profiles;no automatic sampler ladder is qualified yet.
An existing exact DRY preset test now requests that preset explicitly and retains
all its numerical assertions. This is an owner-requested default change,not a
relaxed backend test. Earlier explicit profiles and controllers remain unchanged.
 earlier explicit
profiles and saved controllers remain unchanged. Keep the normal chat server OFF.
No GitHub or Strata publication is authorized. Commit and back up to private LAN
box-git only. Do not silently replay uncertain tool effects or reset model state.
