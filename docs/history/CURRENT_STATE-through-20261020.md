## Paused 2026-10-20 ? current entry point

Read [HANDOFF-2026-10-20-PAUSED.md](HANDOFF-2026-10-20-PAUSED.md) before resuming. Owner requested pause. Current dev38 client CPU integration passed296/296 and candidate COW G0 passed51/51; four real Q4 usability journeys used the older pinned live server. Two coding tasks completed selected checks but still need independent audits; household conversation did not reach coding; fleet SSH/SCP did not complete and the UI hid the honest failure report. Active coding is not yet steerable from the same terminal. Candidate server rollout failed its execution fingerprint and was rolled back. No cumulative G1?G5 claim. No new work until resumed.

# Current checkpoint: queued user messages survive a BranchWrite client crash (2026-10-20)

BranchWrite stores messages typed during an active answer in a private, checksummed local FIFO. A new process first reconciles the in-flight operation using its original ID. After COW confirms the saved answer, BranchWrite commits that receipt locally and sends queued messages in order. The server does not own this client queue.

Executed on 2026-10-20: the process-death queue test passed 3 independent runs; the full chat CLI/HTTP suite passed 7 tests, the separate COW HTTP process-restart test passed once, and the COW client suite passed 17 tests. Total 28 executions across 25 distinct methods, 0 failures/skips. Evidence: validation/chat-queue-client-restart-20261020/. The queue test uses real BranchWrite subprocesses plus actual COW Store/coordinator/HTTP code and a deterministic CPU model fixture. It does not establish GPU inference, native KV recovery, power-loss durability, or a generally autonomous coding run.

# Current checkpoint: BranchWrite receipt recovery after actual COW process restart (2026-10-20)

BranchWrite is the user-facing coding client: it holds the human's local workflow state, queued messages, work ledger, and client operation IDs. Context COW is the server-side canonical owner of conversation histories, branches, and durable receipts. The native Strata-derived engine performs inference and owns KV state. The validation harness drives the real client/server interfaces, injects failures, and checks receipts and work counters.

The BranchWrite client now recovers a committed answer after both the client and COW HTTP service have died. Reusing the original operation ID returns the saved answer. Receipt comparison checks required branch and snapshot identities and rejects conflicts in shared fields. A later user turn continues from the saved prefix.

Executed 2026-10-20: five independent OS-process restart runs passed; 17 COW client tests and 6 chat CLI/HTTP tests passed. Total 28 test executions, 0 failures, 0 skips. Evidence: validation/cow-http-process-restart-20261020/. The test uses real COW Store/coordinator/HTTP code and a deterministic CPU model fixture; GPU inference, native KV restore, and power-loss durability remain unqualified. Source is private on feat/explicit-model-reconciliation-20261019; no GitHub or Strata publication.

# Current checkpoint: human conversation queue and amendment controls (2026-10-20)

BranchWrite commit 9c275495 adds a local FIFO queue and stop-and-amend command to
the user conversation CLI. The queue is private to one BranchWrite chat state
directory; it is dispatched to COW after the active assistant turn completes.
There is no server-side shared queue. Stop-and-amend asks COW to cancel the exact
in-flight new-turn operation, then checks whether cancellation or durable
publication won before retrying or submitting the added detail as a later turn.

Executed evidence: validation/chat-human-controls-20261020/. Six tests pass,
zero failures/skips, against the real COW Store/coordinator/HTTP handler and a
synthetic CPU model, using COW source commit 831b4d8d. This validates local FIFO
ordering, stop/cancel race handling, operation receipts and 128-byte IDs. GPU
cancellation, native process restart and installed-wheel behavior for this chat
flow remain unqualified.

# Current checkpoint: client context recovery across COW coordinator restart (2026-10-20)

The client receipt and bounded activity-tail commands are implemented in BranchWrite dev31/dev32. This additional integration closes the Context COW coordinator itself, reopens the same durable Store, verifies that the saved source branch still points to the identical tip, then builds and recovers BranchWrite's frozen project context after a client crash.

Evidence: `validation/client-cow-coordinator-restart-20261020/`. Sixteen client receipt/status tests and eight local HTTP integration tests passed with zero failures or skips. The integration uses a deterministic CPU backend and real COW Store/coordinator/HTTP code. It does not test GPU inference or native KV restoration. Both coordinator restarts close and reopen the coordinator and Store in the test process. The COW HTTP listener is recreated in that same parent process; this is not an OS-process restart of the service.

# Current checkpoint: BranchWrite dev32 recovery view (2026-10-20)

The client now exposes both exact model receipts and a short activity trail for
resuming after a crash. `branchwrite status STATE --tail 12` shows the last
committed workflow steps and operation IDs without revealing prompts or output
artifacts. `branchwrite receipt` validates and displays the locally retained
COW answer receipt. `reconcile` and `resume` continue with the original
operation ID. Context COW remains the canonical server-side history owner.

Validation on 2026-10-20: 87 focused BranchWrite CPU tests and 8 actual local
Context COW HTTP integration tests passed, zero failures or skips. A clean dev32
wheel install exposes `status --tail`, `receipt`, `reconcile` and `resume`;
CLI help, status help, receipt help and client doctor pass. The real COW HTTP
integration still uses a deterministic CPU model fixture. It does not qualify
Q4/Q8 inference, full COW/native process restart, or power-loss durability.

The dev32 status-tail feature derives the last committed event summaries from the
existing typed ledger. It shows step/frame/original operation identifiers without
emitting prompts, command outputs or artifact contents. The receipt command
separately validates locally retained exact model output. Neither UI implies GPU
residency. The dev32 wheel is backed up at
`box-git:/srv/data/git/private_context_cow.evidence/branchwrite-dev32-package-20261020-v1/wheel/branchwrite-0.1.0.dev32-py3-none-any.whl` (SHA-256 5892f05cc96f7a74a6e72bf5a29bcb105ff8bc2d5bf163fe8ec9e42411edc15a). See `validation/client-status-tail-20261020/` and
`docs/manual/06_RECEIPTS_AND_RECOVERY.md`.

# Current checkpoint: BranchWrite dev31 client-side durable receipt

The user-side durable-receipt feature is in the BranchWrite client. Context COW
remains the canonical server for model histories and receipts; BranchWrite gives
the person operating the workflow a local, read-only way to inspect the exact
saved answer and resume after a client crash.

New command:
`branchwrite receipt STATE --operation-id ORIGINAL_ID [--show-answer] [--json]`.
It validates the locally retained generation answer and COW receipt without
contacting the server. Answer text is withheld unless explicitly requested.
Pending or unknown outcomes remain unresolved and must retain the original ID.
Status now prints the receipt command beside recovery guidance.

Validation on 2026-10-20: 84 focused BranchWrite CPU tests and 8 actual local
Context COW HTTP integration tests pass. The integration kills/restarts client
processes across source publication and committed-answer receipt boundaries,
inspects/reconciles the exact answer while COW HTTP is stopped and no API key is
present, then resumes the same workflow without another fake-backend forward or
branch movement. The test uses a deterministic CPU model fixture; it is not a
GPU/model quality, COW coordinator/native process restart, or power-loss test.
A durable answer receipt proves saved output, not current GPU residency.

Source work is being packaged as private dev31 on
`feat/explicit-model-reconciliation-20261019` in
`/home/dflanag3/src/branchwrite-model-reconciliation-20261019`. The tested dev31 wheel is backed up at
`box-git:/srv/data/git/private_context_cow.evidence/branchwrite-dev31-package-20261020-v1/wheel/branchwrite-0.1.0.dev31-py3-none-any.whl`. See `validation/client-receipt-cli-20261020/` and
`docs/manual/06_RECEIPTS_AND_RECOVERY.md`. Keep previous runs on their
versioned clients. GitHub/Strata publication remains out of scope.

---

# Current checkpoint: BranchWrite dev30 client receipt recovery (2026-10-20)

## Names and roles

- **BranchWrite** is the user-facing coding client. It owns explicit project grants,
  the workflow ledger, tool/worktree policy, client operation IDs and recovery UI.
- **Context COW** is the server and canonical owner of conversation histories,
  branch references, controller state and optional RAM/disk computational checkpoints.
- **Native Strata-derived inference engine** performs model computation and owns
  its native KV state.
- **Validation harness** drives the real client/server interfaces, injects
  controlled failures, checks invariants and stores evidence. It is not another
  agent or a canonical history store.

## Current BranchWrite work

Private source: llm-49:/home/dflanag3/src/branchwrite-model-reconciliation-20261019,
branch feat/explicit-model-reconciliation-20261019. Private bare remote:
box-git:/srv/data/git/BranchWrite.git. Latest source commit before this handoff
latest test commit: a3adf08b6af99491c03e7d71c8cae64f6bad86c1 (product source remains at b48b8ac9043cb8678329e83f1f6e57abf610c084). No GitHub or Strata publication.

The CLI can opt in to build a context from explicitly granted project files and
completed saved COW branch histories. It freezes those inputs, hashes them in a
durable client receipt, and binds the receipt hash to the coding launch. The client
does not scan an entire project. On retry, it reuses the original frozen bytes
and branch tip even if the live project or branch moves.

A client crash after the frozen source directory is durable but before the outer
receipt is published now appears in context-status as
SOURCE_SNAPSHOT_RECOVERY_CANDIDATE. The user can rerun the original code command
with the same state and source selections; BranchWrite verifies and reuses the
snapshot. Status shows the last durable log entries and the recovery instruction.

## Executed evidence

- 71 focused BranchWrite CPU tests passed on llm-49.
- 8 local HTTP integration tests passed on llm-60 with the actual Context COW
  coordinator, Store and HTTP API plus a deterministic CPU model fixture.
- The integration now exercises two client crash boundaries. First, it recovers
  frozen project/branch inputs after source-snapshot publication but before the
  outer receipt. Second, it kills BranchWrite after a bwnative operation's exact
  answer and COW receipt are fsynced in the client journal but before the workflow
  ledger records the result.
- After the second crash, status identifies the original pending operation.
  Reconcile succeeds while the COW HTTP server is stopped and without an API key.
  After the HTTP server is recreated, resume consumes the original local receipt:
  the COW worker head and fake-backend forward-token counter do not change during
  recovery, and the source branch remains unchanged.
- BranchWrite processes are genuinely killed and restarted. The HTTP server is
  stopped/recreated against the same in-process COW coordinator, Store and fake
  backend. This does not prove a COW/native process restart, GPU inference,
  power-loss durability or broad autonomous-task recovery.

Detailed evidence and raw logs:
validation/client-durable-operation-receipt-20261020/
Earlier source-pack evidence:
validation/client-context-recovery-20261019/
Installed dev30 package smoke evidence:
validation/dev30-client-package-20261020/

## Private dev30 package

Wheel built from source commit b48b8ac9043cb8678329e83f1f6e57abf610c084:
 /home/dflanag3/spatial-artifacts/branchwrite-dev30-package-20261020-v1/wheel/
 branchwrite-0.1.0.dev30-py3-none-any.whl
SHA-256: 9d71fb5ba0fa6b056145e416bb102f31b677f8f31ecd5ad2c5f6fe4a753ce19c.
An isolated venv installed the wheel; CLI help exposes project context and
context-status; doctor passed shell/file smoke checks with inference NOT_RUN.
This is a private preview, not a Q4/Q8-qualified installation. The same wheel
is backed up under box-git:/srv/data/git/private_context_cow.evidence/
branchwrite-dev30-package-20261020-v1/wheel/.

## Remaining qualification

No GPU/model inference ran for the client receipt change. No Q4/Q8 quality,
logit or speed claim follows. The old Q4 base profile is pinned to runtime source
commit 55cdfa9a2db1afcee40c340881b332656fb06d1e. Of its 257 declared runtime
source files, 23 differ from current COW source commit
895251441266dda1dd4d6437d98fda7251027b68 (14 experimental API, 8 serving, 1
tool file). Its calibration is NOT_RUN and it has no numerical qualification.
Build a new honest profile identity from current source before any Q4 run; do not
inherit tolerances or relabel the old profile.

The chat server remains off and llm-60 GPU0 is idle. The overall standalone-agent
objective remains active: broad real-model coding reliability, real COW/native
process restart, tool-effect reconciliation during live work, pressure/fault
qualification, and Q8 validation remain unfinished.
---

# Latest integration checkpoint: 2026-10-19

Authoritative BranchWrite: llm-49:/home/dflanag3/src/branchwrite-model-reconciliation-20261019,
private branch feat/explicit-model-reconciliation-20261019. Use docs/manual/05_HANDOFF.md
for installed versions and exact server/runtime locations. Historical entries below
retain their original versioned scope; old Q8-deferred statements are superseded
by the owner's subsequent Q8 authorization and recorded bounded campaigns.

103 current context/workflow integration tests pass, zero failures/errors/skips.
They exercise CPU inference fixtures and actual local HTTP, not real model quality
or numerical qualification. The initial client-host attempt had 16 dependency
errors; configured rerun and both logs are retained in
validation/context-workflow-integration-20261019. Separate real-Q8 recovery evidence
is in validation/project-base-three-builds-20261019-v1/dev25-q8-tool-recovery.

BranchWrite owns canonical workflow/tools; COW owns canonical model histories,
branches/controllers and derived RAM/disk checkpoints; native Strata computes;
the audit harness independently checks boundaries and outcomes. Normal coding CLI
works for bounded demonstrated tasks. Automatic Project Base selection, consultation
scheduling, refresh/compaction and host-approved adoption remain product work.
Do not describe the pure choice validator or question API as that scheduler.
The full standalone-agent objective and original gate qualification remain open.

---

## Separate dev25 recovery candidate

feat/tool-retirement-recovery-20261019 has an installed candidate with50 focused
source checks,20 installed recovery checks and G0 51/51. No dev25 GPU run yet.
The broader100-method run retains1known diagnostic-string failure (99pass).
Proof v2 rejects cross-ledger reuse. Small tool-dispatch measurement adds14.142ms
(+35.823%);whole-agent overhead remains unmeasured. Manual guides still use the
real-Q8-tested dev24 package. See docs/manual/05_HANDOFF.md and the candidate
branch validation/project-base-three-builds-20261019-v1/tool-retirement-recovery.

## Manual operation guides

Start with docs/manual/00_START_HERE.md for server startup, client install/connection, a copy-and-paste HTML task, native dependency inventory and current handoff. Use the tested dev24 wheel. New source-only tool-retirement recovery is isolated on feat/tool-retirement-recovery-20261019, not merged or installed.

## Latest real Q8: installed dev24 reference-refresh workflow PASS

Two successive two-file coding tasks passed through installed CLI49/HTTP/server60.
A:7 calls/1383 outputs/151.866s,5 visible methods+400 independent sequences.
B:10 calls/5345 outputs/434.570s,8 visible methods+800 independent sequences;
the800 include the same400 baseline sequences. Review/export/apply connected A
to B. Both loops ran without parent intervention;no rejected tool effects or
verified task failures. B's long4493-token response includes thought and output,
not4493 independently measured thinking tokens.

Three immutable pack versions were retained. New references produced a new root;
the previous branch/history stayed exact. Both completed states reopened with
server/tunnel stopped,no API key,identical results and unchanged state bytes.
Native generation40.320TPS excludes prefill/tools/HTTP/publication. No fresh
logit oracle or full certification claim. Server/native exit0,key revoked,GPU
free,chat OFF. See validation/project-base-three-builds-20261019-v1/dev24-q8-reference-refresh.

## New source checkpoint: explicit reference-pack refresh at coding admission

Source CLI now offers --refresh-context-pack for a new run with an existing
pinned pack. Changed approved sources become a new immutable pack and new root;
unchanged packs retain their ID. The launch freezes refresh provenance. Resume
keeps the original context; a refresh against an admitted state is rejected
before creating a new pack. Automatic lifecycle scheduling, semantic compaction,
base choice/adoption and multi-base consultation remain separate unfinished work.
Installed dev24 is available separately on llm-49 at
/home/dflanag3/spatial-artifacts/branchwrite-dev24-package-20261019-v1/venv/bin/branchwrite.
Source849de09f95438feb72697b251288cd885ca9996a; wheel SHA256
6ea1b1cfe521a1349310f71811eb403d3c8dff61ea58a2780eba0d4a43824537.
All44 installed modules match the wheel;50 installed checks pass. Source63
pack/HTTP checks and46 additional CLI checks pass; G0 remains51/51. These counts
overlap. The bounded two-task dev24 GPU workflow now passes as scoped above. Installed dev23 is unchanged.
See docs/STANDALONE_AGENT.md.

Latest real-Q8 control drill: the normal server6647ae46 passed startup source
verification, then installed dev23 recovered from a deliberately grammar-forced
premature finish. Real host verification rejected missing command evidence;
one COW fork returned to the earlier root, increased the thinking rung4K to8K,
and completed read/read/edit/test/finish without parent intervention.
52 closed frames,108.590 seconds,1,004 independent integer/edge cases passed.
This is a forced recovery control, not a natural model-quality failure or fresh
numerical oracle. Both processes exited0, temporary access was revoked, GPU
is free, chat remains OFF. Private evidence:
validation/project-base-three-builds-20261019-v1/dev23-q8-failed-finish.

## Current checkpoint: installed dev23; bounded real Q8 restart + coding PASS

The standalone-agent goal remains active. This section supersedes older current
headings below; those are retained as dated history.

- Client: BranchWrite installed on llm-49 at
  /home/dflanag3/spatial-artifacts/branchwrite-dev23-package-20261019-v1/venv/bin/branchwrite.
  Exact wheel source:c5fdb874436fb712d7ba443a156df08a325a1671.
  Wheel SHA256:9e0dd41651edb73f2a919322a1cb7212f27ae3b830d67d9f10da85c1da448a66.
- Client source: /home/dflanag3/src/branchwrite-model-reconciliation-20261019,
  feat/explicit-model-reconciliation-20261019; private box-git:/srv/data/git/BranchWrite.git.
- Server: Context COW source on llm-60 at
  /home/dflanag3/src/context-cow-persistent-operation-status-20261019,
  fix/persistent-text-operation-status-20261019;
  private box-git:/srv/data/git/private_context_cow.git.
- The qualified Q8 run used server source2a083b85308416b3563224778e9620c301ea45e1,
  execution profile cde1bbe9584a6bc8c8268dab5a297c893e744ff333633fdc29c7792b0bbaa098.
  Later source edits are not retroactively GPU-qualified.
- Native Strata owns inference and computational state; COW owns canonical
  histories/controllers, branches and derived RAM/disk checkpoints; BranchWrite
  owns workflow admission, original IDs, sandboxed tools and the RuntimeLog.
  Audit runners observe and check these systems, not another agent runtime.

### What the current installed path demonstrated

The ordinary coding CLI prepared15,780tokens, lost its root acknowledgment,
exited, then reconciled the same original ID after actual server/native restart.
Reconciliation took0.400954 s, made0 native commands and did not change the workflow
ledger. The subsequent native load restored15,780consumed tokens with0 prefix
forward work. BranchWrite then repaired a small project autonomously in53.090 s.
Only owned calculator.py changed; originals/protected tests were unchanged.
Visible tests and1,004 independent integer cases passed. Public review/status passed.

Native generation:475 tokens at53.974 native timed TPS. This excludes tools,
new suffix prefill, persistence and client overhead; it is not whole-agent TPS.
Two earlier harness/backend failures remain retained. The typed-text root
comparison defect was reproduced, fixed and retested. No fresh logit oracle
or original G1-G5 qualification follows. See
validation/project-base-three-builds-20261019-v1/dev23-q8-restart-coding.

All 44 installed module bytes match the wheel;64 installed client checks pass.
Current source lost-bootstrap recovery checks34 pass. The typed-root fix has
43 related CPU checks and G0 51/51. Counts overlap and are not coverage percentages.

### Product boundaries and priorities

The CLI supports code/resume/status/review/export/apply/reconcile, explicit
prepared-prefix or completed-tip forks, host-proposed base selection and
context-pack pins. It retains immutable setup and original operation IDs.
Acknowledged bootstrap recovery and explicit unacknowledged bootstrap
reconciliation are implemented. Unknown work remains unresolved, never resent
as a fresh task. Sampler presets are greedy, Min-P and DRY+Min-P; arbitrary
profiles remain available through explicit host workflow configuration.

Project Base APIs provide independent questions, observation refreshes and
pack-backed rebuilt versions. Pack refresh preserves old identities. Normal
coding admission can pin a pack or host-approved catalog choice. Automatic
base proposal/selection, refresh scheduling, compaction/adoption, multi-base
consultation and task-breakdown dispatch are not integrated. The validated
breakdown parser is not an execution scheduler.

Next substantive work includes broader failed-attempt/branch exploration,
broader unfamiliar projects and repeated clients/trees, source-pinned normal
serving/deployment, and explicit base lifecycle integration. Advanced parsed
workflow forms are not all executable. Tool-effect reconciliation, broader
crash/pressure, sanitizer/soak and compatibility campaigns remain outstanding.
Prior H/L/SC reports retain their own versioned scope.

The research server is stopped, GPU free, temporary SSH key/tunnel removed and
chat OFF. There is no stable serving endpoint implied by the installed CLI.
All work stays on Linux/private LAN Git; Windows only steers. No GitHub/Strata
publication is authorized. Do not read another live writer's RuntimeLog.

Latest server source6647ae46 adds normal startup verification of declared
runtime source pins. Its56 CPU serving/source checks and G0 51/51 pass. A later
normal-entrypoint Q8 control drill verified56 declared source files at startup
and completed autonomous recovery; it does not retroactively qualify all native
numerics for this new profile. It verifies source files at
startup, not during token generation; undeclared legacy source pins remain
explicitly unverified.

Everything below is historical unless explicitly reaffirmed above.

## Latest: dev19 Min-P coding PASS; dev20 status source only

SC20 repeated the frozen SC19 task with explicit Min-P through installed dev19.
Eight original tests+400independentcases and complete public CLI handoff passed.
Saved request bodies prove exact preset delivery. Five calls/2129outputs,
134.226s wholeCLI;51.315TPS native timed generation. Same15537tokenprefix restored.
No general sampler quality claim or new numerical certification. Server/native
cleanly stopped,keyrevoked,GPUidle,chatOFF. See validation/SC20-2026-10-19/STATUS.md.

Source dev20 adds read-only pending-tool status guidance:unknown outcome versus
recorded result awaiting settlement.21focusedsourcechecks pass;not yet packaged.
No automatic tool-effect reconciliation is implemented. Installed dev19 remains
at /home/dflanag3/spatial-artifacts/branchwrite-dev19-package-20261019-v1/venv/bin/branchwrite
on llm-49. Earlier installed dev18 and dev16 remain available.

## Current checkpoint: installed dev18 and SC19 (2026-10-19)

BranchWrite is a working research coding agent; the overall standalone-agent
objective remains active. Current source: llm-49
/home/dflanag3/src/branchwrite-model-reconciliation-20261019,
branch feat/explicit-model-reconciliation-20261019. Private remote:
box-git:/srv/data/git/BranchWrite.git. No public publication.

Installed candidate: /home/dflanag3/spatial-artifacts/
branchwrite-dev18-package-20261019-v1/venv/bin/branchwrite on llm-49.
Wheel SHA256 7ae92fbdd57220ae2007fa0bed86e06f6c998f8a5ff81d0d91b799840a357ec6.
Older installations remain available; this is not an automatic fleet upgrade.

SC19 independently repaired a new dependency-order task: eight supplied tests
and400 independent seeded cases passed. Six model calls/2373 output tokens,
155.466seconds whole CLI,49.334TPS native timed generation. The compatible
15537-token controller prefix was restored; only4081new prefill tokens computed.
Full review/export/apply/retry/offline-resume passed. Server/native exited0,
GPU idle,owned key revoked,chat OFF. See validation/SC19-2026-10-19/STATUS.md.

SC18 separately demonstrated real Q8 durable lost-reply reconciliation without
new inference,then autonomous task completion. The lease input-binding cache
optimization is implemented and has separate bounded numerical/performance
qualification in private_context_cow.git; earlier statements below saying it is
not implemented are historical. Broader original G1-G5/VC remain unqualified.

Dev18 installed checks:22execution/discovery/status;15HTTP reconciliation;
39planning/verdict/provenance/retry controls passed. Counts are scoped evidence,
not independent coverage percentages. Planning controls use scripted ledger/CPU
model fixtures,not live-GPU failed-finish qualification. The 92-method broader
source run retains one unchanged historical empty-suite diagnostic assertion
failure (91pass,0skips/errors). Do not call that suite green.

Next substantive work:live failed-attempt recovery and branch exploration,
broader unfamiliar repositories/longer tasks,effect/crash recovery and deployment.
Retain original operation IDs;do not repeat uncertain tools or count catalogue
passes as completion of the overall product goal.

Everything below is historical unless explicitly reaffirmed above.

## 2026-10-19 SC16 diagnostic: failure retained; concrete profiling lead

The128-token baseline/profile pair produced identical tokens. Original full
thinking-object equality failed because separate generation streams have different
stream_key values and snapshot IDs. Canonical objects otherwise equal;next_draw0.
No assertion/result was weakened or relabelled PASS. See SC16 status and diagnosis.

The profile identifies repeated input_binding/native_tokens work for investigation.
No cache optimization is implemented yet. GPU requests/cleanup completed normally;
chat stays OFF. Normal dev16 and the SC15 two-client success remain unchanged.

## 2026-10-19 current: dev16 two-client integration passed

SC15 passed independent correctness and full public handoffs for both installed
clients on llm-49 against one Q8/FP16-KV server on llm-60. Actual max activeGPU0=1,
queued=1,18completed requests,zero failures. Both forked the15537-token generic
prefix;native counters prove no prefix computation. Source/protected tests and
524900540-byte prefix payload unchanged. Both live progress displays worked.

A:6calls/4786outputs/550.34s including queueing;B:8calls/4972outputs/606.03s.
Each passed200independent cases plus its original tests;B also invalid cases.
Full review/export/apply/retry/offline-resume passed. Originals/run states unchanged.
Server/native exited0,keys revoked,GPU free,chat OFF. See SC15 evidence for scope.
Dev16 clean install/90installed controls and282source controls pass;counts overlap.
No fresh numerical oracle or original G1-G5/VC qualification claimed.

SC14 timing lead: reported native decode phases total~179s for9998tokens(~56TPS),
versus930s whole CLI. Host/sampling/status inter-response gaps merit profiling;
they do not isolate a causal function. Preserve validation and same-profile
semantics while measuring. Broader autonomous coding,recovery and deployment
work remain;the standalone-agent objective is not complete.

## 2026-10-19 current: SC14 passed; integrated code awaiting new package

BranchWrite autonomously improved its real710-file repository, changing only
project_scope.py. Nine protected methods,100 independent scope cases and three
supplemental validity checks passed. Full review/export/apply/retry/offline-resume
handoff passed,with original source/tests and saved prefix unchanged.
10 model calls,9998 output tokens,929.86seconds whole CLI. Zero prefix work on
restoring the15537-token root; no numerical oracle/full qualification claimed.
See validation/SC14-2026-10-19/STATUS.md for exact scope.

Reviewed scope normalization is integrated with stderr-only owner-emitted
model/tool progress. Combined282selected CPU/HTTP/subprocess/filesystem controls
pass,zero skips/errors/failures. Dev16 wheel built; clean install and90installed controls pass. Its live GPU run is next. Retain
dev15 for its saved unfinished workflows;do not silently migrate interpreter
identities. No owned GPU job remains; chat stays OFF.
Broader agent objective,larger tasks,multiple trees and recovery remain active.

## 2026-10-19 current: standalone coding agent; reusable-controller trial

Current integration: feat/autonomous-inline-task-20261019 on llm-49.
Installed client: branchwrite 0.1.0.dev15; inference: pinned Q8/FP16-KV COW
server on llm-60. Historical Q8-deferred entries below are superseded by the
owner's subsequent Q8-primary instruction.

BranchWrite CLI admits tasks and grants. Interpreter/FrameKernel/RuntimeLog
own workflow; Executor/ToolRegistry isolate actual tools; Context COW manages
immutable model histories, branches and checkpoints; Strata executes inference.
The audit campaign supplies independent checks, never model actions.

The generic controller prefix now excludes project-specific test commands and
argument enums; current immutable HOST TOOL CONTEXT supplies those bindings.
SC13A autonomously repaired a project: six original methods plus 200 independent
cases passed, as did status/review/export/new-copy apply/identical retry/offline
resume. Seven calls,1621 output tokens,158.08 seconds whole CLI. Its new generic
prefix has15537 consumed tokens. Raw client/service archives are individually
verified on private box-git; receipts: validation/SC13-2026-10-19/A/private-archives.json.

SC13B also passed: a different multi-file project reused that exact saved root
in a new native process. Eight calls,4956 output tokens,353.81 seconds whole CLI;
eight original methods plus200 independent generated cases and five invalid
classes passed. Zero stale project commands; complete public handoff passed.
Native restore loaded523907260state bytes with zero prefix forward work;
first913suffix tokens began at15537. Total10254forward=5298prefill+4956generated.
The524900540-byte root payload remained SHA256-identical. Server/native exited0,
owned keys/credentials retired,original SSH keys byte-exact,GPU free.
Both raw runs are verified on private box-git; see each project's archive receipt.

266 selected source controls and75 installed controls passed before the campaign.
Functional coding tests do not qualify a numerical oracle. Original G0-G5 and
full VC qualification remain separate and incomplete. Broader real projects,
recovery/pressure, deployment ergonomics and long autonomous runs remain.
Private LAN Git only; chat OFF. Earlier dated sections are historical evidence.

## 2026-10-18 latest: both line-file tools pass real remote Q4 trials

Unchanged protected L02 passes with create_text_file/read_file/finish:37 exact
bytes,3 model calls,503 outputs,36.459s whole CLI. Separate owned existing-file
repair passes read/replace_text_file/read/finish:39 exact bytes,4 calls,428
outputs,45.079s. CRLF/no-final-newline,0640 file mode and neighbors preserved.
Both use normal DRY.8+MinP defaults and4096 thinking. No operator intervention
in either model loop. Actual client49 has no model/GPU files;real HTTP401 causes
zero native forward work. Completed reopening works without transport.

120 distinct CPU methods (23 new) and45 actual-tokenizer mask checks pass.
Earlier model failures and preflight errors are retained. Setupv8 stopped before
inference because existing Executor.create changes0700 directories to0755;
the focused replacement fixture uses0755. Directory-mode cloning remains open.
One stochastic success per task is not general reliability or a speed benchmark.

Source exercised:17d728209541f4b90d85174e67a8f88820fbe2d5. Raw evidence privately
verified at box-git:/srv/data/git/private_context_cow.evidence/20261018-line-file-tools-v1/evidence.tar.gz
SHA c3a8a67fc1fb87adf0fcf88106a82c4547bdf5c0448b45d97bb4d15630697588,
6303093 bytes;317 outer and352 nested client data members individually verified.
Services/native/client/tunnels stopped,owned keys revoked,original keys exact,
credentials removed;chatOFF. No current-profile numerical/native-restart oracle
in these trials. Full VC/G remain unqualified;Q8 deferred. Next original L03,
and separately current28 numerical qualification. See docs/LINE_FILE_TOOLS.md.

## 2026-10-18 current: line-based file tools ready for real-model trial

create_text_file and replace_text_file now accept line arrays plus explicit
LF/CRLF and final-newline choices. New generic examples use the actual tools.
120 distinct CPU methods and45 actual-Q4-tokenizer mask checks pass; no skips.
GPU/model exercise is UNRUN. See docs/LINE_FILE_TOOLS.md for semantics, retained
failures and evidence locations. Global samplers unchanged; protected workloads
and exact bytes unchanged. Full VC/G remain unqualified. Earlier history follows.

## 2026-10-18 latest: autonomous Ubuntu L02 passes on explicit DRY0 profile

Actual CLI on llm-49 called the authenticated Q4 COW server on llm-60. Original
protected task/checker stayed unchanged. Three model calls created the missing
parent/file, read its37 exact UTF-8 bytes and requested finish:PASS in32.858s,
419 consumed output tokens. Thoughts closed naturally at170/6/116 tokens within
the4096 allowance. The client exposed no GPU/model/server files. Actual wrong
API key returned401 with zero native work; completed reopening worked without
transport. All service/native/client/tunnel PIDs retired, scoped SSH key revoked,
original authorized_keys byte-exact, credentials removed;chat remainsOFF.

Keep the failures: v4 on4ca produced an extra leading space and could not repair
under its create/read-only grant (16 model calls/13804 tokens/757.69s). v5 on3110
added generic examples and same-target edit permission but omitted final LF and
repeated identical replacements (16 calls/6577 tokens/381.44s). v6 used the same
source/model/prefix/grammar/grants asv5 with per-run DRY multiplier0 instead of.8.
Request/stream identities differ,RNG is unpaired:one success is not a causal
DRY proof or broad robustness. Global DRY+MinP defaults are unchanged.

Three reusable literal-file examples add no protected task answer. They execute
real file tools;23 focused tests pass on integrated source. The6 new methods
are included in23,not an additional disjoint total. Missing-parent source and
new examples are now integrated;implementation/examples/tests/scripts are byte-
identical to actual tested feature3110fcc before these documentation updates.
Twelve actual Q4-tokenizer/llguidance masks accept correct create/newline repair
forms in final/thinking modes,so no grammar newline ban was demonstrated.
A lines-plus-explicit-ending input is an ergonomic research idea,UNIMPLEMENTED.

Private raw archives under /srv/data/git/private_context_cow.evidence/:
 20261018-literal-l02-failure-v1/evidence.tar.gz (027db95b...,162+419 files)
 20261018-literal-l02-missing-lf-v1/evidence.tar.gz (d7b5eec6...,142+402 files)
 20261018-literal-l02-pass-v1/evidence.tar.gz (94a6a6f8...,59+146 files)
 20261018-literal-prefill-cpu-v1/evidence.tar.gz (36314058...,24 files)
Every data member verified. Optional derived state retired afterward through
the disk pool;canonical records retained. Model failure candidates on llm-60
remain unreviewed/export-ineligible;no training. GitHub/upstream untouched.

Current COW profile28c765ed has JSON-policy source changes;older92df numerical
results must not be inherited. New tiny/medium matching-reference fixtures are
prepared on60 but GPU UNRUN. Full VC00-VC09 and original G1-G5 remain unqualified.
Next:record source/private refs,continue original protected L03 with actual
remote CLI;then supported-matrix numerical/auth qualification. Do not mutate
protected tests or silently change global sampler settings to call this robust.

## 2026-10-18 current: exact Unicode teaching pair works in a bounded diagnostic

The ten-example and expanded55-example interpretation arms both finish7/10.
The expanded library lowers median recorded thinking1330 to843 but does not fix
exact decomposition copying. Preserve those failures. Owner then requested the
exact failed observation and exact desired JSON in prefill. That seen case and
two fresh-marker/newline variants now pass with all fields/UTF8 bytes unchanged.
Thoughts1359/907/895 close naturally within4K. This is narrow transfer,not unseen
model reliability or a numerical/state oracle. No model/schema/sampler change.

Private box-git raw evidence is verified;both services/native processes exit0
and are absent,keys/credentials retired,chat OFF. Earlier orchestrator exit0
while reportingFAIL is retained as a launcher bug;new launcher exit policy is
independently checked0/1/1 forPASS/FAIL/ERROR. Never infer pass from old exit0.

The isolated nested-file feature4ca28a7 fixes missing parent creation for exact
granted leaves;13 new/87 distinct related tests pass,including actual filesystem,
Chromium and COW CPU grammar fixtures. Private task branch is backed up but not
yet integrated here. Actual autonomousL02 remains UNRUN. Next use its isolated
checkout for original protectedL02 file creation/readback,thenL03. Do not precreate
the missing directory or insert protected answers into the autonomous prefix.
See provenance/UNICODE-EXACT-EXAMPLE-Q4-2026-10-18.json. Full VC/G unqualified;
Q8 deferred,Windows steering,private LAN only. No owned model job remains.

## 2026-10-18 current interim: Unicode grammar fix tested on real Q4

The formerly blocked quoting/Unicode smoke now passes through client49/HTTP/GPU60.
The completed ten-example arm passes7/10;three outputs change a decomposed accent
into its composed lookalike. Keep the exact comparator and these real model
observations. Expanded55-example/65,290-token pre-template arm is RUNNING at this
checkpoint. Inspect current receipts,not old status,for its eventual outcome.

The old grammar's printable-escape restriction is fixed in COW0c50. Corrected
profile28c765ed passes production fingerprints;earlier wrong-fingerprint and
missing-credentials attempts ran no inference. Original failures remain evidence.
Completed-arm raw reports and source/profile receipts are verified privately on
box-git. No public push;Windows steering only,chat OFF,Q8 deferred. Current-run
sampler DRY0 is explicit and does not change the global DRY+Min-P default.

See provenance/ROBUST-PREFILL-UNICODE-INTERIM-2026-10-18.json. Raw client49:
/home/dflanag3/spatial-artifacts/branchwrite-ubuntu-baseline-20261018-v1/robust-prefill-components-v3.
Poll tmux bw-json-unicode-model-v3 before any restart. Finish collection and
cleanup,next autonomousL02. No new fullVC/G qualification or autonomous pass.

## 2026-10-18 latest: comparison stopped for JSON grammar defect

The component campaign is terminal, not still running. Existing10-example root
returned2/10exactJSONreports;8Unicode output fields were altered under a grammar
policy that rejected their valid escaped encodings. Expanded65.3K-token root
was stopped before any completed case. Its transport error is operator-induced;
neither result establishes intrinsic model failure or example effectiveness.
COW fix0c50aeb4 enables the supported compiler option and changes affected engine
identity. CPU grammar/regressions/G0 pass; fresh GPU retest remains outstanding.

Client148/148 checks pass. Standalone real terminal110cases/205shellcalls pass.
Updated Unicode pack tests use asserted actual nonASCII values, with earlier
launcher/fixture mistakes retained. No autonomousL02 yet. Both client/CPU and
server/canonical diagnostic archives are verified on privatebox-git; replayable
native checkpoint payloads explicitly omitted. All owned inference/tunnel
processes exited; scoped keys and secrets retired. ChatOFF,Q8deferred.
See validation/ROBUST-PREFILL-GRAMMAR-BLOCKER-2026-10-18.json for hashes and scope.

## 2026-10-18: component-first reference-pack campaign in progress

Explicit hashed example/facts packs now support optional pinned coding CLI
bootstrap. Source additions/changes/deletions make a new admission stale; old
saved roots stay unchanged.146 integrated client checks pass. Independent
terminal fixtures110/110 pass across205 real sandboxed commands.55 teaching
fixtures provide five demonstrations in each11sections; heldout fixtures are
separate and structurally varied.

The Q4 report-comprehension campaign is RUNNING on llm-60 via CLI/client49,
using the existing12.4K vs expanded65.3K token roots,10 observations each.
Initial old-root observations include incorrect Unicode string reporting despite
exact tool transport; preserve this failure and compare the expanded root.
No robustness or thinking-length benefit is established. Autonomous L02 remains
NOT_RUN; do not count transport success as model/task success.
Raw phase/status and auto-stop/credential-retirement scripts are under the
robust-prefill-components-v1 artifact root on49. ChatOFF,Q8deferred,privateonly.
See validation/ROBUST-PREFILL-IN-PROGRESS-2026-10-18.json and docs/REFERENCE_PACKS.md.

## 2026-10-18: bounded L01 PASS with ten examples and per-run DRY-off

95 client/107 server CPU checks pass. Ten independent teaching scenarios use15
real sandboxed shell observations;example final reports are host-authored.
Q4 received the exact12,749-token root. Native counters show it was evaluated
once,with subsequent calls prefilling only their229-573 new input tokens.

DRY0.8 with the new examples still failed final reporting (91 thinking tokens).
The otherwise unchanged per-run DRY0 control passed all5 L01 cases plus a
complete final-report review (281 thinking tokens,1523 outputs,87.14s CLI).
All runs allowed4096 thinking. First two failures used4096 and219 tokens.
This is one sampled mitigation,not general causal reliability or a speed
comparison. The global DRY+Min-P default remains0.8. File-readback verification
alone is not a semantic judge. Earlier failures and an unreviewed LoRA record
remain private;no protected diagnostic answer was approved for training.

Raw evidence/backups are verified on private box-git. Owned processes/tunnels
and keys retired;optional checkpoints retired after backup,canonical records
preserved. Chat OFF,Q8 deferred;no new numerical or native-restart oracle.
Full VC/G qualification remains open. Next L02/L03 after owner's private
web-viewer overflow fix. See validation/TERMINAL-L01-EXAMPLES-SAMPLER-2026-10-18.json.

## 2026-10-18: second L01 report FAIL; exact tool provenance verified

The generic command/plan feedback change passes91 client and103 server CPU
checks,including real HTTP delivery. Same-task Q4 run:8 model calls/requests,
1120 outputs,69.71s CLI. All five raw transport assertions pass; actual cap
typo127 was observed and autonomously corrected. Final report still garbles
pipefail wording and contains drafting notes,so complete L01 is FAIL. Binary
display explanation is now present;do not infer causal improvement from one run.
File-readback verified:true does not certify report semantics.

Raw failure,CPU failures/corrections,and LoRA mitigation are privately backed up.
Owned server/native/client/tunnel absent,keys revoked,chat OFF,Q8 deferred.
40 canonical cache files preserved after optional payload retirement. No new
numerical/native-restart oracle or full VC/G qualification.
See validation/TERMINAL-L01-PROVENANCE-2026-10-18.json. Next: generic concise
terminal-report example and report acceptance guard before another L01 attempt.
No L02 expansion or additional GPU job yet.

## 2026-10-18: L01 transport PASS; complete final report FAIL

Actual llm-49 CLI/terminal and llm-60 Q4 preserved all four command results:
intentional exit7,pipeline0,pipefail7,binary9. Exact separate stream bytes and
explicit lossy display metadata reached subsequent real model invocations.
All five transport assertions pass. The complete task fails: the final model
report garbles a command and stops before the pipefail/binary explanations.
The file-readback policy's verified:true covers file hashes/readback only.

7 model calls,9 native requests,4556 output tokens,183.70s CLI; final thought
reaches4096 while looping over quoting. Exact command provenance in feedback is
a candidate mitigation,not a proven cause. No false-success classification seen.
89 client/101 server CPU checks and G051/51pass; no skips/errors in final runs.
Earlier setup failures retained. No numerical or native-restart oracle.
Source/workspace unchanged. Owned processes/tunnel retired,key revoked;chatOFF.
Raw failure and unreviewed/non-exportable LoRA observation are verified on
private box-git. See validation/TERMINAL-L01-2026-10-18.json.
Next: test exact command provenance in feedback,then rerun L01 before L02/L03.
Full VC/G certification remains incomplete. Private LAN only,Q8 deferred.

# Current goal: push-button autonomous coding,2026-10-18

Owner selected a generic executable .bw workflow as the immediate delivery target.
Read docs/AUTONOMOUS_RUN.md for the one-interpreter run/step CLI, config, supported
handlers and explicit limits. One bounded real Q4 autonomous task now passes; see
validation/AUTONOMOUS-CORE-2026-10-18.json. Broad workload validation remains open.
The original VC/G qualification scope remains open.

---

# Current implementation pointer - 2026-10-18

The archive-only status below is historical. Current private Linux implementation
and executed component evidence are recorded in validation/CURRENT-CATALOG-STATUS.md.
The production program reader/check CLI, frame kernel, model request FLOW and
registered tool dispatch exist. The general step/run task interpreter and autonomous
changed-workload loop remain missing. Original COW G1-G5/full VC09 qualification
is separate from these component tests. Repository: private box-git BranchWrite.git;
authoritative checkout /home/dflanag3/src/branchwrite-runtime-active-20261018 on llm-60.
New thinking default1024; old512 successes/controllers unchanged. No public push.

---

# Evidence state

## Inspected and executed here

- The exact uploaded v0.2.0 archive, its active v0.5 contract, native CLI reference,
  211 acceptance cases, 44 tickets, templates and handoff utilities were inspected.
- The old verifier and 98 old offline tests passed. That suite tests the old handoff,
  not the product and not the new language.
- The new reference/checker results are in `validation/TEST_REPORT.md` and `tests.txt`.

## Reported, not independently qualified

The user reports existing Min-P and DRY and asks to exploit state-dependent GBNF,
Typical, DynaTemp, Mirostat 2, Adaptive-P and XTC. The old native CLI reference described
plain-text greedy inference without sampling controls. The newer conversation may
supersede that limitation, but no current installed source or native trace was supplied.
Do not treat the historical CLI text as current proof of either support or absence.
The controls must be bound to the actual source, service, tokenizer, device and build.
“microstat 2” and “adaptive 2” in earlier discussion are treated as Mirostat 2 and
Adaptive-P, not names of newly specified algorithms.

## Not performed

No product repository was checked out or modified. No host was contacted. No model
ran. No GPU tests, native grammar/sampler checkpoint tests, arbitrary-code isolation,
real parallel ACT campaign, or numerical/performance superiority was demonstrated.

There is no production-ready claim in this archive. Unbound capabilities fail closed.
A successful reference test cannot turn a `not_run` product case into a PASS.

## 2026-10-20: autonomous repair and progress notices

Dev54 installed CLI completed one real-Q4 Python repair in77.362s with no
intervention. Existing3tests unchanged;100independent seeded inputs passed.
Actual failed run_shell and successful run_check receipts/feedback were audited.
See validation/remote-admin-20261020/autonomous-repair/.
Dev55 adds fixed tool-specific progress labels;471CPU/PTY/HTTP regressions
passed without failures/skips. Installed client on llm-49 under
/home/dflanag3/spatial-artifacts/branchwrite-dev55-tool-progress-20261020/.
New-launch candidate only: old admitted workflows keep their original build.
Remaining priorities: end-to-end steer latency, robust broader coding/admin
workflows and independent acceptance; current metadata optimizations are not
yet GPU-qualified or deployed. No broad G1-G5 qualification claimed.


## 2026-10-20 built-in PDF integration (bounded checks)

Built-in ReportLab/pypdf/PDFium dependencies, ordinary project build_pdf/render_pdf
and actual image feedback are implemented. 34 focused actual-worker/canonical
completion/project-check tests pass with no skips. Completion rejects stale
builds, unrendered current pages and altered canonical receipts; failed rebuilds
preserve previous PDF bytes. Latest combined regressions and real Q4 authoring/
visual revision remain pending. See validation/pdf-20261020/README.md and
examples/prompts/results.json. Existing CAD/Blender prompts retain their exact
prior-version model passes; new code/writing/PDF/admin prompts stay pending until
executed. Code and evidence remain private LAN only. No G1-G5 qualification.


## 2026-10-20 PDF actual Q4 authorship and installed regression result

Installed dev59 CLI onllm-49 completed the exact examples/prompts/pdf.txt task
against Q4/COW onllm-60 in493.635s. The model wrote ReportLab source, built the
actual PDF, rendered both pages, ran current checks and finished without operator
candidate edits. Canonical audit proves both actual images entered settled native
requests. Visual inspection found readable headings/table/checklist/page numbers
without visible clipping. This is a functional bounded pass, not a speed claim
or proof of visual revision after an edit. See validation/pdf-live-q4-20261020/.

The dev60 aggregate passed500 CPU/PTY/HTTP/PDF methods,0skips. Standard Linux
venv support and immutable imports are checked. The subsequent Blender structural
runtime fix passed7 real Blender/MCP regressions;53 CAD regressions also pass.
New-launch dev61 follows. Each result keeps its actual source/version scope.
The remaining examples stay pending until their exact CLI prompt is executed.


## 2026-10-20 interactive domain connection, dev62

CAD/Blender operator configurations now reach the existing interactive Work
launcher. Read-only modes receive neither capability. Saved exports persist in
existing turn/file-version metadata and display actual artifact paths.48 focused
plumbing/terminal/control/preview tests pass; installed live domain validation is
pending. One fixed domain per session; general mixed-domain acceptance remains
unfinished. The dev61 real Q4 text-writing example is running separately; do not
mark its prompt verified before the independent checks and content review finish.


## 2026-10-20 current combined result and plain-text example

Dev62 codeb4b039c5 passed506 CPU/PTY/HTTP/PDF/session methods,0skips,127.423s
with unchanged source. Actual CAD53/Blender7 domain regressions remain separately
scoped. The writing.txt prompt passed an installed dev61 Q4 continuation:165words,
actual read/check and unchanged prior PDF. Prompt status/evidence is in
examples/prompts/results.json. The code.txt installed dev62 continuation is active
onllm-49; original controller2477016/client2477018, revalidate before action.
Do not mark it passed before independent browser acceptance. Live interactive
CAD/Blender, PDF revision/restart, broader coding/admin and supported-matrix
qualification remain outstanding. No public push or full G-gate claim.


## 2026-10-20 saved document viewing, dev63

The existing /preview now serves the explicitly selected saved PDF or literal
UTF-8 text. One PDF/no HTML can be selected by default. Other text/PDF files are
not added to website bundles.47 focused loopback/Git/terminal/domain tests pass;
full latest aggregate and installed/live UI validation follow. The code.txt Q4
job remains separate and active; original IDs must not be repeated.
