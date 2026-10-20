SC16 original diagnostic FAIL retained,exit1. All three GPU requests completed.
Warmup32tokens;baseline128tokens/12.386992s whole request;profile128/14.482567s.
Token IDs match exactly. Exposed thinking fields schema/progress/complete/reasoning/
final text match. Original assertion compared entire thinking objects and failed
on snapshot identity. Canonical objects differ ONLY controller.stream_key;
both next_draw=0. real.py's scope transition hashes each generation stream into
that key. Distinct fresh requests are not identical full controller records.
Each thinking snapshot points to its own committed receipt. No original script,
assertion or result was changed to call this a PASS. This is an engineering
fixture assumption,not an observed model failure or a LoRA candidate.
No full-logit/frozen-profile numerical certification is claimed.

Profile covers one existing ContextCoordinator._run on the designated branch.
Instrumented worker span12.6141s. input_binding called388times,2.8696s cumulative;
native_tokens647times,1.0901s cumulative (overlaps binding,do not add).
Millions of token packing/iteration calls merit a bounded derived-binding cache
review. Native validation/hashes must remain;no speedup has been implemented.
Profile timing includes cProfile overhead;one pair is not a stable speed estimate.

Work: zero initial saved-prefix forward tokens,6960newprefill+288generated=7248
actualforward tokens,zero integrity mismatches. Saved prefix unchanged. Owned
server/native exited0,keys revoked,original SSH keys byte-exact,GPU free.
Shutdown did not produce the optional atexit hook-summary file;the completed
per-request profile exists. Do not invent an absent hook summary or soak result.

Next: read authoritative COW spec/current input-history/backend code. Test-first
bounded cache for repeated expected binding work only if immutable-history and
lease-invalidation proofs support it. Preserve actual native identity comparisons,
foreign-thread/stale-lease rejection,positions,image state and byte-integrity guards.
Measure uninstrumented benefit and qualify the resulting source/profile explicitly.
Normal dev16/SC15 remain unchanged and passed;overall standalone goal stays active.
