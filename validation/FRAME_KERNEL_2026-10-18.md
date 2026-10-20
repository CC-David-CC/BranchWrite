# Production frame/return controller: bounded component PASS

20 controller tests plus21 storage checks pass41/41. Final combined regression
passed406/406 with no failures, errors or skips. This is CPU/Linux/ext4 plus
existing real browser/HTTP-fixture coverage, not model/GPU execution. New1024
thinking default remains; recorded512-token successes were not rerun/rewritten.

Implemented: atomic child/wait admission, original operation/request ownership,
reverse named returns, exact result contracts, duplicate/conflicting return
handling, resource settlement, parent resumption, nested FLOW completion and
reopen. Another stale controller cannot overwrite a newer projection. Uncertain
ledger writes block current-state reads until reopening. A real cooperative
subprocess increments a file once, returns through the ledger, and its producer
exits47 without cleanup; reopening refuses another dispatch, returns exact bytes
and resumes once. This is not general client/effect exactly-once qualification.

The initial missing-module RED is retained. First focused run passed34/35;
its fault fixture intercepted artifact fsync before any ledger write, so expecting
ledger poisoning was incorrect. The corrected fixture targets the actual ledger
file descriptor; an additional test proves that artifact-sync failure prevents
admission without poisoning an unchanged log. Missing FLOW finish RED2 errors is
also retained before implementing nested/settled completion. No protected
acceptance assertion, reference equation or tolerance was changed.

Required raw evidence is verified member by member on private box-git. Exact
archive bytes, hashes, executed IDs and source fingerprints are in the adjacent
JSON. Source/runtime remains under
/home/dflanag3/src/branchwrite-runtime-active-20261018 on llm-60.
Branch work/branchwrite-frame-kernel-20261018, base c002d7d.

Still missing: production step/run CLI and general decision interpreter, actual
COW/Executor dispatch bindings, grants/relevant-state/budget checks at dispatch,
complete nested type definitions, broad lifecycle/native restart/pressure/fault
qualification and autonomous workload runs. No registered R05 or original VC/G
gate is upgraded here. Numerical oracle/error N/A; no native/GPU jobs started.
No new model failure class occurred, so no fabricated LoRA candidate was added.

Next is to bind the canonical operation registry and program parser to this
controller, then use the existing COW client and Executor through one step/run
kernel. Keep host-only diagnostic getters distinct from causal model visibility;
raw slot availability does not authorize feeding sibling results before a join.
Do not create another target-specific runtime or reuse the protected reference
implementation as production. Chat OFF, Q8 deferred, Linux/private LAN only;
natural-thinking and broader end-to-end data collection remain deferred.
