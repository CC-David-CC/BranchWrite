# Illustrative programs, not installed product commands

These scripts demonstrate v0.6 syntax and operation boundaries. The offline parser checks
syntax; real type resolution, world setup, host grants, native controls and execution must
be implemented and qualified. Values such as `source-base`, `readonly-a`, `proposals.a`,
`selected-world`, `protected-tests` and `owned-test-ref` are symbolic references that the
host must bind, not invented API endpoints or executable shell strings.

The registry/host join contract exports named branch results into group results. Dotted
references such as `proposals.a` denote named typed slots, not completion-order indexes.
The branch-to-slot binding is frozen by the host definition before dispatch; model output
cannot choose real return destinations.

The first example deliberately gives child B an XTC profile. It is unavailable until XTC
is qualified; use a separately authored run with two available explore profiles and distinct
seed/task bindings to test baseline branching. The runtime must never silently substitute.

VERIFY backed by a process/test program admits planned ACT children and observes results
through the same interpreter; the compact syntax does not make tests a pure read. COMMIT
requires both original acceptance and any contract-required challenge evidence. The local
adoption checker assembles those references; no single model claim can replace them.

In the composition example COMPOSE produces an integration proposal. A pure composition
implementation could instead directly return a derived artifact; its operation definition
makes that distinction explicit. Source edits still require the normal planned effect.
