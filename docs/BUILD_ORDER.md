# Dependency-driven build order

The authoritative ticket DAG is `acceptance/tickets.toml`. Gate labels group evidence;
they do not force unrelated work to wait for every test in a lower-numbered category.
A primary case owner is accountable for its oracle; integration tickets also run their
dependencies and applicable regressions, even when they own no new primary case IDs.

## Shared foundation first

R01/R04 establish actual repository/native facts. R02/R03/R05 freeze canonical types,
non-JSON syntax, ledger and durable typed frames. R08 establishes relevant-state freezing.
No one should invent a private variant of the frame, plan, profile or capability record.

After those interfaces are pinned, three workstreams can proceed in parallel: language /
GBNF derivation (R06), native decoder-state lifecycle (R07), and worlds/effect boundaries
(R09). Integration remains through one interpreter rather than three separately running
agent frameworks.

## First useful vertical slice

R10/R11 qualify constrained greedy plus the reported DRY/Min-P baseline. R12/R13 add real
typed tool returns and ordinary tracked headline/status/summary/final generation. R35
preserves the fixture's input values, object-identity invariants and distinguishing mutants
while moving its handoff metadata to TOML. R14 delivers the real nested session and crash
after child return. Do not postpone all native work until the reference code looks complete.

## Native state before exotic sampling

R15/R16 certify independent matcher progress, exact/exploration forks and transactional
RNG/feedback lifecycle. Then DynaTemp (R17) and Typical (R18) can proceed concurrently.
XTC (R19), Mirostat 2 (R20) and Adaptive-P (R21) are independent algorithm implementations
once the shared lifecycle exists; none mathematically builds on another. A smaller team
may do XTC and Mirostat first and Adaptive-P next for convenience, not as a dependency.

Use separate workers for modules/tests, not independent default profile policies. One
maintainer integrates the fixed chain contracts and state/evidence semantics. All workers
must preserve the existing native baseline and repository test expectations.

## Branching and results

R22 builds independent parallel expansions; R23 proves actual isolated ACT overlap. R24
makes challenge/comparison/selection evidence-bound. R25 composes complementary results
and verifies the fresh integration state. R26 handles guarded publication. R28 budgets and
reservations precede parallel dispatch. R29 keeps views and step/run on the same kernel.

R27/R31 qualify faults, native restart and intended OS/service configurations. R30 measures
fair compute use. R32 is baseline product evidence, not a claim all advanced controls work.
R33/R36/R37 certify enabled advanced profile combinations and numerical/performance claims.
R38/R39 retain adversarial and all inherited regressions. R40 issues an exact enabled-
capability report. R34's constrained MTP scope is conditional and never silently enabled.

## Per-ticket completion

Read source, add the failing discriminator, implement the smallest coherent change, run
regressions and the real boundary test, retain exact commands/source/profile/evidence,
and update observed case outcomes. Missing capability remains not_run/blocked as appropriate;
never mark it PASS because a mock, reference oracle or neighboring sampler passed.
