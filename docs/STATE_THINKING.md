# Thinking at each work state

A worker can pause after reading a file, making an edit or seeing test results
to decide what to do next. Its thought can be kept as a saved branch. New facts
may make that thought useful, outdated or wrong. BranchWrite chooses which saved
point to use; COW chooses where its computed state lives in memory or on disk.

Updated2026-10-17: COW's initial fixed-registry thinking matcher now passes
bounded real Q4 CLI/HTTP/GPU checks with greedy and Min-P fork/resume. Automatic
per-state scheduling and retention described here are **not yet implemented**.
See validation/THINKING_Q4_2026-10-17.md for the exact delivered scope.

At each READ/EDIT/TEST/FINISH or other host-defined state, the interpreter may
schedule a bounded reasoning operation against that state's exact COW snapshot,
goal, grammar identity and relevant world observations. Reasoning can steer the
next action, supply a candidate answer, or propose that a useful insight be kept.
The host validates and selects; model text cannot grant execution permission or
declare its own test passed. Different branches may reason under different
states/grammars and retain independent parser, RNG and adaptive-sampler progress.

The existing ledger records the reasoning operation ID, parent tip/revision,
evidence/preimage identities, budget, result receipt and disposition. A late
result remains tied to its original inputs; it cannot silently replace work
based on newer observations. Reasoning and action have separate result contracts.
The host can discard an insight from the current plan without treating a prior
edit or other already-completed effect as undone.

Useful thoughts can remain named tips or cited artifacts; stale ones can lose
their active references according to retention policy. Keep canonical ancestry
and evidence where policy requires it. Logical retirement makes eligible derived
checkpoints evictable; it is not an instruction to manually free GPU pages. RAM,
disk, GPU residency, transfers, integrity and expiry belong to COW/backend/pool
layers. The client asks to fork, continue, retry, retain or release logical work,
using the existing authenticated API and operation identities.

When new data arrives, check which dependencies actually changed. An unrelated
result need not invalidate every thought. If the model's earlier input changes,
create the corresponding new canonical path and compute the changed suffix.
Do not drop text from the middle while claiming its later numerical state still
matches the edited history. A compacted insight is a new derived summary with
source references and a newly prepared compatible context.

Implementation order: preserve consumed-state publication and lost-reply
recovery; add the canonical reasoning/closure/final controller; expose per-state
budgets through CLI/HTTP/client; test pause, fork, reseed, retry, restart, stale
results and retention; then compare 0/128/256/512/1024 early-stop-aware budgets.
Keep hardware placement out of those model/workflow decisions. GPU=[0] runs one
request now; future GPU lists may complete independent work out of order.

Keep both `fixtures/image_questions/short.md` and `expanded.md` in the budget
comparison. Current Q4 immediate-grammar execution has a recorded miss on the
short question and a passing H02 result with the expanded question. Thinking
was disabled in those original runs. New0/128-budget cases retain both. Do not
attribute a wording gain to reasoning or hide the
miss by dropping the simpler input. Repeat the exact pair on Q8 during the later
end-to-end campaign; Q8 testing is currently deferred by the owner.
