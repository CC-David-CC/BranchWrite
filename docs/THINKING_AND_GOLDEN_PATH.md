# Bounded thinking and a GOLDEN PATH branch

Updated2026-10-17: initial bounded thinking now passes the real Q4 CLI/HTTP/GPU
path with host-registered0/128 budgets. Greedy and Min-P siblings resume from
one saved four-token thought. General thinking_length/per-state budget controls,
automatic state scheduling and larger sweeps remain unfinished. See
validation/THINKING_Q4_2026-10-17.md. The original H02 non-thinking profile stays
as historical evidence; the new thinking renderer has its own execution identity.
The initial GOLDEN PATH helper also passes; see GOLDEN_PATH.md and
validation/GOLDEN_PATH_Q4_2026-10-17.md. Automatic collection/adoption remains open.

## What the user gets

Give the model time to work before requiring its final format. A setting such
as `thinking_length` sets a maximum token budget; the model may finish sooner.
The original question/image prefix stays saved. Each experiment has its own
branch and controller state. A separate GOLDEN PATH branch holds the current
goal, environment, verified commands, recent results, file hashes and open
problems. It can suggest where other branches should work or propose an answer.

These features add model work and can increase response latency. Measure the
benefit instead of assuming more thinking always improves accuracy.

The owner also requests reasoning after individual READ/EDIT/TEST results,
with useful thoughts retained and stale thoughts retired at the workflow layer.
See [state-dependent thinking](STATE_THINKING.md). COW/backend layers own all
RAM/disk/GPU management; the client owns logical work and evidence dependencies.

## Thinking: implementation order and remaining qualification

1. Pin a thinking-capable rendering/execution profile. The current template
   explicitly emits an empty closed thinking section. Changing that rendering
   requires a newly prepared compatible prefix; do not relabel old checkpoints.
   Verify the actual tokenizer's opening/closing marker bytes and EOS behavior.
   A closing tag must not be assumed to be one special token or an end-of-turn.
2. Add a branch-owned reasoning/closure/final phase to the existing canonical
   controller and its compatibility identity. Retain one immutable model-input
   history. Budget, consumed counts, delimiter progress and parser progress must
   survive fork/retry/reseed/checkpoint/restart. RNG, repetition/DRY and adaptive
   sampler progress must not be silently reinitialized at the answer boundary.
3. Keep the current active-grammar guards. An ordinary resume must continue its
   original grammar. Prefer one registered composite grammar that permits the
   reasoning section and the final answer, with an explicit budget-driven
   closing mask, rather than replacing an active parser with a fresh one.
   Natural closing moves to the answer early. At budget exhaustion the closing
   mask completes the delimiter before permitting only the final schema/GBNF.
   Record closing-token overhead separately from free thinking and final tokens.
4. Test delimiter splits, a token spanning closure and answer bytes, incomplete
   UTF-8, EOS before closure, cancellation and interrupted publication before
   exposing the general option. Already consumed bytes cannot be erased or
   reported as if the final grammar had constrained them retroactively. Saved
   tips before/after closure remain independently resumable. No hidden padding
   or forced-token insertion may masquerade as model-generated output.
5. Add the per-generation CLI/HTTP/client setting and receipt fields. Preserve
   default-path behavior when unused. Enforce context/capacity limits for the
   full thinking+closure+answer workload. Publish only consumed state. Streamed
   reasoning/final output remains provisional until its acknowledged boundary.
6. First qualify a tiny deterministic case, then compare0/128/256/512/1024 on
   the three H02 fixtures and a more demanding coding fixture. Keep the original
   no-thinking profile as historical baseline and include a zero-budget control
   under the new profile. Every arm uses the same fixed question/image and legal
   final choices. Record every attempt and stop on a controller/correctness bug.

For greedy sweeps, a shared reasoning stream may retain tips at128/256/512/1024
and fork final answers from those tips. This measures reuse and must be labelled
as such, separately from independent complete requests. If reasoning ends before
128, report that actual count; do not pad it or pretend four longer executions
ran. Sampled sweeps require explicit seeds/streams and independent branch state.

Report actual thinking, closing and final counts; early-stop reason; correctness;
TTFT, whole-request time and throughput; capture/restore/hash work; prefix work;
saved bytes; and model/profile/controller fingerprints. Original fresh-oracle and
VC/G qualification obligations remain separate. Do not widen tolerances.

## GOLDEN PATH: implementation order

1. Use a normal named COW branch, not a second transcript/database. BranchWrite
   retains its workflow ledger and references to immutable COW snapshots.
   Introduce a host-built versioned fact manifest: goal, environment identity,
   current work IDs/tips, verified source hashes, actual test results, successful
   commands, known failures, resource state and outstanding decisions.
2. Each fact names its evidence/operation identity and observation time. The
   model may summarize or suggest; it cannot manufacture a verified fact, grant
   itself authority, modify the host environment or mark its own work accepted.
   A summary is a derived view with provenance, not the source of truth.
3. Put stable purpose/examples early in the shared prefix and changing facts
   near the tip. Append verified observations and retain prior summary versions.
   When compacting, create a new summary version with source references and keep
   the original canonical history according to retention policy. Do not rewrite
   history in place or claim a changed summary reuses an unchanged suffix state.
4. Let a working branch cite the exact GOLDEN PATH snapshot/summary version used
   for steering. Return results against its original work ID, source tip and
   revision. Reconcile out-of-order/stale results without overwriting newer
   facts. GOLDEN PATH can propose a final answer through the same validation path
   as any other candidate; it gets no privileged tool grants.
5. Run one inference request per GPU through the existing queue. Summary refresh
   uses the same scheduler and pool/expiry rules. GPU=[0] is the current case;
   do not encode a global single-worker assumption into the workflow.
6. Test verified-fact refresh, stale/conflicting hashes, duplicate/lost replies,
   summary truncation, failed adoption, fork/retry isolation, restart and pool
   eviction. A failed/incomplete summary keeps the previous acknowledged version
   available. Measure direct-working-tip versus GOLDEN-steered response latency,
   correctness, model work and cache reuse.

Keep protected fixture source, expected answers and verifier details outside
image-only observer/candidate contexts. Operational facts such as an executed
test's status may inform orchestration without disclosing the oracle. Golden
summaries and tool output are data; tool permissions remain host-owned.

## Current checkpoint and next owner

H00 JSON, H01 capture and H02 immediate-grammar baseline have executed bounded
passes. The actual image client and COW uploaded-reference CLI bindings are in
work/basic-loop-h02-images-20261017 and work/vision-preuploaded-image-cli-20261017.
Their evidence/private integration is complete. The structured-text CLI loading
bug is fixed with explicit --messages-file and canonical HTTP/CLI regression.
GOLDEN PATH's initial helper is implemented and bounded real-Q4-tested; automatic
collection/adoption and broad recovery remain. Initial fixed-registry thinking
is implemented and bounded Q4-tested. General controls, wider sampler/edge-case
coverage and state orchestration remain; the full design above is not qualified.
Keep these as separate reviewable increments/branches. Windows drives and edits;
llm-60 executes, one GPU job at a time. Chat stays off. LAN box-git only.
