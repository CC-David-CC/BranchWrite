# Current goal: push-button autonomous coding,2026-10-18

Owner selected a generic executable .bw workflow as the immediate delivery target.
Read docs/AUTONOMOUS_RUN.md for the one-interpreter run/step CLI, config, supported
handlers and explicit limits. One bounded real Q4 autonomous task now passes; see
validation/AUTONOMOUS-CORE-2026-10-18.json. Broad workload validation remains open.
The original VC/G qualification scope remains open.

---

# Codex / Luna entry prompt

Implement BranchWrite in the actual `CC-David-CC/BenchWrite` checkout using this v0.3.0
handoff and the v0.6 proposed contract. Preserve existing instructions and uncommitted
work. Begin with source/capability discovery, not a new repository or a second runner.

Replace the old seven-verb execution abstraction with one typed computation model:
EXPAND, CONTINUE, PLAN, ACT, OBSERVE, TRANSFORM, SAVE, VERIFY, CHALLENGE, COMPARE,
SELECT, COMPOSE, COMMIT, ABANDON; retain the six structural constructs.

A PLAN freezes exact relevant input state, operation definition, generation controls,
world effects, output/evidence contract, authority dependencies and budget. It is not
an authorization. Dispatch rechecks relevant preconditions, never a global head that
would invalidate an independent sibling. Do not bind later actions to obsolete initial
file states: each dependent action is frozen when its actual inputs exist.

Keep the canonical workflow in typed .bw text. Explicit JSON/JSON Schema model output
is supported beside GBNF (owner policy2026-10-17); schema validity never grants execution.
One definition source drives each output validator and grammar. No regex command mining,
partial-stream execution or hidden repair loop. Preserve exact raw data and keep native
transport behind the source-pinned COW boundary. Canonical typed values must not undergo
a lossy JSON round-trip merely because a model uses JSON output.

Grammar matching and every stateful sampler are native per-branch decode state. A
committed active partial resumes its matcher and sampler; a new output contract begins
at a legal boundary. A clone preserves RNG exactly. Explicit seed splitting creates a
new exploration lineage. Rejected probes, drafts and previews cannot mutate committed
state. No generic `accept(token)` replay is presumed to recover feedback samplers.

PARALLEL.PLAN forks one immutable input base into independent model expansions.
PARALLEL.DO dispatches several already eligible computations in enforced independent
world scopes, subject to shared-resource leases and the one scheduler's budget.
A read-only planning scope cannot acquire project-write authority from generated text.
A Git worktree alone is not an arbitrary-code sandbox. Joins bind typed named slots;
SELECT does not merge alternatives, COMPOSE does not merge KV, and COMMIT needs fresh
verified evidence and guarded publication.

Write failure-distinguishing tests before implementation. Preserve the migrated 211
old case obligations and new cases. The first complete session includes native typed
requests/returns, actual bounded effects, verification, headline/status/summary/final
invocations, and a real restart after child return before parent resumption. It resumes
once without rerunning the tool or generation. Then prove grammar/sampler isolation,
interleaving independence, true execution overlap, uncertainty preservation and resource
accounting. Use the same runtime for `step`, `run`, tools and generators.

Parallel workers may own language/grammar, native decode state, and effect/recovery
work after their shared types are frozen. DynaTemp and Typical can be parallel;
XTC, Mirostat 2 and Adaptive-P share infrastructure but not algorithm dependencies.
Use one selector interface and one owner of mutable state, not multiple decoding loops.

Report exactly what ran. Never call an offline oracle native parity, never call a
scripted fixture a model result, and never call an unknown external effect failed.
