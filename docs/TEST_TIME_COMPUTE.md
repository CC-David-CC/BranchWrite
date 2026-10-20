# Spend computation on information, not repeated ceremony

The pinned objective for the first campaign is **verified task completion under a common
aggregate budget**, with wall time, latency and resources also reported. More branches,
more tokens or more diverse text are not automatically better.

Use the following policies through ordinary typed computations and the one scheduler.
They are policies over the same graph, not extra agent controllers.

1. Observe and pin one truthful source/input base. Reuse its native prefix only when the
   backend proves it avoids physical evaluation/copying. Keep logical and physical counts.
2. Expand a small bounded candidate set with explicit task/seed/profile differences.
   Compare against a one-branch baseline using the same aggregate token/tool budget.
3. Run cheap admissible checks before expensive effects; retain rejected candidates and
   their costs. Do not let generated confidence substitute for a check.
4. Continue promising unfinished candidates only under a pinned cost/exit rule. Widen
   later only when the rule and remaining budget permit. Equal small initial slices are
   an experimental baseline, not a theorem of optimality.
5. Challenge a prospective winner using a separately scoped critique/probe proposal.
   Execute proposed probes through PLAN/ACT. Critique text is not failing-test evidence.
6. Select alternatives. Compose complementary work only when needed and reverify the
   combined exact state. Publish once through the declared guarded boundary.

The first native campaign compares constrained greedy, available DRY+Min-P, and explicit
branch diversification. Add Typical/DynaTemp/XTC/Mirostat/Adaptive-P independently, then
selected interactions. Do not compare a 4-branch 4x-token run to a 1-branch run and credit
all improvement to branching or the sampler.

Record task ID, source and verifier contract, candidate count, seed policy, profile/order,
logical prefix length, actually evaluated input/output tokens, sampling overhead, native
calls, physical cache reuse, peak memory, wall time, tool time, cancellations, abandoned
compute, outcome and evidence references. Budget exhaustion/failed/unknown candidates
stay in the denominator. Report per-task paired results and uncertainty across tasks/seeds.

Measure collisions/near-duplicate proposals, stale plan incidence, invalid syntax/semantic
rejections, verifier disagreement, integration conflicts, source changes and unknown effects.
Early pruning has false-negative risk; keep an audit sample of pruned candidates for deeper
checks where budget allows. A learned allocation policy is later research, not the first
implementation dependency.

A deterministic singleton host choice can bypass inference as an ordinary pure computation.
This does not authorize skipping model state updates for forced tokens in an ongoing native
generation. Cache/deduplication must preserve distinct call/evidence ownership and obey the
computation's purity/nondeterminism contract. Never deduplicate ACT/COMMIT by visible text.

No particular branch count, token slice, device utilization or speedup is asserted here.
Bind actual budgets and measure. The old handoff's real-backend reuse/latency campaigns
remain required; the new sampler overhead must be counted rather than hidden.
