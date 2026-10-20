# Prepared-prefix admission

SC09 v1 failed before any model work: the existing CLI used append_user on the
idle system-context root. The server correctly requires ask for that state.
This is a client operation-selection gap, not cache corruption or a model failure.

Dev4 adds --from-prefix BRANCH, mutually exclusive with --from-branch. It reuses
the existing canonical fork and ask APIs. The default snapshot is the source
root; an explicit snapshot remains pinned. --from-branch retains completed-tip
append_user semantics. No controller status is forged or reset. The server still
requires a renderer-matched idle context-only root and rejects other states.
No backend code, execution profile, serializer or numerical tolerance changed.

Five new unit tests pass after three initially errored. They cover distinct modes,
saved setup, mutually exclusive source forms and stable source pinning on retry.
A real CLI/HTTP/Store test using CPU arithmetic is written but not yet executed.
Real Q8 prefix restore with zero forward work and the SC09 feature trial remain
pending. Original failed operations and state must remain untouched; use explicit
new work/state for the corrected trial.

The actual HTTP test now passes through the existing registered-grammar path.
Its CPU backend deliberately does not implement unconstrained native resident
generation; the diagnostic from the incomplete fixture is retained. The
first broad run caught the existing no-guessed-boundary guard. That assertion
was preserved unchanged. Only a sealed prepared-prefix launch supplies validation
context for inline ask registration; undeclared raw configs remain rejected.
Corrected158/158pass,0skips. Installed dev4 controls pass. No corrected GPU run yet.
