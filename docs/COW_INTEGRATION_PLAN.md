# BranchWrite on Context COW

Planning revision: 2026-10-16. This is an implementation overlay for the v0.6
contract, not a replacement specification or a claim of product acceptance.
The existing 339 product obligations and 40-ticket dependency graph remain.
No BranchWrite runtime or native adapter is implemented by this document.

## Outcome

Build a real client for several coding-context trees, initially with one active
inference request on one GPU. Pay for the common codebase prefix once where the
COW service can reuse it. Explore independent continuations, run authorized
checks, compare evidence and resume a selected continuation. Test the complete
CLI/HTTP/server/API/native path through this useful workload.

Sampling is a primary exploration mechanism. Different seeds, prompts and
sampling profiles are explicit experimental variables. Branch count and text
variation alone do not establish better results. Measure verified task outcomes
under a common aggregate budget, including failed and abandoned work.

Real tool execution is part of the first vertical slice. Develop the minimum
Phase 3 PLAN/ACT/return path alongside Phases 1 and 2, not after qualifying every
sampler. Its first bounded read/edit/test tool must execute through the actual
enforced host boundary. A text-only agent loop or mocked tool response does not
exercise the feedback, effects, ownership or recovery contract.

The product/command name remains BranchWrite / `branchwrite`. The inherited
handoff names `CC-David-CC/BenchWrite` as its target, whereas this inspected
checkout is `fleet/branchwrite` with private remote
`git@box-git:/srv/data/git/BranchWrite.git`. This plan lives in that actual
checkout. No rename, public repository change or publication is implied.

BranchWrite is a separate application/repository that consumes COW. The two
projects are developed together: the current COW CLI/API is not frozen. When a
real BranchWrite scenario exposes an inadequate boundary, design and implement
the required change in its owning repository, then test both sides together.
Keep model-state ownership in COW and workflow/tool ownership in BranchWrite;
do not build a permanent client workaround merely to preserve an unsuitable API.

## Ownership

| Owner | Canonical responsibility |
|---|---|
| Context COW | Consumed token history, controller state, branch references, checkpoints, pool management and native request/publication receipts |
| BranchWrite | Typed workflow definitions, invocation/frame/slot state, original outbound intent, tool ownership, budgets, observations and evidence references |
| Host/tool boundary | Actual filesystem/process effects, permissions, resource leases and effect reconciliation |

BranchWrite may retain exact submitted input artifacts and human-readable views.
It must not reconstruct a second authoritative model transcript or implement
sampling, grammar matching, KV restoration or token generation itself. A workflow
ledger is not a duplicate of the COW history: it records which computation was
requested, why, under what grant, and which result satisfied which continuation.

One interpreter handles `step`, `run`, child returns, branches and joins. Use
ordinary queues for eligible work, parent-linked records for ownership, and
explicit Ready/Waiting/Settling/Closed transitions. Inference eligibility may be
parallel while GPU execution is serialized. Actual independent tool overlap is
a separate required boundary and remains in the full plan.

Logical parallel eligibility must not assume simultaneous inference. Configure
one execution slot now; future service deployments can advertise several GPU
slots backed by the same RAM/disk pool. Physical placement and capacity do not
define invocation identity, seed derivation, causal visibility or result slots.
Keep compatible-checkpoint routing and hardware qualification owned by COW.

Exercise ordering now without claiming extra GPUs: compute siblings serially,
then buffer/delay delivery so B returns before A. Test duplicate delivery, stale
epochs, a restart between returns and a delayed old result after a new attempt.
Bind every return to its named child/attempt/slot/epoch and source operation;
arrival order cannot select a destination or winner. A serial run with reordered
delivery is ordering/recovery evidence, not physical multi-GPU concurrency.

## Current COW facts and limitations

Inspected source is in `fleet/context-cow-sampler-integration`, private branch
`work/sampler-integration-20261016`. The reviewed integration checkpoint is
`a17e50308e6ca6f9b3b4b5eba650517ffb50ed12`; its production code is unchanged
from the preceding 259-test CPU qualification. Record a new exact pin when the
seed/stop branches integrate; never infer capabilities from this planning date.

Existing CLI controls include context preparation, ask/answer/append/continue,
fork, rewind, saved-answer retry, original-request recovery, evaluation, selection
and adoption. Named GBNF states and sampler controls are exposed. The combined
CPU source has 259 passing checks and G0 51/51. Bounded Q4 CLI workflows exist;
their scope differs from full registered gate qualification.

The frozen combined seed/reseed, STOP, revision-CAS and machine-result v13
source passed 337 CPU tests and G0 51/51. Actual BranchWrite CLI conformance
exposed and corrected a machine-envelope assumption: preparation can legitimately
return an answer object without text. Nineteen client conformance tests then
passed against that frozen source through actual HTTP and CLI subprocesses.
Its first Q4 GPU probe succeeded through preparation, forks and sampled partial
output, then stopped because CLI reseed rejected the harness's `--revision`
argument. Revision-interface correction and the remaining GPU flow are pending;
no restart/STOP success is claimed for that failed attempt.

BranchWrite now has a typed COW client and a bounded Linux executor. Its first
Q4 HTTP coding campaign executed all four example/grammar arms on two tasks;
the four constrained cases passed real edit/test/feedback, and the four
unconstrained cases were rejected for a missing terminal framing LF. See
`validation/CODING_PILOT_Q4_2026-10-16.md` for the exact source scope and limits.
This is a useful first slice, not the complete workflow interpreter or product.

The independent Q4 grammar audit passed 38 exact full-frontier comparisons with
zero maximum logit error, after correcting and retaining the auditor's padded-mask
and receipt-timing failures. Its raw result is retained in COW evidence as
CLI-GRAMMAR-NUMERICS-2026-10-16.json. This covers the earlier frozen grammar CLI
workflow, not the newer combined seed/stop changes. Original cumulative COW G1-G5
remain unqualified. Existing sampler evidence does not prove every
grammar/sampler/stop combination or this future BranchWrite client.

Accepted prototype exactness is bound to the model/build/profile, token history,
operators and ordered request/native batch boundaries. Do not promise equivalence
across different arrangements, hardware or quantizations. Retain existing mismatch
evidence. Q4 is the initial development model; Q8 validation follows a useful,
working Q4 client. No Q8 speed result is inferred from Q4.

## Phase 1: bind one client to the real service

This phase implements R01/R04 and the minimum R02/R03/R05/R08 foundation.

1. Audit the actual source, private remote, dirty state and native service
   ownership. Pin source/build/model/tokenizer/store/profile and supported controls.
2. Build one typed native-client interface. Its operations map to inspected
   `tools/cow_cli.py` commands and `serve/cow_http.py` handlers. Do not invent new
   endpoints or expose internal snapshot formats as a new client protocol.
3. Provide an HTTP transport for ordinary use and a CLI subprocess transport for
   conformance testing. Both return the same typed client results and preserve
   original operation IDs, request bytes and expected revisions. The HTTP path
   need not spawn a subprocess per request. The CLI conformance path must actually
   run the CLI, not call its Python implementation directly.
4. Persist intent before sending. Allow one unresolved mutation per branch.
   On uncertainty, reconcile the original request/receipt; a new operation ID is
   new work, not a retry. A stable URL alone does not identify the same store.
5. Treat streaming as provisional. Distinguish durable partial output, terminal
   model turn, complete parsed typed result and successful host action.
6. Bind sampler profiles to the actual accepted native order/parameters. Record
   requested and accepted identities. Reject unavailable combinations explicitly.

Acceptance: the same prepare/answer/fork/continue/history/retry scenario succeeds
through both transports. Inspect server imports and native work receipts. Inject
a lost response after commit and show recovery returns the original receipt
without additional generation or a second branch movement.

In parallel with that transport slice, implement one registered tool's complete
admission and execution path: exact plan, host grant, owned process/workspace,
bounded resources, observed result and durable typed return. Its harness must
exercise real processes and files and reject unauthorized effects. Test failures,
timeouts, disconnects, descendants and response loss at that same boundary.
Add tools through the same mechanism; do not postpone enforcing ownership until
after an unrestricted executor has accumulated dependent behavior.

## Phase 2: exercise samplers and branch-owned state early

This phase develops R06/R07/R10/R11/R15/R16 through one shared client. It does
not require reimplementing samplers already present in COW.

Start with greedy control output and DRY + temperature + Min-P content. Then
exercise each available experimental family separately before supported pairs.

| Experiment | Purpose | Required state checks |
|---|---|---|
| Greedy | Deterministic control and parity baseline | Legal selection, positions, exact matching-profile continuation |
| Temperature + Min-P, optional Top-K/Top-P | Controlled stochastic exploration | Explicit settings and actual RNG draw cursor |
| DRY | Discourage repeated sequences during open content | Branch-local consumed history, window and native breaker policy |
| Locally Typical | Explore typical information content | Pinned filter order and candidate population |
| DynaTemp | Explore distribution-dependent temperature | Entropy population, bounds and singleton behavior |
| XTC | Explore exclusion of obvious candidates | Trigger draws, exclusions, no-op behavior and exact replay |
| Mirostat 2 | Surprisal feedback exploration | Per-branch feedback state, update/restore/reset semantics |
| Adaptive-P | Selected-probability feedback exploration | Per-branch feedback state, update/restore/reset semantics |

Never combine two terminal selectors. No Python fallback for an unsupported
native profile. Existing prototypes reduce implementation work; they do not
remove the obligation to test the exact client/profile combination.

Use these distinct cases:

- Exact clone: fork an active continuation with its existing RNG/feedback/parser
  progress. Interleave A/B and confirm neither changes the other's state. An
  identical sample is expected when all inputs and state are identical.
- Exploration: fork the common prepared prefix and start a fresh content
  generation with a recorded seed/profile/task. Derive child seeds from stable
  run/attempt/child identity, never launch order. Do not call reseeding an exact
  clone. Do not require different seeds to produce different tokens every time.
- Parameter sweep: fork from one prepared prefix for each configuration; keep
  suffix/boundaries constant when attributing sampler effects. Record actual
  settings and budgets. Do not silently change settings mid-generation.
- Partial continuation: pause at a committed output boundary; continue or
  restart without resetting the draw cursor, DRY history, grammar or feedback.
- Retry: unchanged controls return the saved result and original receipt with
  no inference. Changed controls create a new operation from the recorded source.
- Rejection: incompatible profiles or an active grammar change fail before
  native forward work and do not move the branch.

Measure profile effects on verified coding outcomes, output diversity, token/tool
cost, latency, TPOT, throughput and native state overhead. Include a prompt-change
comparison so sampler diversity is not confused with task diversification.
Use a small bounded candidate set first; fix aggregate budgets before comparing
against one-branch work. Larger experiments report task/seed uncertainty.

### Prepared examples are a first-class experiment

The owner authorizes iterative Q4 model-quality tests with different starting
prefills and additional examples. A role or workflow state may have its own
prepared prefix; READ, EDIT, TEST and comparison need not share one initial
example set. Share numerical prefixes only where canonical ancestry and the
execution contract actually permit it. Different identities may still share
immutable definitions; identical text in unrelated paths does not prove shared KV.

Run the minimal real task first with the smallest existing prefix. Compare four
conditions even if that baseline passes: unchanged, one targeted example only,
GBNF only, and the same example plus GBNF. This supersedes the earlier rule that
example experiments start only after a failure. Keep the production baseline
unchanged until the comparison supports adopting a candidate. Add more examples
only if the one-example candidate is inadequate; large collections remain an
escalation, not the starting point.
Retain complete failures, diagnose them and compare pinned candidates. Freeze
each candidate's exact bytes/tokens, template, tokenizer, position configuration,
native schedule and sampler settings. A changed early example produces a new
prepared computation; never relabel an existing checkpoint or reuse invalid
descendant state. Measure prefix construction once and actual later reuse, rather
than rerunning the expensive preparation for every small question.

For each four-condition comparison, keep the task, authorized actions, protected
tests, sampler settings, output limit and attempt budget fixed. Use the same
recorded seed for paired stochastic trials, without requiring identical output
when the prompt or legal-token set changes. Record actual prefix tokens and
grammar identity: example and grammar conditions are distinct computations,
not interchangeable checkpoints. Test the same small task variants in every
condition, including variants not shown in the example. The first greedy pilot
is a bounded comparison; stochastic quality claims need repeated seeded trials.

Measure verified task success separately from parse/schema success. Retain the
actual proposed patch and final answer, test outcomes, unauthorized or rejected
actions, incomplete output, retries and timeouts. Use a fixed task-specific
rubric for factual accuracy, required details and unsupported claims; do not
award quality merely because the grammar accepts the answer. Compare output
length, latency, TTFT and token/tool costs, with prefix preparation and reused
request costs reported separately. A grammar that forces a legal but wrong
action, an example that encourages copying the wrong details, or their
combination reducing answer quality is a regression to report. Do not enable
either intervention universally based only on one successful fixture.

Separate error classes: prompt/example tuning can address the model selecting a
poor legal action or producing a poor patch. Parser bugs, stale references,
unsafe execution, missing returns, duplicate effects, hangs and deadlocks require
runtime fixes. Do not hide them with padding, more examples or automatic repair.
Grammar may enforce punctuation; a comma or semicolon split across tokens or
requests must not stall the interpreter. A valid request that cannot progress
must produce a bounded, explicit outcome with its unresolved ownership preserved.

Include progress/deadline witnesses across model requests, parsing, tool dispatch,
child returns and parent resume. Test incomplete output, malformed delimiters,
UTF-8 and punctuation splits, declined actions, timeouts, lost acknowledgments
and reverse-order returns. Use bounded attempts per campaign while permitting
further recorded development iterations; do not spin forever on a failed action.

Keep regression tasks and some held-out task variants separate from the examples.
Tuned-case success and generalization are different results. Record failed
attempts and preparation cost when comparing strategies. The goal is an excellent
user experience; a SOTA claim would require a separate fair comparative campaign.

The owner also proposes an eventual experiment with roughly 600K tokens of
examples under a 4x YaRN positional configuration. This is not a currently
qualified capacity. Inspect backend/model support, maximum positions, cache
allocation and RAM/VRAM/disk budgets; pin all positional settings into execution
identity. Qualify numerical continuation and restart under that same arrangement
and evaluate task quality before claiming success. Expand from small fixtures
through useful intermediate lengths, retaining prepared states for reuse. Record
initial prefill, restore/transfer and long-context per-token costs separately;
cache reuse does not make the initial computation or long-context attention free.

The initial larger-context testing range is 8K through 128K, used as needed.
Select the smallest sufficient prepared context for each test; this is not a
requirement to run every length or grow large example sets for passing tasks. The
current pinned COW test profile has capacity 98,304 tokens. Tests beyond that
capacity require a separately qualified execution profile and capacity check,
not reuse of an incompatible saved checkpoint. The 600K/YaRN proposal remains
a later experiment beyond this initial range.

## Phase 3: the first complete coding session

Implement the original R12/R13/R14 requirements using the same interpreter.
Start its minimal executor/return slice while Phases 1 and 2 are being built.
The complete nested session remains the milestone; the phase numbering does
not create a dependency on every sampler experiment finishing first.

1. Observe and pin an owned small project and its protected checks.
2. Prepare its model prefix once. Generate a design through native constrained
   output and retain its real receipt.
3. Freeze a concrete authorized tool action from observed inputs. Execute it
   through an enforced host boundary; a directory alone is not containment.
4. Save the tool result artifact, then record its typed return into the exact
   parent/attempt/slot/epoch. Kill the owned client after that record but before
   parent resumption.
5. Restart. Consume the saved return once, without redispatching the tool or
   regenerating its output. Continue the correct native model context.
6. Propose and apply a bounded fix in the owned workspace; run protected checks
   and record observations. Generate separate headline/status/summary/final
   outputs without polluting the Builder context. Factual status remains a
   ledger projection.
7. Publish only when the task requires it and the target/grant/evidence guards
   succeed. Do not modify a user's live checkout as an implicit publication.

Use the `.bw` contract and one canonical type definition source. Existing
reference code remains an independent oracle. Literal control-looking text,
UTF-8 splits and incomplete records must not become executable actions.

Named static server grammars can prove an initial fixed-state path. Full R06
requires a reviewed mechanism for frozen, host-derived eligible choices. Design
registration, compilation ownership, identity, authorization and lifetime at the
COW boundary before adding it. Do not send arbitrary model-provided grammars or
silently reset a live matcher. Static-grammar success is not full dynamic-grammar
qualification.

## Phase 4: useful branching and integrated recovery

Develop R22-R29/R31 using the same full pipeline, rather than a second harness
that bypasses the client.

- Expand two fixes from one prepared codebase, using explicit exploration inputs.
  Reverse/interleave their completion; retain named results independent of order.
- Execute eligible tool actions in independently enforced scopes. Record actual
  overlap where required. One GPU inference slot does not forbid tool overlap.
- Compare protected evidence, select an alternative, or explicitly compose
  complementary artifacts and verify the new integration state. Never merge KV,
  grammar progress or sampler feedback.
- Exercise retry/navigation, branch changes, client disconnect, server restart,
  partial grammar/UTF-8/stop state, stale CAS and lost acknowledgments through both
  client transports where applicable.
- Exercise RAM eviction, disk eviction/expiry, interrupted publication, bounded
  disk-full and memory pressure. Keep canonical retained history where possible.
  Exact-resume mode rejects missing numerical state; separately authorized
  reconstruction reports charged prefix work and its new lineage explicitly.
- Preserve unresolved-effect ownership and reservations across failures. Abandon
  means non-adoption and settlement, not fictitious rollback.

Use small fixtures to catch failures quickly, then an 8K prepared codebase with
different bounded questions and outputs. Only expand to several realistic long
codebases after the small full-path recovery cases pass. Reuse the shared RAM/disk
pool; do not introduce a BranchWrite checkpoint cache or residency lock.

## Phase 5: qualification and performance

Retain R17-R21 and R30-R40, conditional MTP and every inherited case. Prioritize
reusing source-bound native law evidence where applicable, then execute the
missing client combinations and interaction tests. A reused result must have the
same relevant dependency closure; a neighboring sampler pass is insufficient.

For each completed stage report executed IDs, passes/failures/skips/unrun cases,
original commands, code/build/model/profile identities, real work counters,
checkpoint I/O/copies, memory, latency, TTFT, TPOT and generation throughput.
Keep startup, prefix creation, resident reuse and disk restart timings separate.
Audit runs are not performance runs; report instrumentation overhead separately.

The end goal remains accelerated long-codebase work: reusable large prefixes,
new questions, useful multi-thousand-token answers and native-like continuation speed.
The user's Q8 goal is roughly 40+ TPS where feasible, with lower throughput at
long contexts accepted and 30+ TPS branching already considered useful. These
are measurement objectives, not unexecuted acceptance results. Record validation
overhead against the accepted roughly 8% preference; exceeding it is a reported
tradeoff, not permission to drop integrity guarantees or discard correct work.

Q4 is first; validate the integrated useful workload on Q8 afterward. Future
GPU placement belongs to COW: independent GPU slots or explicitly grouped model
devices, one active request per configured slot. BranchWrite reserves advertised
service capacity instead of inventing GPU scheduling or double-counting roles.

## Handoff and scope of this planning change

Keep code, plan and evidence private on this PC and box-git. Windows drives
editing/Git/SSH only; tests and model work run on authorized Linux hosts. The
ordinary chat server stays off. Root owns GPU launches, one inference job at a
time on llm-60. No new deployment, download, public push or upstream PR follows
from this plan.

The inherited offline handoff verifier is tested on a clean exported payload,
not inside `.git`. Baseline export of `23b8c62` fails manifest coverage because
the owner-provided PDF is tracked but missing from the payload manifest. The
planning revision updates that manifest along with authored plan/pointer files;
it does not alter the PDF, reference equations, runtime code, tests, acceptance
statuses or the active v0.6 specification. Validate the exported updated payload
and retain both original failure and corrected result.

Implementation is authorized. The first client slice starts in the separate
`fleet/branchwrite-cow-client` worktree on `work/cow-client-20261016`, alongside
the ongoing COW seed/stop work. Develop the Phase 1 client, the Phase 2 sampler
slice and minimum real tool executor together, pinning each tested COW revision.
Begin with actual capability discovery, not the historical CLI reference or
the provisional configuration names in this handoff. Run the complete first
native workflow when the required service controls are ready; full G1-G5
certification is not a prerequisite to starting the consumer application.
