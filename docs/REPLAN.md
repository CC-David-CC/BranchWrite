Owner policy update2026-10-17: explicit JSON/JSON Schema model output is now supported
beside GBNF. Canonical workflow/ledger representations remain typed .bw/BWT records.
The historical blanket JSON bans below are superseded; they are not implementation
instructions. The reference oracle and mathematical specification remain unchanged.

# BranchWrite v0.3.0: the replan

## The central decision

Build one durable interpreter for typed, state-bound computations. Do not build one
agent loop per verb, one execution engine per parallel mode, or a second sampling engine
in Python. The interpreter freezes, admits, dispatches, records and returns computations;
the native service performs token generation. Grammar, evidence and permissions have
separate responsibilities.

This document is an overview. The normative proposed contract is
`../spec/BW_FIRST_PRINCIPLES_v0.6.md`; the examples are proposed syntax, not an already
implemented BranchWrite command interface.

## Intent becomes a small instruction language

The executable vocabulary is:

```
EXPAND CONTINUE PLAN ACT OBSERVE TRANSFORM SAVE
VERIFY CHALLENGE COMPARE SELECT COMPOSE COMMIT ABANDON
```

ASK, DO, LOOK, CHECK and STOP describe intent but are not a second supported instruction
set. PLAN freezes; SAVE retains; successful completion returns a typed value from a settled
invocation. ABANDON terminates an unsuccessful or unadopted attempt without pretending to
undo external effects. COMPOSE is a real operation, because selecting an existing winner
and constructing a new integration result are different computations.

FLOW, REPEAT, BRANCH, PARALLEL.PLAN, PARALLEL.DO and ON express structure around the same
computation mechanism. A parallel group changes eligibility and scheduling, not the meaning
of ACT or EXPAND.

## No model JSON dependency

Model-facing programs and control decisions use strict `.bw` text. A control result can be:

```text
ACT execute-a plan=plan-a -> outcome-a
```

Host state derives its allowed grammar. Names resolve to typed in-scope values, registered
operations and trusted return slots. They are not shell commands or capabilities. A complete
record is parsed and admitted before execution; partial streaming text has no authority.

TEXT blocks prefix literal data lines with `|`; control-looking text inside them stays data.
Arbitrary exact bytes stay artifacts. Canonical typed records preserve booleans, integers,
decimals, strings, bytes and absence without converting between incompatible representations.
TOML/TSV serve configuration and catalogue export, not arbitrary runtime-state serialization.
There is no JSON mode, schema, tool envelope or repair-to-JSON path in the active BW contract.

The original source archive still contains historical JSON material. A native service's
pre-existing internal wire format remains its own contract. This plan removes BW's JSON
support requirement without inventing a replacement native COW protocol.

## Freeze relevant exact state, not the whole run

PLAN binds the operation, inputs, output contract, causal input frontier, native decoder
snapshot or world preimages, resources, policy dependencies and budget. Grants bind the plan
separately. The interpreter rechecks freshness, permission and leases at actual dispatch.

A global revision would make every event in branch A stale branch B, destroying independent
parallelism. The dependency projection must instead contain every relevant dependency and
no irrelevant scheduling noise. An actual dependency change stales the plan; an unrelated
sibling event does not. Locks or native compare-and-swap enforce the check/mutation boundary.

A FLOW is an immutable recipe. Its later computations freeze after actual preceding outputs
exist. Do not freeze guessed future filesystem revisions, invented observations or predicted
test success. Direct EXPAND and explicit PLAN use the same admission function; PLAN merely
makes a frozen computation retainable for deferred dispatch.

## Independent siblings in both planning and doing

PARALLEL.PLAN forks qualified native continuations from an immutable shared base. Each child
owns future context, grammar matcher progress, RNG counters, DRY history, adaptive feedback
and stop/provisional-token state. An exact clone supports replay, not guaranteed diversity.
Exploration uses explicit, stable child seed derivation and/or different task/profile inputs;
launch and completion order never define the seed.

PARALLEL.DO dispatches eligible ACTs into independently enforced world scopes. Distinct
names, directories or worktrees do not alone establish isolation. Physical resource claims,
leases, authority and capacity decide which computations can overlap. Required concurrency
is proven with actual overlap witnesses; merely returning two outputs cannot pass that test.

Named return slots, not arrival order, bind children back to the parent. Sibling results
become visible only at declared joins. Parent ownership, epochs, input types and outstanding
resource settlement are checked before a return can resume its exact continuation.

## Grammar first, then a pinned decoding profile

There are two kinds of grammar state: the host-authorized output contract and the native
matcher position inside one output. Share the former immutably where valid; never share the
latter mutably. A new output contract starts at a qualified boundary. CONTINUE and an exact
partial-output fork preserve existing progress.

The proposed certified profile order starts with hard legality. All later filters or score
transforms operate within that set. They cannot resurrect illegal tokens. An empty legal set
is an explicit failure, not permission to drop constraints. A grammar with one complete
host-derivable control record does not need model deliberation; this does not imply that
forced tokens within an ongoing native generation cost no computation.

Use constrained greedy for control records and exact references. Use DRY + temperature +
Min-P + ordinary random selection as the initial content profile. Add Typical, DynaTemp and
XTC as named experiments; Mirostat 2 and Adaptive-P are alternate final selectors. Exactly
one final selector is permitted. Pipeline order, parameters, model/tokenizer/build and RNG
lineage belong to profile/state identity.

Do not require Adaptive-P to wait for the Mirostat algorithm. Both need shared snapshot,
clone/reset, transactional feedback and receipt semantics; neither needs the other's math.
The numerical tests in this bundle are synthetic reference checks, not native sampler parity.

## Evidence and publication

VERIFY applies protected acceptance criteria. CHALLENGE proposes counterexamples or probes;
any real probe execution still needs normal admission and ACT. COMPARE evaluates known
results under pinned criteria. SELECT chooses eligible references. COMPOSE creates new
bytes or structure from explicitly chosen inputs and records their provenance. New integration
output needs fresh verification; component passes do not automatically transfer.

COMMIT publishes through an explicitly granted, guarded boundary. It rechecks target and
source identities and requires evidence for the actual adopted artifact. SAVE controls
retention rather than serving as the first durable recording of actions. Failed branches
remain historical evidence even after leaving the active execution frontier.

## Build around one real vertical slice

First establish actual repository/native facts and canonical types, ledger, frames and
relevant-state plans. Language/GBNF derivation, native lifecycle and physical-world boundaries
can then proceed on separate bounded implementation branches against those fixed contracts.

Qualify grammar-first greedy and the user-reported Min-P/DRY baseline. Port the original
fixture metadata without changing its test values or distinguishing mutants. Complete a real
nested model/tool session, including restart after the child's durable typed return but before
the parent's consumption of that return. Prove it resumes the exact slot without rerunning
the tool or losing history.

Then certify native partial-output forks, isolated concurrent effects and shared budgets.
The five additional sampler algorithms can proceed independently after native lifecycle
contracts stabilize. Qualify each profile before using it; do not silently replace an absent
sampler. Advanced sampling need not prevent release of an explicitly limited working baseline.

## Evidence delivered, not simulated product completion

The handoff retains all 211 prior product obligations, adds 128 new cases and assigns them
to 40 dependency-bound tickets. All 339 product cases remain not_run. The source archive is
retained unchanged, and its 98 original offline tests passed in this preparation session.
The new suite contains 237 passing offline reference/catalogue tests. See the validation
report for commands and limits. No native service, GPU, actual OS sandbox, production
concurrency or full model run was exercised here.
