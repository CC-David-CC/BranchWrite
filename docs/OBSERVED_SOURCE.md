# File versions belong to the host

The model chooses what to change. The host remembers which exact file bytes it
has shown, freezes that file hash in the plan and checks it before execution.
The model does not need to copy a64-character checksum to ask for an edit or
picture. All file and native checkpoint hashes remain enabled.

## Current proposal shape

replace arguments are path,before,after. capture_page arguments are path.
interact_page arguments are path,actions. There is one public proposal shape;
source_sha256 in these model arguments is now an unknown-field error. The read
and tool feedback still expose exact observations for tracking and diagnostics.

The host takes the latest visible same-world/path observation in actual
canonical completion order. It does not infer permission from a file existing,
choose an older matching read instead of a newer stale read, or accept another
workspace's observation. Repeated A/B/A digests retain their actual order.

Frozen bw.tool-plan.v2 contains the full exact source_sha256 plus its observation
witness. PLAN checks actual bytes under the owner lock. ACT rechecks the same
frozen precondition; Executor repeats the exact write check. Unique preimages,
byte limits, grants, private-file rules and uncertain-effect reconciliation are
unchanged. A file changed since the last observation needs a new read.

This changes the model-facing tool contract, not the COW mathematical contract,
canonical history, checkpoint format, GPU integrity checks or numerical tolerance.
Old v1 plans/workflows are not silently reinterpreted. Use their pinned original
code to inspect/reconcile them. New workflows need a new startup grammar and
fresh model context; do not resend an old pending operation under new code.

## Why this changed

A bounded autonomous H07 run edited the form successfully, then spent eight
capture proposals mistyping the new file hash. All were rejected. Sixteen model
outputs exhausted its loop without delivering an image. A host-only diagnostic
confirmed the generated source passed the unchanged protected checks; that did
not make the autonomous task pass. Keep the original failure and LoRA class.

The interface now puts version bookkeeping in its trusted owner.217 selected
checks pass (201client,16serverCPU), including11 new observation/version guards.
Positive model proposal fixtures were migrated; existing assertion expressions
were AST-compared unchanged. Direct Executor hash checks, protected assertions,
COW gates, reference equations and tolerances were not weakened. The same three
independent worked examples were regenerated and actually executed under v2.
They contain no current workload answer. A live Q4 H07 retry remains unrun at
this source checkpoint. See validation/OBSERVED-SOURCE-2026-10-18.json.

## Executed H07 follow-up

The v2 default-sampler retry reached16 outputs without a browser image. Source
version binding worked; semantic/no-op edits were the separate failure. A fresh
run changing only dry_multiplier to0 passed all bounded autonomous/browser and
native-delivery audits in108.38s. The global default remains unchanged. One pair
does not establish sampler causality. See validation/AUTONOMOUS-H07-V2-V3-Q4-2026-10-18.json.
