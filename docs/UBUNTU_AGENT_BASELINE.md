# Ubuntu Agent Baseline: real terminal integration

The previous Basic Agent Loop H00-H12 have bounded autonomous Q4 passes.
The next catalogue is separate. L00 is NOT_RUN with the model.

## First boundary: actual sandboxed commands

The new read-only terminal primitive consumes a host-fixed argv and snapshots
only granted readable files. A private Linux PID/mount/network namespace runs
the actual system program with separate stdout/stderr and its real exit status.
The projection is read-only;host home,secrets,GPU and ungranted workspace files
are absent. Terminal temporary writes stay inside its bounded tmpfs. Actual
namespace retirement is required before publishing output. Unknown retirement
or failed publication cannot become a safe automatic retry.

34 focused checks pass:14 terminal,7 existing execution and13 file-tool checks.
The first stream probe failed before implementation. A real Ubuntu26 coreutils
alias exposed executable admission that was too narrow. Root-owned,non-writable
system targets under /usr are now accepted,while only system-bin spellings are
admitted. A malformed command catalogue originally created a workspace before
rejection;new admission now runs before creation. Earlier failures are retained.

This is the executor foundation,not yet the general model terminal action.
Next:let the model supply a bounded shell command under an explicit host grant,
reuse this same isolation/capture/publication implementation,and bind exact
command bytes in existing PLAN/ACT/RuntimeLog. Then test registry/CLI delivery,
missing/stale receipts and offline reopen before actual Q4 L00. No second
workflow engine or transcript. Writable commands and user-manager operations
need their separate explicit scopes and tests. Preserve original protected
catalogue assertions;one selected target at a time.

## Thinking and failed-task recovery

New thinking admissions default to4096 tokens. The COW thinking matcher may
close naturally earlier and forces the legal closing delimiter at its cap.
The cap belongs to the immutable grammar definition;do not mutate an admitted
controller to change it. Larger budgets alone do not guarantee better reasoning.

After a verified task failure,retain the attempt and feed a new planning attempt
its goal,observed failure and current evidence. Ask it to think carefully,
separate givens from assumptions,identify the contradicted assumption,and choose
a different approach. This is task-level prompt/workflow recovery,not per-token
sampler manipulation. The newer owner instruction advances the ladder on a verified task failure;
natural closure and budget exhaustion are recorded separately. Never rerun an uncertain external effect;reconcile its original
operation first. Capture genuine generalizable model failures for reviewed LoRA
candidates,without protected answers. No model failure exists in L00 yet.
