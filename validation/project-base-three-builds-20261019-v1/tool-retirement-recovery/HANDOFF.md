## Latest checkpoint

Dev25 is now separately installed on llm-49 at
/home/dflanag3/spatial-artifacts/branchwrite-dev25-package-20261019-v1/venv/bin/branchwrite.
Sourcec8a2e721e36d4e28ba72890f6934a65ea898b26b.
Wheel251366753de7e4bc7313b5112b63ece518c7a4d5d0e482d44e787a6dd36e778f.
All44 wheel module files match installation.20 installed CPU/CLI recovery
checks pass with source imports excluded. G0 passes51/51.
No dev25 GPU campaign yet. Dev24 remains unchanged.

Next: actual Q8 CLI?HTTP interrupted edit after durable return,then resume
without reexecuting the edit. Retain exact original operation/model IDs and
native counters. Include an interruption before returned publication that must
remain unresolved. Then broader resources/recovery and whole-agent measurements.
Earlier source-only notes below are dated history,not the latest installed status.

# Tool retirement recovery work in progress

Source-only branch feat/tool-retirement-recovery-20261019.
Installed dev24 is unchanged and remains the current real-Q8-tested candidate.

New dispatch publishes a resource-retirement proof and returned result in the
existing canonical RuntimeLog before Kernel settlement. Resume accepts only the
exact proof and settles without reexecuting the tool. Missing/unproven outcomes
remain unresolved; matching file contents never prove an operation completed.
There is no second workflow journal or alternate history representation.

49 CPU/CLI/HTTP tests pass,including9 new focused methods and2 real subprocess
death cases. Positive process exits after returned publication and resumes the
same edit without changing its inode/mtime; negative exits before returned
publication and stays unknown without resending. Zero skips/failures in final run.
Initial red, stale-mirror setup failures and an older nonregistered status
fixture incompatibility are retained. The status fixture now constructs an
unproven returned state directly; all status assertions remain unchanged.
Registered backend acceptance tests,reference equations and tolerances unchanged.

Remaining: review and broaden forged-proof/resource fixtures; clarify CLI recovery
guidance; measure extra per-tool publication cost; rerun G0; package a distinct
candidate and execute installed checks; real-Q8 interrupted-edit/resume integration.
Do not call this installed or GPU-qualified,or silently migrate dev24 workflows.
Source hash changes bind new interpreter admissions; keep old packages for old runs.


## Proof binding review and dev25 candidate

The cross-ledger negative test reproduced a v1 gap: identical frame/plan/world
identities allowed transferring a proof to a second canonical workflow ledger.
Proof v2 additionally binds ledger path,parent,parent epoch and result slot.
The regression fails before the fix and passes after it. This is an engineering
receipt-binding defect,not a model training example. No source-only v1 proof is
silently upgraded.

CLI guidance now distinguishes durable proof-based resume from unknown effects
and from model-output reconciliation.50 focused CPU/CLI/HTTP checks pass.
A broader100-method run has99passes and1unchanged historical diagnostic-string
failure. The empty-test operation still correctly returns1. Actual Chromium
capture passes once its executable is configured. G0 rerun passes51/51.

Three repetitions of25 measured1KiB read dispatches after5 warmups per version
on llm-49: median-of-run-medians39.476ms dev24 versus53.618ms candidate,
+14.142ms/+35.823%. This exceeds8% for the isolated tool path. It is not measured
whole-agent overhead or TPS loss; initialization,admission,parent resume,
model work and browser work are excluded. Raw samples and module paths retained.
Do not discard the validation protocol solely on this timing. Whole-agent
measurement and real-GPU combined recovery remain outstanding.
