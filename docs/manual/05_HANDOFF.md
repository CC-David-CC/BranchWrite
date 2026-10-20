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

# Context COW and BranchWrite handoff

The goal remains a useful standalone coding agent using shared computational histories and independent continuations. Passing a workload catalogue is supporting evidence, not the end state.

## Division of roles

| Piece | Owns |
|---|---|
| BranchWrite CLI and client | Task/grant admission, model/tool workflow, original operation IDs, sandboxed client tools, verification and workflow restart. FrameKernel/RuntimeLog is its canonical workflow. |
| Context COW HTTP server | Immutable model history/controllers, movable branches, active native leases, RAM/disk pools, expiry, derived checkpoints and operation receipts. |
| Native Strata engine | Model computation, consumed-token frontier and native state capture/restoration/sharing under the pinned profile. |
| Audit harness and VC/L/SC runners | Independent expectations, fault injection, numerical/work/resource evidence. They are not needed to drive an ordinary coding task. |

A .bw file describes workflow control. It is not a KV-cache file. BranchWrite's saved run refers to COW state; neither a transcript nor a branch label alone proves GPU residency.

## Current client-side durable receipt milestone

The current BranchWrite branch is feat/explicit-model-reconciliation-20261019 on
llm-49, at test commit a3adf08b6af99491c03e7d71c8cae64f6bad86c1. The dev30 wheel
was built from product-source commit b48b8ac9043cb8678329e83f1f6e57abf610c084;
the later commit adds tests/evidence, not package behavior.

The client now demonstrates two durable boundaries: frozen project inputs can be
recovered after source snapshot publication, and a committed COW answer can be
recovered after the client journal fsync but before the workflow ledger return.
For the latter, status names the pending operation; reconcile reads the exact
answer and COW receipt from the client journal with the HTTP service stopped and
no API key; resume then records that same result without another fake-backend
forward or branch movement.

Run the bounded process-separated receipt evidence from the checked-out repo with
its pinned COW test sources and grammar dependencies using the command recorded in
validation/client-durable-operation-receipt-20261020/result.json. Its raw logs and
scope limitations are in the same directory.

This is CPU-fixture evidence. The COW HTTP server is stopped and recreated, but
the COW coordinator/Store/native fake remain alive in process. Q4/Q8 inference,
a full COW/native process restart, power-loss testing, state-directory loss,
tool-effect settlement and broader coding-workload reliability are outstanding.

## Authoritative places

| Item | Host and path or private Git ref |
|---|---|
| BranchWrite source | llm-49:/home/dflanag3/src/branchwrite-model-reconciliation-20261019 |
| Current client branch | feat/explicit-model-reconciliation-20261019 |
| Client Git | box-git:/srv/data/git/BranchWrite.git |
| Tested dev24 wheel source | 849de09f95438feb72697b251288cd885ca9996a |
| Latest passing Q8 evidence commit before these guides | b2ed1bff59fe1fddadcf5d8907964f02ec758416 |
| Installed client | llm-49:/home/dflanag3/spatial-artifacts/branchwrite-dev24-package-20261019-v1/venv/bin/branchwrite |
| Wheel backup | box-git:/srv/data/git/private_context_cow.evidence/branchwrite-dev24-20261019-v1 |
| COW source | llm-60:/home/dflanag3/src/context-cow-persistent-operation-status-20261019 |
| Server branch | fix/persistent-text-operation-status-20261019 |
| Server Git | box-git:/srv/data/git/private_context_cow.git |
| Tested server commit | 6647ae4637cf43ea356cfb1bc799722238212434 |
| Passing dev24 campaign | Both hosts:/home/dflanag3/spatial-artifacts/project-base-three-builds-20261019-v1/dev24-q8-reference-refresh-v1 |
| Compact committed evidence | BranchWrite validation/project-base-three-builds-20261019-v1/dev24-q8-reference-refresh |
| Model-failure collection | llm-60:/home/dflanag3/src/branchwrite-lora-examples/candidates |

The Windows fleet/branchwrite checkout was f5aa649 and fleet/Public_Context_COW was c8e9c09b when checked for this guide. Treat them as historical, not current Linux sources. Do not bulk-copy Linux outputs to Windows. r730's authorized data disks remain available for task-specific large storage after mount checks.

The llm-60 BranchWrite source mirror is a test copy and may contain experimental recovery files. Use the llm-49 Git refs and versioned installed packages as authoritative; do not infer a release from the mirror.

Only private LAN box-git is authorized. GitHub publication needs new owner approval; Strata upstream additionally waits for Niko.

## Current tested behavior

Dev24 passed two consecutive real-Q8 tasks through installed CLI49 ? authenticated HTTP ? COW60 ? GPU0. A implemented a two-file reporting library. B extended the applied A result using refreshed reference requirements.

- A: 7 calls, 1383 output tokens, 151.866 seconds; 5 visible methods and 400 independent generated sequences passed.
- B: 10 calls, 5345 output tokens, 434.570 seconds; 8 visible methods and 800 independent sequences passed. Those 800 include the repeated 400 baseline sequences.
- No parent intervention during either model loop. No rejected tool effects or verified task failures.
- Three pack versions retained. B has a different canonical root. A's branch and history stayed unchanged.
- CLI review/export/apply passed. Completed A and B reopened after tunnel/server stop with identical results and unchanged state bytes, without an API key.
- Native generation averaged 40.320 TPS over 6728 tokens. This excludes prefill, tools, HTTP and checkpoint publication.
- Native work: 49815 forward = 43087 prefill + 6728 generation. Zero integrity mismatches.
- Source startup verified 56 declared files. No fresh full-logit oracle ran in this coding campaign.

Earlier dev23 separately passed actual server/native restart, lost bootstrap acknowledgment reconciliation and zero-prefix-work restoration, followed by autonomous code repair. Its forced-finish drill also exercised a real COW planning fork and 4K?8K thinking escalation. Preserve those distinct versioned scopes.

Original G0 has 51 reference checks; the last executed G0 passed. Original cumulative G1?G5 remains unqualified. Matching-profile evidence does not establish arbitrary batch-arrangement equivalence.

## New recovery work is on its own branch

Branch feat/tool-retirement-recovery-20261019 now has a separately installed
dev25 candidate. Its source is c8a2e721e36d4e28ba72890f6934a65ea898b26b;
current candidate evidence is258a357c3e6b139c34061bdb19a5a4ded63202d9.
It is now merged into this development branch. At integration, all 44 production Python modules matched the separately installed, real-Q8-tested dev25 wheel. A later source-only browser diagnostic fix is not in that installed wheel. Keep unfinished dev24 workflows on their original installation. A bounded real-Q8 recovery campaign has completed; see the scope below.

Installed candidate on llm-49:
 /home/dflanag3/spatial-artifacts/branchwrite-dev25-package-20261019-v1/venv/bin/branchwrite
Wheel SHA256:
 251366753de7e4bc7313b5112b63ece518c7a4d5d0e482d44e787a6dd36e778f

It records a retired tool result/proof in the existing canonical ledger before
settlement. Resume can settle that exact result without reexecuting the tool.
A crash before the durable returned record stays unknown,even if current file
contents look right. A new negative test found transferable v1 proofs across
two workflow ledgers; version2 binds ledger path,parent/epoch/slot ownership too.

50 focused source checks and20 installed recovery checks pass. The installed
checks include actual process death and new-process CLI resume,with source
imports excluded. All44 installed module bytes match the wheel. G0 passes51/51.
The broader100-method run has99passes and1unchanged diagnostic-string failure:
the empty suite correctly returns nonzero,but its message differs from the old
expected text. No backend assertions or numerical tolerances were changed.

A three-repetition1KiB tool-read probe measured39.476ms dev24 versus53.618ms
candidate,+14.142ms/+35.823% for that isolated dispatch path. This exceeds8%
there; it is not a measured whole-agent overhead or TPS loss.
Real-Q8 recovery campaign: the installed dev25 client created a website, was
terminated after a durable tool return, and resumed successfully after both
server and native processes restarted. The original create operation was
executed once, returned once and settled once; its file inode and modification
time were unchanged by recovery. A separate crash before recording the return
remained unresolved on two resume attempts (exit 4), without reexecuting it.
Restoring the 20,516-token state performed zero prefix forward work. The
independent website structural check passed. Desktop/mobile render checks
passed on llm-60. Optional browser capture on llm-49 failed because Chromium
could not establish its sandbox; do not bypass the sandbox. No numerical
oracle ran in this campaign, so it supplies no new logit-equivalence claim.
Raw evidence: /home/dflanag3/spatial-artifacts/project-base-three-builds-20261019-v1/dev25-q8-tool-recovery-v1.
Keep dev24 available for existing workflows. Broader resource/crash fixtures,
whole-agent measurements and a clean-machine server installer remain.

## Recovery rules for dev24

1. Keep the entire client state directory and use its original venv.
2. If a process is still live, inspect its owner-emitted stderr/progress and process identity. Do not open its live RuntimeLog from another observer.
3. After the writer exits, use branchwrite status STATE.
4. For a pending model operation, use branchwrite reconcile STATE --operation-id ORIGINAL_ID, then resume the same state. Only proven durable output is recovered; unknown remains unknown.
5. Dev24 has no general tool-effect reconciliation command. Do not use model reconcile to certify an edit or repeat an uncertain command. Preserve its original receipt/evidence and obtain owner-side reconciliation.
6. An admitted run keeps its frozen task, sampler, source/profile identity and branch references. A new ID is new work, not recovery.
7. Streamed output is not an acknowledged durable save point. Expect loss after the last acknowledged boundary if a process crashes.

## Next product work

- Integrated dev25 has bounded installed/live recovery evidence; broader recovery qualification remains.
- Broaden unfamiliar coding tasks and longer workflows; keep independent acceptance checks.
- Integrate automatic host-approved Project Base selection, refresh scheduling, multi-base consultation, compaction and adoption into the existing interpreter. APIs/parsers alone are not a scheduler.
- Package the generated native dependency closure into a reproducible clean-machine server installer.
- Run broader cancellation/crash/disk-full/memory-pressure, sanitizer, soak and supported-matrix campaigns.
- Preserve actual generalizable model failures in the private LoRA collection. Do not relabel infrastructure faults or forced test actions as training data.

The development server/native worker and temporary tunnel/key were closed after the last campaign. GPU0 was free. Chat stays off. These guides do not mean a service was left running.

## dev26 packaged client (source 3ef0800)

Separate installation: llm-49:/home/dflanag3/spatial-artifacts/branchwrite-dev26-package-20261019-v1/installed-check/venv/bin/branchwrite.
Wheel SHA256: bc3257fcbce1f0e9a4e4aa69a4b3788572c23b0789df1c5ed6f4e783a77e1d46.
Fresh wheel installation, actual file creation and isolated-shell checks passed.
All 16 installed recovery/diagnostic tests passed without development source
imports. No dev26 GPU campaign ran; dev25's bounded Q8 evidence remains separately
versioned. Continue unfinished runs with their original versioned installation.

## Current private client preview: installed dev30

BranchWrite source commit b48b8ac9043cb8678329e83f1f6e57abf610c084 on private
branch feat/explicit-model-reconciliation-20261019. Wheel:
 /home/dflanag3/spatial-artifacts/branchwrite-dev30-package-20261020-v1/wheel/
 branchwrite-0.1.0.dev30-py3-none-any.whl
SHA-256 9d71fb5ba0fa6b056145e416bb102f31b677f8f31ecd5ad2c5f6fe4a753ce19c.
Installed in an isolated llm-49 venv; CLI help and doctor smoke passed.

71 focused BranchWrite CPU tests and 8 actual local CPU Context COW HTTP tests
pass. Client crash recovery now reports an orphan receipt candidate; after
offline receipt recovery the real resume CLI starts one bounded step against a
restarted local COW HTTP server. This uses a deterministic CPU fake model. It does
not qualify Q4/Q8 inference, full server/native process restart, or autonomous
task success. Raw test results:
validation/client-context-recovery-20261019/
Package smoke evidence:
validation/dev30-client-package-20261020/

The dev30 wheel is also backed up privately at
box-git:/srv/data/git/private_context_cow.evidence/branchwrite-dev30-package-20261020-v1/wheel/.
Keep previous runs on their original versioned client. This package is a preview,
not a replacement for the older Q8-qualified dev28 package.

## Latest supported example: installed dev27, Q8

Source29f7bb25d3c9f9d62efde61f7afb3e5708abadfb; install on llm-49:
/home/dflanag3/spatial-artifacts/branchwrite-dev27-package-20261019-v1/installed-check/venv/bin/branchwrite.
Wheel22f8312eafb8181ec61055a15a69c85121766928f04d087a287e53f48b0188e3.
Both independent coding tasks passed via installed CLI49/HTTP/COW60/Q8 GPU0.
First created a website (549.17s,7095 outputs); second edited it (111.99s,1119
outputs) using automatic host selection of the exact15,638-token common tooling
root. Independent structural/meeting-content checks passed; first branch and
second input directory stayed unchanged. These are different tasks/output lengths,
not an isolated speedup comparison. Catalog revision identifies shared tooling,
not website working-tree freshness. No fresh numerical oracle ran.

Native generation34.51TPS excludes prefill,tools,HTTP and publication. Root restore
performed zero prefix forward work from a resident native handle; no disk load was
recorded. Both server/native exited0,GPU free,key revoked,chatOFF. Full original
G1-G5 remains unqualified. Automatic summary adoption, freshness/refresh scheduling,
multi-base consultation and broad coding reliability remain unfinished. Evidence:
validation/dev27-auto-base-q8-20261019. Keep old runs on their original versions.

## Previous Q8-qualified manual target: installed dev28 and COW89525144

Client source28befcae4e8c24d9a6d6b53361791beac0ee72be, installed on llm-49 at
/home/dflanag3/spatial-artifacts/branchwrite-dev28-package-20261019-v1/installed-check/venv/bin/branchwrite.
Wheel8e6b4912cc49e6958c99e88d9a003885912378e16b47443b92ca96398983a6d6.
Server source llm-60:/home/dflanag3/src/context-cow-history-counts-20261019,
private branch feat/canonical-history-counts-20261019, commit89525144. This is a
separate working tree; the older server installation is preserved. New execution
profile7ed02ba4f2e842b82c798b9194a8a7b489c6e86c85de9f41a0770a40f9d79e36
rehashes the declared source closure. Native binary/model/configuration are unchanged;
old checkpoint profiles are not silently relabelled as this one. Use a fresh store.

Actual installed CLI49 to authenticated COW60/Q8 GPU0 prepared a13,068-cell pack
root. Native counters match. Identical prepare-base retry produced no new native
commands. Coding from its automatically selected catalog repaired interval merging
in86.54s,5 model decisions/1210 output tokens, with no interventions during the
model loop. Seven protected unit methods and an independent sandboxed1000 seeded
interval-union cases plus2 probes passed; the original fails the independent oracle.
Original project, protected files and prepared base stayed unchanged. Root reuse
performed zero prefix forward work. Native generation50.81TPS excludes other work.
No fresh model-logit numerical oracle ran. Server/native exited0,GPU free,key revoked,
chatOFF. Evidence: validation/dev28-pack-base-q8-20261019.

Older website and restart evidence remains versioned above; this trial does not
retroactively rerun every older scenario. Automatic source refresh/adoption and
compaction, broader agent reliability and full cumulative gates remain unfinished.
