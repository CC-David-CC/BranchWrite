# Current state, 2026-10-20

This file records the work order; executed outcomes live in
`validation/CURRENT-CATALOG-STATUS.md` and per-run JSON evidence. The latest
catalog result says Basic Agent Loop H00-H12 passed 13/13 in bounded autonomous
Q4 runs. The next workload family is Ubuntu Agent Baseline, starting with L00.

The Ubuntu baseline is not yet a clean pass ladder:
- L00 has positive host/identity/file observation subcases, but a prior complete
  greedy run failed because the final report copied observed values incorrectly.
  A separate controlled wrong-host admission check passed; that does not repair
  the final-report failure.
- L01's individual stdout/stderr, exit, pipeline and binary cases passed, but
  the final answer was incomplete/garbled. Treat L01 as an overall failure until
  an independent complete report passes.
- L02 has bounded greedy-pass evidence. L03 has no complete recorded pass.
- L04-L06 and the Ubuntu job/admin assignments remain ahead of this first
  terminal/config ladder.

The project roles are:
- BranchWrite is the user-facing CLI/client and owns the task workflow ledger,
  grants, tool policy, operation IDs, receipts and recovery commands.
- Context COW is the HTTP server and canonical owner of conversation branches,
  controller histories and optional RAM/disk compute checkpoints.
- The Strata-derived native engine performs inference and native KV/state work.
- The workload harness owns independent expectations and fault/evidence checks;
  it is not another runtime or canonical history store.

Do not infer that a passing unit suite is a complete task pass. Keep the
per-run distinction between model output, host evidence, protected acceptance,
and recovery. The detailed older planning notes below are retained as history;
their H06-H12 ordering and status statements are superseded by the current
catalog page.

---

# Workload progression and independent rerun contract

Owner direction, 2026-10-18. This is an implementation plan, not executed proof.

Complete Basic Agent Loop before advancing to Ubuntu Agent Baseline. Current
bounded evidence covers H00-H05, with the original H03 observer failure and
separate passing mitigation retained. H06-H12 remain NOT_RUN. Older catalogue
paragraphs below the latest entry are historical, not current instructions.

## Development and release from supervision

During development, the implementer may guide attempts, improve BranchWrite's
existing tools and execution harness, update reusable templates, JSON/GBNF
schemas, and zero-shot instructions, then add independently owned few-shot
examples where useful. Zero-shot instructions and few-shot examples are distinct;
record which was actually used. If a COW CLI/HTTP/API boundary fails, repair that
boundary rather than bypassing the real client. No second workflow runtime.

Every attempt retains its actual inputs, source hashes, outputs, receipt IDs,
tool effects and independent result. Owner authorizes guided development beyond
one failed attempt; record each attempt separately, rather than silently retrying
inside an allegedly single-attempt test. Default task-run repair limits stay
explicit and bounded. Never edit protected assertions or feed their answers,
reference pages or implementation into the candidate context.

The exit check for each supported task is a fresh, independently checked run
through BranchWrite -> COW CLI -> HTTP -> server -> GPU -> authorized real tools.
Freeze the improved client, templates, examples and grammars before this run.
No implementer supplies an intermediate action, edits the candidate file, changes
an answer, or resumes a stuck decision during that final run. Otherwise label it
a guided development result, not autonomous success. Include a broader frozen
rerun after cross-cutting changes; do not claim success on untouched catalogue
cases from unit-test counts.

New model tasks start with1024 thinking tokens (owner update2026-10-18). Extend only if the budget is
exhausted AND the task fails. A natural end or success stops escalation. Q4 is
primary; Q8 remains deferred. Preserve allowed settings, branch-local state,
consumed-token publication and original operation IDs for reconciliation.

## Ordered targets

1. H06: add a functioning click counter while retaining H05's two-square page.
   First missing boundary: the production isolated capture admits only H03-H05
   and never invokes the supplied protected interaction checks. Add behavioral
   tests before extending the real browser path. A screenshot alone cannot prove
   a click or a changed counter. Bind tool actions to the actual source revision.
2. H07: input and greeting, including literal markup as text, with H06 preserved.
3. H08: one local image; grant and serve only captured approved assets, not host
   directories. Retain source/asset/image identity and browser isolation tests.
4. H09-H10: external CSS, then external JS, retaining earlier behavior and
   immutable multi-file capture identities. No unrestricted resource fallback.
5. H11: observe and repair the injected runtime defect from real error evidence.
6. H12: desktop/mobile viewports with no horizontal overflow and preserved
   interactions. Complete the basic HTML series and rerun its supported path.
7. Ubuntu Agent Baseline: L00 -> L01 -> L02 -> L03, one selected target at a time.
   Then its declared L05 job loop, followed by A04/A05 only after scoped user-unit
   grants and real user-manager preflight. L04/L06 remain separately tracked.
   Never run planted defects against llm-60's actual inference/chat service.

T/C/B later tracks stay separately NOT_QUALIFIED until actually executed. The
sequence above does not automatically complete them or original G/VC gates.

## LoRA collection

Capture generalizable model failure classes in
/home/dflanag3/src/branchwrite-lora-examples/candidates/ under its existing rules:
actual failed prompt/output, images when relevant, model/profile/tokenizer,
template/schema/sampler/thinking settings, source and evidence hashes, violated
invariant, mitigation outcomes and a generator brief with held-out separation.
Keep single observations labelled as such. Reuse a class instead of duplicating
large archives. Infrastructure failures remain engineering evidence. Protected
answers are not training examples. No training/export/publication is authorized.

## Placement and evidence

Windows is a read/transport steering station only. Execute, edit and collect on
Linux. llm-60 GPU0 runs one inference job at a time; the chat service stays OFF.
Keep raw evidence outside source checkouts and check capacity before launching.
Back up reviewed work to private box-git only; GitHub and Strata need separate
approval. Current COW auth pass still needs independent audit and archival;
current-profile sampled-controller coverage remains a separate open item.

Current source: /home/dflanag3/src/branchwrite-active-20261017.
Input packs on the Windows steering station:
C:/Users/dflanag3/Documents/fleet/branchwrite-workloads/
  basic-agent-loop-codex-handoff-v0.1.0/
  ubuntu-agent-baseline-codex-handoff-v0.1.0/
These are protected workload inputs, not model-visible runtime templates.

## Deferred research: natural thinking termination

After the initial end-to-end path, measure natural reasoning lengths under
larger caps on frozen tasks and compare quality, latency and token cost. The
successful H06 edit hit512; its natural stopping point is unknown. No escalation
was needed for that success. This is a recorded research vein, not an additional
current milestone gate. The owner subsequently raised the default for NEW
admissions to1024; recorded512-token successes remain unchanged.

## Owner clarification: independently capable product

The goal is BranchWrite choosing and completing work through its own reusable
CLI/interpreter. Tests are replaceable diagnostics. H06 passed a scripted
component flow; it did not establish a general agent. Current inspection finds
COW client, grant-checked executor and browser modules, but no production CLI
decision interpreter. Build the existing v0.6 interpreter/tool-admission path
rather than another target-specific driver. Keep one workflow authority; do not
ship the protected reference runtime as a second runtime or create a shadow
model transcript. Task IDs and expected answers belong in protected fixtures,
not product decisions. The model chooses registered tools and arguments; the
host validates permissions, budgets, source revisions, effects and completion.

Next: inspect canonical v0.6 parser/frame/return obligations and existing adapters,
then test-first connect a general read/edit/execute/observe/finish decision loop
to the real COW client and existing Executor. Let that loop tackle H07 and later
workloads. Freeze a run on changed task bytes to check transfer without model
or implementer access to its protected expected result. Capture failed model
classes and improve reusable templates/grammar/examples, with every attempt
retained. Do not call a new task-specific scripted pipeline independent ability.

Default update2026-10-18: use1024 thinking tokens for new admissions. Keep all
existing512-token successes, captured registry definitions and controller states
unchanged; do not rerun old successes merely for this change. Broader end-to-end
data collection and natural-cutoff research remain deferred.
