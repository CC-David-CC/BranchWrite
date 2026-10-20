# BranchWrite — first-principles contract v0.6

Status: proposed replacement contract. Handoff version 0.3.0. Product command `branchwrite`.
This is the only active system specification. Supporting documents make examples and
acceptance procedures concrete; source v0.4/v0.5 are retained as history.

## 1. Outcome and design boundary

BranchWrite is a local durable execution environment for typed computations involving
models, tools and evidence. It lets a user explore alternatives from exact context
states, perform authorized work in independent physical scopes, compare the results,
and retain a selected, verified outcome with its causal history.

The objective is useful verified work per bounded compute/resource budget. Branching is
a means, not a success metric. No claim of universally optimal test-time compute follows
from having a tree. The optimal allocation depends on task rewards, costs, dependence
between samples, verifier quality and unknown future outcomes.

One interpreter owns workflow transitions. COW owns native model context. Actual
operating systems and services own external reality. Immutable artifacts own retained
bytes. A Git reference, where configured, owns published code identity. None is a
substitute for another. A model proposes data; grammar limits syntax; grants authorize;
execution changes the world; observations support verification.

## 2. One execution unit

An admitted computation consists of a pinned operation definition, typed input bindings,
parent/attempt ownership, a result contract, a continuation, relevant state dependencies,
budget and resource requirements. It runs through the same interpreter whether it is a
model expansion, a title generator, a local comparison, a tool invocation or publication.

A proposal is untrusted data. A frozen plan is immutable computation data. A grant is
permission for that plan. A result is a typed value with provenance. A verified result
is a result bound to sufficient evidence under a pinned check contract. A selected result
is a chosen reference. A published result additionally has a checked publication receipt.
These are separate domain meanings, not interchangeable booleans.

The definition of an operation declares whether it is pure, generates model output,
observes a resource, or changes a resource. The verb is not permission to hide effects.
A model-assisted COMPARE, a pure TRANSFORM and a tool-backed VERIFY all use the same
invocation mechanism with explicit implementations and declared effects.

## 3. Executable operations and intent vocabulary

| Operation | Meaning | Must not imply |
|---|---|---|
| EXPAND | Generate a new proposal/continuation from declared native state and inputs. | Automatic world mutation or a new grant. |
| CONTINUE | Resume the same durably committed active model turn, preserving output progress. | Append a new user turn or reset grammar/sampler state. |
| PLAN | Validate and freeze a proposed computation against relevant exact state. | Permission, dispatch or execution success. |
| ACT | Dispatch the exact authorized effect computation in its bound world scope. | Interpret arbitrary generated text as a command. |
| OBSERVE | Acquire bounded observations through a registered read/observation capability. | Run arbitrary programs under a read-only label. |
| TRANSFORM | Produce a derived value/artifact from immutable inputs. | Mutate its source, erase provenance, or condense runtime obligations away. |
| SAVE | Pin/retain an already durable named result under a retention policy. | The first durable recording of effects. |
| VERIFY | Apply a pinned evidence/check contract and return a typed disposition. | Trust a model's claim of passing tests. |
| CHALLENGE | Seek counterexamples, missing assumptions or additional probes. | Weaken protected checks or execute invented tests without a plan. |
| COMPARE | Produce a source-bound comparison under named criteria. | Choose a winner merely by generation order. |
| SELECT | Select declared eligible references under a pinned rule. | Merge contexts or inherit acceptance for changed bytes. |
| COMPOSE | Construct an explicit combined artifact/program/input set from selected inputs. | Blend KV/parser states or claim component acceptance proves integration. |
| COMMIT | Publish an eligible result through a declared guarded external boundary. | Approve arbitrary actions, or conflate native token receipts with publication. |
| ABANDON | End an attempt without adoption, retaining history and settling obligations. | Roll back external reality or drop unknown work. |

The prior ASK / DO / LOOK / CHECK / STOP spellings are human intent categories used in
migration documentation. They are not a second accepted runtime instruction set. ASK
elaborates to EXPAND, CONTINUE, TRANSFORM or COMPARE by actual purpose; DO to ACT or
COMMIT; LOOK to OBSERVE; CHECK to VERIFY, CHALLENGE, COMPARE or SELECT. SAVE and PLAN
retain their explicit meanings. Ambiguous historical programs require a recorded rewrite,
not a guessing compatibility parser. Successful completion is a typed return from a
settled invocation; STOP does not mechanically become ABANDON for successful work.

Operation and call identity are different: repeatedly executing one EXPAND syntax node
creates different invocation IDs. For an active output, CONTINUE is a separately
identified native operation within the same logical generation/result invocation.

## 4. Structural composition

FLOW defines ordered composition and typed inputs/outputs. REPEAT has an explicit bound,
exit predicate and exhaustion disposition. BRANCH creates a child scope with declared
inherited inputs and independent future history. ON handles a declared typed signal in
an ordinary bounded scope; it cannot broaden authority or swallow unresolved effects.

PARALLEL.PLAN denotes several eligible model computations sharing one immutable input
base, with independent native continuation state and subsequent context histories.
It does not refer to concurrent calls of the local PLAN freezing operation alone.

PARALLEL.DO denotes several eligible ACT computations, independent branch-local world
scopes, and scheduler permission to dispatch them concurrently. It is not an instruction
to run a list of shell strings in an invisible worker loop. A single eligible ACT uses
the same dispatch path. Resource contention may serialize work even in a parallel group.
Required-concurrency qualification observes real overlap; serialization cannot pass it.

A group has named typed result slots, dependencies, a join rule and a finite shared budget.
Completion order does not grant visibility, change selection criteria, or identify a
winner. A first-verified policy is possible only when explicitly chosen; it deliberately
permits timing-dependent selection and must be tested and labeled as such.

## 5. Graphs, identities and visibility

Invocation ownership is a forest rooted in a run. Sequential live calls act like stacks;
parallel calls form an active frontier, not one global pop stack. Causal dependencies and
integration form a DAG. Native prefix sharing forms a different graph, owned by the
native service. A world scope binds physical resources. Do not keep synchronized copies
of one state under different tree names.

A child's visible input frontier is frozen before dispatch: allowed ancestors, explicitly
supplied artifacts and its own later events. Sibling events are invisible until a declared
join supplies selected values. Ledger append order is not causal permission. A model can
read only supplied content or a granted observation; an artifact hash is not access.

A returned child leaves the active frontier only after its terminal value/error, exact
return binding and resource settlement are recorded. It stays at its original historical
node. Source bytes may deduplicate; distinct invocations, grants and results must not.

## 6. PLAN and exact relevant state

Freeze the smallest sufficient state projection for the computation, not a mutable global
run revision. A plan binds:

- The operation/program/template/type identities, task/attempt and exact typed inputs.
- The selected causal frontier and all dependency versions actually read.
- For generation: service/store/model/tokenizer/build identities; native snapshot/revision
  and turn state; appended input bytes; grammar contract/epoch and committed progress;
  decoder profile/algorithm revision, feedback/RNG state lineage and stopping contract.
- For effects: execution profile; world/snapshot; preimages/read/write/resource sets;
  immutable executable/patch or tool definition; exact arguments/environment references;
  deadline, allowed outputs and reconciliation/idempotency contract.
- Protected acceptance inputs, output type, resource reservations and bounded costs.
- Policy/capability dependencies. A grant separately binds this plan hash and expiry.

The plan digest covers semantic inputs, not unspecified float/object serialization.
Use a canonical typed encoder with version/domain tags and explicit lengths. Exact bytes,
integers, decimals, text, optional absence, boolean and identifiers must round-trip without
coercion. TOML is configuration, not a lossy replacement for arbitrary runtime values.

At dispatch the interpreter checks the exact relevant versions, grant, leases and current
obligations. An unrelated sibling event must not invalidate the plan. A relevant change
must. A model's old statement about a file is not a fresh preimage observation. Check and
mutation need an enforceable atomic boundary, lock or resource-native compare-and-swap;
a prior check alone does not eliminate a time-of-check/time-of-use race.

Do not freeze unknown future state. A multi-step FLOW can be an immutable recipe, while
each dependent computation is frozen only when its predecessor's actual typed output and
postconditions exist. A composite frozen plan may name a pinned deterministic input
binding expression, but cannot pretend the still-unobserved value is already a concrete
state. This resolves obsolete-base failures without a special "ignore-staleness" flag.

## 7. Non-JSON language and typed data

The model-facing control language is `.bw`, with explicit operation lines, named references,
finite block syntax and literal text blocks. It does not require model JSON mode, JSON
Schema, a JSON tool-call feature, a JSON parser or JSON repair. No command extraction from
arbitrary prose. Code and free text are data, never recursively parsed as control syntax.

One canonical type/operation definition source supplies parser expectations, model-facing
shape descriptions and grammar generation. The grammar describes syntactic possibilities;
resolution/provenance/authorization remain host checks. No hand-maintained schema trilogy.

A control record nominates in-scope symbolic handles; the host resolves them to typed
values. A handle is neither a filesystem path nor a capability. No guessed return addresses,
new tool registrations or model-supplied authorization metadata are trusted. Scalars and
records retain types internally. Shape validation runs at admission, return and restore.

Text uses explicit literal blocks with line prefixes; a line containing ACT/COMMIT/END
inside the literal is just data. Full UTF-8 and empty content are supported. Text newline
normalization is explicit in the language contract; binary/source byte fidelity uses
immutable byte artifacts, never a lossy text round-trip. Model-authored source files are
retained as exact decoded bytes with any declared newline rule before being proposed as
an edit. Model output limits and nesting/field/reference limits are enforced independently
of grammar, including malformed/truncated stops and resource exhaustion.

Active configuration and handoff records use TOML/TSV/text; ledger payloads use a versioned
canonical typed codec with framed integrity checks. Native transport envelopes are owned
by the existing COW protocol and may have their own encoding. Do not rebuild that protocol
merely to remove a transport implementation detail. It remains opaque to model output.

## 8. State-dependent GBNF

For a generation invocation, build its grammar from the frozen output contract and the
host-eligible choices at the invocation's declared boundary. The grammar identity binds
compiled bytes, definition revision and source eligibility frontier. Never mutate it because
some other sibling finished. Recheck semantic eligibility after generation and at dispatch.

There are two distinct states: host workflow eligibility and native parser progress within
one output. The former changes at recorded host transitions; the latter advances when
that continuation accepts a token. Independent branches need independent matcher stacks,
partial-token/UTF-8 handling, root/epoch and end-of-generation state.

Apply hard grammar legality before probability-dependent sampling in BW's certified
profiles. Grammar, globally suppressed tokens and stopping rules form the hard legal set.
Soft sampling stages can remove or reweight within it; they can never resurrect a token
outside it. An empty legal set is a contract/decode failure, not a reason to disable grammar.
A singleton set has only one admissible next token. Syntax legality is not semantic truth,
a valid patch, permission or guaranteed eventual completion of a bounded generation.

A fresh result contract begins with a fresh matcher at a qualified output boundary.
A CONTINUE of an active partial preserves its matcher, even when the native request ends
mid-record. An exact fork of such a checkpoint clones progress if the backend qualifies it;
otherwise that fork is unavailable, not silently reset. A different contract requires an
explicit new generation lineage at a permitted boundary, not replacement of a live matcher.

Probe candidate tokens against temporary state. Token pieces may span multiple characters,
a newline plus part of another field, or partial UTF-8 sequences. Rejected probes must not
advance committed matcher state. Special tokens, prompt-prefilled output prefixes, reasoning
channels, EOS and stop strings require tokenizer-specific qualification. Do not guess channel
boundaries with a regex. No partial/provisional control output is eligible for execution.

A grammar that permits exactly one complete control record needs no model to choose it:
the interpreter can derive the record directly if the operation definition is deterministic.
Record that as a local computation, not invented inference. A one-token legal set during a
larger generation still obeys the native decode/accounting contract; do not assume it costs
no forward pass or allows arbitrary skipping of model state updates.

## 9. Decoder profiles and branch-local state

BW selects a pinned decoder profile for a generation computation, not an unlogged collection
of global sliders. Samplers are implemented once at the native decoding boundary. BW owns
profile requests and receipts, not a second Python token-generation loop.

The requested family consists of greedy, DRY, Min-P, fixed temperature, Locally Typical,
DynaTemp, XTC, Mirostat 2 and Adaptive-P. Top-K/Top-P remain disabled in the minimal Min-P
baseline unless a separately named benchmark profile requests them. DRY's sequence history,
window and sequence-breaker policy are part of the exact profile/state, not generic stop
strings. Do not randomly suppress repetitive protocol scaffolding with a prose profile.

A profile has an ordered list of transforms/filters and exactly one terminal selector:
greedy, ordinary random distribution, Mirostat 2, or Adaptive-P. Static and dynamic temperature
are alternative temperature stages. Mirostat 2 and Adaptive-P do not stack with one another
or with another final selector. A pipeline whose order differs has a different identity.

Core intended profiles are grammar-first constrained greedy for control and grammar-first
DRY + temperature + Min-P + distribution selection for open content. Experimental profiles
substitute Typical, DynaTemp, XTC or a feedback selector under explicit contracts. See the
supporting profile document for precise order and qualification limits. An upstream default
order is not an implicit BW requirement. A DRY + Mirostat composition must be explicitly
qualified rather than presumed to be supported by a backend's normal Mirostat mode.

Min-P filters relative to the maximum at its input distribution. Typical orders candidates
by distance of surprisal from entropy and can remove the modal token. Positive temperature
alone preserves argmax; Typical/XTC/DRY need not. DynaTemp responds to distribution entropy,
not actual correctness confidence. XTC diversifies token choices, not verified ideas.
Mirostat/Adaptive-P targets need not be attainable under severe grammar constraints.

Every mutable decoder component is continuation-local: RNG algorithm/state/draw position,
DRY history, grammar progress, Mirostat control state, Adaptive-P feedback, stop state and
any draft/pending selection state. Configuration can be shared immutably. A clone with the
same RNG state is independent but may produce identical samples; independence is not diversity.

Use two explicit fork semantics: exact clone for replay, or an exploration fork with a
recorded stable child/component seed derivation and/or new profile. Seed derivation must
not depend on launch order, wall time or completion order. Changed profile means changed
future decoding law and a new plan identity, not an exact replay promise.

The conceptual decode step proposes `(token, next_decode_state, trace)` from a snapshot.
Commit that proposed state once for an actually accepted token. Candidate probes, rejected
draft tokens, duplicate receipts and UI previews cannot update committed state. Native
libraries that mutate RNG/feedback in `apply` need transactional staging/checkpoint support;
a no-op `accept` is not proof that they are stateless. Token IDs alone need not reconstruct
a feedback algorithm that used historical probabilities. Preserve exact native serialized
state or sufficient certified trace; otherwise report exact recovery unavailable.

## 10. Native contexts, receipts and recovery

Use the existing native COW operations and source-pinned wire semantics. namespace/load/
prepare establish context; ask/answer/append-user generate at stopped boundaries; continue
resumes active turns; fork/rewind navigate qualified snapshots. Status/history/operation and
original-request recovery retain their native meanings. No invented endpoint names, silent
stateless replay or reinitialization fallback.

Before any native mutation, durably record exact request bytes, operation ID, original
expected revision, owner/service identity, input/control bindings and budget. A branch has
at most one unresolved mutating operation under BW control. A different branch can progress
subject to shared service capacity. Services with the same URL after a restart must still
prove the intended store/model/tokenizer identity.

Streaming is provisional until a checked native receipt. A receipt can durably publish a
partial answer while leaving the model turn active. That is not a complete BW typed return.
CONTINUE retains the exact output contract and numerical/parser/sampler progress. A stopped
malformed output is rejected; a budget-limited active output is explicit incomplete work.
Neither authorizes an effect or creates a hidden repair attempt.

A lost acknowledgment is reconciled using the original operation ID/bytes/revision. Unknown
process-local status does not prove non-commitment. Native receipt recovery, checkpoint
availability and unfinished-inference recovery are distinct. Retained text alone is not
proof of exact numerical restore. Explicit reconstruction, where authorized, is a new lineage
and charges actual processing; it is never labeled restored old state.

Native state serialization must be versioned and bound to model/tokenizer/build/profile.
A seed without draw position and feedback is insufficient. Test request splitting, committed
partial continuation, in-memory clone, eviction and process restart separately. Bitwise
repeatability across devices/builds is not presumed; qualify exact reproducibility or a
specified numerical/distributional equivalence independently of semantic correctness.

Speculative/MTP decoding remains outside the first certified profile unless the installed
backend already qualifies it. Preserve existing MTP and non-MTP worktrees. Do not claim that
matching a draft token to an independently sampled target token proves distribution-correct
speculative sampling. Rejected drafts must not alter grammar/RNG/feedback; certify target
probability law, accepted-prefix state and EOS behavior before enabling the combination.

## 11. Worlds and concurrent effects

A world scope names an enforced execution boundary: source snapshot/worktree, read/write
capabilities, private scratch/temp/cache/home, environment/credential exposure, process tree,
network/IPC/device resources, resource leases and ownership. A scope is not a whole-machine
snapshot. Worktrees alone do not isolate arbitrary code, shared Git administration or sockets.

Candidate processes cannot rewrite the ledger, protected artifacts/tests/policy, sibling
workspaces or broker-owned Git metadata. Links, concurrent path replacement, inherited handles,
child processes and network must be handled at the actual enforcement boundary. Unsupported
required containment blocks dispatch. Shared writable resources need exclusive leases or a
qualified transactional boundary. Read-only sharing is allowed by capability, not assumption.

Two ACT plans are eligible together only when their dependencies are resolved, grants valid,
relevant preconditions fresh, world boundaries enforced, read/write/resource effects compatible,
and combined capacity fits the run/service budgets. A resource R/W conflict is different from
two worktrees editing the same relative filename. The latter is a later integration concern.

The scheduler can select any eligible antichain consistent with the pinned policy. Resource
claims and intent are recorded before dispatch, and an owned reservation remains held until
outcome/termination is known. A discovered unused port that was released is not a lease.
Workers do not acquire interpreter authority or update other branches' plans/results.

An ACT plan cannot be silently reinterpreted as COMMIT. Test code with side effects runs through
ACT; OBSERVE reads its receipts and VERIFY evaluates them. Planning computations with scratch
work use a scope that actually enforces the promised read-only source and bounded scratch effects.

## 12. Evidence, comparison, composition and publication

VERIFY returns pass/fail/unknown/inapplicable only under its pinned contract and evidence
provenance. Coverage, missing evidence and verifier limits remain visible. A model critic
can produce a Challenge or Assessment value; shape does not turn it into an observed test.
Claims cannot write authoritative task status.

Acceptance binds exact candidate bytes/commit, protected verifier inputs, execution environment
and tool versions. Relevant mutation invalidates current eligibility without editing old evidence.
Reuse a result only if the verifier's full dependency closure is unchanged and its replay/cache
contract permits reuse. Timing, nondeterministic or externally dependent checks need their own
freshness rules; identical source hashes alone are not universal proof of reusable evidence.

COMPARE uses comparable contracts/budgets and retains known failures/unknowns, not just survivors.
SELECT chooses explicit typed references. Alternative implementations are selected, not merged
because both individually passed. Complementary required branches may be composed in a declared
order into a fresh integration workspace. COMPOSE creates a new artifact/state identity and must
be followed by the relevant integration verification. It never combines two matcher/RNG/KV states.

A join is a local causal/typed-return operation, not automatic publication. Some task contracts
require COMMIT before successful group return; others require only a verified selected artifact.
The output type and join rule declare that difference rather than making every planning join publish.

COMMIT publishes through an exact target identity with expected-old guard and valid grant.
For Git, use an owned non-checked-out test/publish reference or an explicitly qualified exclusive
ownership boundary. Updating an unrelated live checkout is a separate effect. A lost acknowledgment
is reconciled from actual reference/receipt state. A changed target blocks stale publication.
No universal atomic transaction across files, databases and remote services is claimed.

## 13. Durable typed frames and returns

A frame retains run/task/attempt/parent IDs, immutable program position, inputs/locals, loop
iteration, continuation epoch, wait-set slots, expected child/type, output obligations, resources,
model/world references and exact native/effect operation identities.

Control states are Ready, Waiting, Settling and Closed, derived from ledger events. Task acceptance,
model-turn activity, published code and scope closure are orthogonal facts. Waiting includes named
unresolved effects; it is not a synonym for failure. Closed requires settled/transferred obligations.

Register child admission and parent wait ownership in one logical durable transition. Retain result
artifacts before recording return/slot delivery. A slot binds the expected child, attempt, epoch,
type and result digest. An identical delivery is idempotent; a conflicting/wrong-slot/wrong-epoch
result cannot overwrite it. Legitimate out-of-order sibling returns do not fail because an unrelated
parent projection revision advanced. Once a join predicate is satisfied, record parent resumption
before dispatching the next effect. Do not serialize closures or trust a saved Python call stack.

Type, provenance, commitment and authority remain separate. Missing, explicit absence, bool/int,
text/bytes, precise number types, typed references, empty values and union variants must survive
restore. An active stream is not a returned value. A terminal error can return to a declared ON
handler, but an unknown external effect retains its obligation until reconciled or transferred.

## 14. Local records and retention

Keep one private append-only single-writer ledger plus immutable artifact store. An illustrative
layout is `run.toml`, `events.bwl`, `artifacts/sha256/`, owned workspaces and scratch. The production
codec is a versioned framed typed encoding, not pickle, eval or model-readable JSON. Its exact bytes
must be specified and tested before claiming interoperability. Hashes detect corruption, not an
attacker replacing the entire trusted control store.

Publish and verify an immutable artifact before a durable ledger reference. Persist dispatch intent
before external send. Distinguish torn trailing frame, corrupt committed record, missing artifact
and harmless unreferenced residue. Do not truncate accepted history to make recovery succeed.
Qualified storage profiles define fsync/rename/locking behavior. Process restart and power-loss
recovery are separate claims and need separate tests on intended platforms.

SAVE pins a name to an immutable result plus scope/retention policy; it does not create durability
for the first time. Aliases are revisioned, do not overwrite the old value, and never change producer
provenance. Garbage collection follows ledger/artifact/active continuation/resource roots and cannot
remove evidence needed by unresolved effects. Numerical KV eviction is a native cache capability,
not permission to discard logical history or promise all old checkpoints remain executable.

## 15. Budgets and test-time compute policy

The scheduler accounts for actual and reserved model input processing, output tokens, sampler
cost, requests, tool runtime, concurrent slots, memory/context pressure, retained storage and
failed/abandoned work. One service's shared capacity is counted once, even with two role labels.
Fan-out does not multiply a parent's remaining budget. Unknown live work keeps its reservation.
No default numbers are inferred from a GPU brand; bind limits from actual allocation and profiling.

Start with bounded best-of-N and evidence-based selection. Deterministic fallback ordering/ties
are part of the policy. Add progressive widening/early pruning only against declared cheap tests
and an explicit objective. Do not implement a research bandit/search framework before measuring
the simple baseline. Novel wording is not independent evidence, and a model's confidence is not
an automatic value-of-compute estimator.

Reuse immutable prefixes when native evidence demonstrates actual sharing. Count logical prefix
length separately from physical evaluated tokens, cache hits, bytes copied and wall time. Different
profiles/seeds may share a prefix but not decoder progress. Different prompts often dominate diversity
more than raw stochastic branching; compare both under the same task and compute budget.

Cross-branch computation deduplication is permitted only for identical pure deterministic inputs,
definition, law and scope. Distinct invocations/evidence ownership remain. Do not deduplicate side
effects or stochastic attempts merely because their visible text matches. Replaying an exact fork
for parity is an intentional test, not a promised exploration gain.

## 16. User-facing features and roles

Cartographer and Builder remain logical roles, deployable on one or two qualified COW services.
Each role has declared inputs and native branch ownership; role names do not imply permissions,
model size or additional service capacity. The local world host is not automatically the inference
host. Cross-service context initialization is explicit and charges real input processing.

Headline, factual status, status narration, summary, design, builder decisions, generated analysis,
final response and human questions use the same typed invocation/return discipline. Factual status
is a pure ledger projection and cannot be rewritten by generated narration. Auxiliary generation
uses an independent selected input scope and cannot pollute the Builder's native context.

Templates are local immutable definitions pinned per invocation, with one-pass substitution of
declared fields. Data cannot recursively expand template syntax. A template update affects new
admissions only. Source-bound annotations arriving after a user edit or newer task revision remain
history, not the current display value. Summary sources/omissions/unresolved IDs remain explicit;
condensation cannot replace runtime waits, grants or resource obligations.

Only genuinely exposed native reasoning/channels are called native reasoning. A prompted analysis
is labeled generated analysis. Unsupported channels/controls are reported; there is no fabricated
hidden reasoning. Human approval/steering is returned to the exact live wait epoch and injected only
at an admitted safe model boundary. Render/inspect commands never initiate hidden inference.

## 17. Failure, abandonment and rewind

Failures, rejection, invalid output, cancellation, budget exhaustion and unresolved outcomes are
explicit dispositions. ABANDON requests non-adoption and cleanup. It does not undo file writes,
terminate unknown remote processes by assertion, erase reservations or close unsettled scopes.
Compensation is a separately planned and authorized effect with new evidence.

Native rewind changes model position only. A new attempt chooses historical causal inputs without
rewriting the ledger. Restoring code is an authorized physical effect. Neither rewinds external
services, network transactions, sockets or devices. Fork/rewind of a branch with an unresolved
mutation is blocked. Truthful current physical observations must accompany any historical context.

Budget exhaustion may leave a partial native turn or live external work. Preserve and report both.
Known ended work can close; unknown work remains Waiting/Settling or transfers through a recorded
authorized ownership handoff. A failure report itself is not evidence of resource termination.

## 18. Implementation boundaries

Prefer a small local application with responsibility boundaries for typed definitions/language,
interpreter/reducer, records, native COW, execution/workspaces, policy/verification and CLI. Use the
actual repository structure where sound. Do not add a second adapter-side workflow loop, global
sampler singleton, independent transcript database, optional legacy JSON path or forced daemon.

Native decoder-state contracts are established before sophisticated sampling. Language/grammar,
native snapshots, and world/recovery work can then proceed in parallel against frozen shared types.
DynaTemp and Typical share probability utilities but do not require one another. XTC needs tested
RNG/filter composition. Mirostat 2 and Adaptive-P share transaction/checkpoint infrastructure; neither
requires the other's algorithm. Unavailable experimental samplers do not block a qualified baseline.

## 19. First complete milestone

Run one real nested coding session through the product: observe/pin the project; expand a design;
freeze an exact tool computation; execute an owned child; return its observed result to the exact
Builder continuation; propose/edit/verify an actual fix; publish only if the task contract requires;
produce isolated headline/status/summary/final outputs with proper provenance.

Interrupt after a child result is durable and its return recorded but before parent resumption.
Reopen, reconstruct the typed locals/wait/epoch and resume once without repeating the tool or
regenerating the child. Repeat at a committed active partial model boundary and verify decode-state
continuation. These are separate recovery tests, both required.

Next run two model expansions from one immutable base, deliberately reverse/interleave completion,
then run eligible branch-local ACT plans with witnessed overlap. Include wrong-slot/late result,
branch grammar divergence, explicit seed splits, shared-resource contention, composition conflict,
fresh integration verification, target CAS conflict and unresolved-effect abandonment.

## 20. Qualification and evidence

The catalogue is a minimum. Every product PASS binds exact test ID, source/spec revision, model/
service/build/profile/tokenizer where applicable, environment, original commands and retained raw
witnesses. Reference arithmetic, a mock server or a permission decision is not a native/GPU/OS PASS.
All inherited behavioral obligations are preserved with explicit language/encoding migration.

Certify syntax, semantic admission, branch state, numerical law, replay, concurrency, resource
isolation, recovery, model quality and performance separately. Statistical tests use stated tasks,
seeds, tolerances and uncertainty, not one lucky sequence. Never require unattainable entropy/
probability targets as a correctness oracle under deterministic/grammar-forced distributions.

## 21. Final invariant

At every transition there is one truthful relationship between the exact computation proposed,
its native/context and world dependencies, its authority, its actual effects, its retained evidence,
and its typed continuation. Independent branches cannot change one another's mutable state.
A result may be selected or rejected; its history remains. No syntax, sampler, branch, cache or
convenience interface is allowed to bypass that relationship.
