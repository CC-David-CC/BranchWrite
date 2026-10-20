# Rejected edits and uncertain writes

A model can ask to replace text that does not occur in a file. That is a bad
proposal, not an uncertain write. The host checks the exact preimage and output
size while planning, sends a rejection back through the ordinary tool-feedback
path, and lets the worker propose a new action. A previous successful read stays
visible after this rejection.

The Executor owns the single pure replacement calculation. ToolRegistry uses
that calculation under the owned workspace lock during PLAN and again during
ACT validation. The actual Executor write repeats it against current bytes.
Existing digest, grant, private-file, byte-limit and unique-preimage rules remain.
No alternate edit representation or relaxed matching is introduced.

Once external execution begins, an exception can follow an actual durable write.
That still raises EffectIndeterminate and retains the original operation for
explicit reconciliation. This change does not catch post-write ToolRejected,
automatically retry pending effects, or reopen the old uncertain run with a new
implementation identity.

The real autonomous H04 attempt exposed this distinction after an incorrect
model edit and a nonmatching repair. Its failure is retained. Eight new tests
first produced three failures and two errors; all eight then passed. The affected
176-test client/browser/CLI suite passed without skips. See
validation/REPLACE-ADMISSION-2026-10-18.json for exact IDs and scope. The real H04
retry is separate; a passing host regression is not a task or numerical pass.

## Real retry outcome

The exact observed bad repair now rejects before execution in a separate owned
workspace. The autonomous GPU retry nevertheless timed out after three wrong
copied file digests; H04 has not passed. This is a separate model/tool-use and
latency issue. A missing acknowledgment left an original intent pending; the
server retained its committed checkpoint receipt. No uncertain generation was
resent. See validation/AUTONOMOUS-H04-Q4-2026-10-18.json.
