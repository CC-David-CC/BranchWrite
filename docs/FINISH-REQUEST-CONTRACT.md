# Experimental finish-request wording

The fixed-weight compact-feedback probe repaired the final shell artifact but
still repeated named checks without requesting finish. The actual root system
instruction said: “Request finish only after the current host completion policy
is satisfied.” The selected-check policy cannot return final success until the
model explicitly requests finish. Ordinary pre-finish feedback therefore kept
reporting an overall failure even after a zero-status named check. This is a
circular instruction risk, not a demonstrated causal explanation.

An owner can select `instruction_style="compact-finish-request"` in
`build_launch`, or `--instructions compact-finish-request` for a new coding root.
This changes one sentence in the compact system prefix to:

> Once the host's required evidence and checks are ready, request finish so the host can evaluate completion; final verification happens after that request.

The existing `compact` and worked-example styles are unchanged. Retained roots
remain immutable. Both styles keep exactly the same tool schema, grammar,
readiness option, grants and verifier. The host still rejects missing, failed
or stale checks and requires explicit finish; this wording never finishes a
task automatically or certifies model-selected checks as independent truth.

The successful Hermes and DeepSeek controls on the same original model ended
with ordinary final answers after real tool output. Neither exposed BW's named-
check/finish protocol. Their positive and negative probes printed statuses
rather than asserting them, so their success does not justify weakening BW's
verification. Their runtime, prompts and tool APIs also differ; this comparison
motivates a test rather than establishing the cause.

Earlier broad guidance and check-readiness probes did not improve completion.
They changed continuation guidance or readiness projection, leaving the root
system sentence intact. A new comparison must isolate this wording on the same
new BW source, with fixed weights and compact feedback in both conditions.
Use fresh balanced task variants, independent host checks and separate saved-
artifact versus workflow-completion outcomes. No live behavioral improvement is
established for this option yet.

CPU protocol checks exercise actual CLI/HTTP bootstrap and real host execution:
a premature finish is rejected, a passing named check alone remains unfinished,
and a later explicit finish passes. These are scripted mechanics, not model
competence measurements. The private proposed qualification has eight fresh
near-transfer/regression variants, sixteen bounded workflows and no training.

## Actual fresh probe: abandoned without promotion

The planned sixteen-workflow probe stopped early. It produced **two independently
graded failures, one timeout that was deliberately not graded, and thirteen
unrun workflows**. It is not a sixteen-task score.

| Attempt | Saved artifact | Workflow outcome | Model requests |
| --- | --- | --- | ---: |
| First fresh objective, legacy compact wording | Failed independent checks | Step budget exhausted; no finish | 13 |
| Same objective, finish-request wording | Failed independent checks | Step budget exhausted; no finish | 13 |
| Second fresh objective, finish-request wording | Not graded | Task guard expired during an unfinished action | 10 issued; 9 complete |

The complete pair made no edits or named checks. Neither reached the condition
this hypothesis targets: a correct saved artifact and current passing checks
followed by repeated checking instead of finish. The wording did not help the
first objective, but this incomplete probe neither isolates nor disproves a
finalization effect. The option remains experimental; defaults are unchanged.

In the timeout, one proposed shell action remained incomplete across six
512-token chunks, followed by a cancelled continuation. The command never
became an admitted shell invocation. The original coordinator reported
`cancelled`, `durable=false`, with `coordinator-process` scope. The pre-grade
guard stopped the schedule before capturing or grading that workspace. The
original pending journal remains preserved as abandoned and nonresumable; it
was not rewritten as complete, replayed or continued.

Only completed request receipts contribute the recorded 3,144 output tokens,
including 3,072 within the unfinished action. Output and time consumed inside
the cancelled request are unknown. These are incomplete observations, not a
full timeout-cost or speed measurement. All source/native/weight checks passed
afterward. The owned service was stopped and its GPU lease released.

[Redacted aggregate and provenance](../validation/minicpm-finish-request-20261025-bi/results.json)
record the exact counts, unrun list, bounds, source/protocol/model/oracle/guard
hashes and cancellation scope. Raw prompts, solutions, generated text and
owner-local operational details remain private. No model weights changed.

## Selecting the experimental option

For a **new** coding root, select
`build_launch(..., instruction_style="compact-finish-request")`, or pass
`--instructions compact-finish-request` to the existing coding CLI. Omit that
choice to preserve existing defaults. Saved roots cannot change their prefix
on resume. The same-source control uses `instruction_style="compact"`; both
conditions in this probe enabled compact tool feedback separately.

Fifty-eight relevant CPU checks passed, including actual CLI/HTTP prefix delivery
and early-finish rejection, passing-check-without-finish rejection, and eventual
explicit finish. Five additional private supervisor-guard checks passed,
including settled unfinished workflows being gradeable and uncertain effects
being refused before grading. Twenty-four fresh-oracle controls passed. These
are machinery checks, not evidence that the model learned or improved.

Three older bootstrap fixtures also failed unchanged on the published base
because their synthetic servers omitted required connection discovery. That
separate test-only defect was subsequently fixed in
[`76986b2`](https://github.com/CC-David-CC/BranchWrite/commit/76986b2c9b5069fd70bcb45288d8713de895be48).
It was not a failure introduced by this instruction option. No behavior default,
verification gate or model candidate was promoted from the abandoned probe.

## Integrated CPU checkpoint

The native-learning branch now includes the separate discovery fixture repair,
compact-feedback option and finish-request option together. On that combined
source, **166 focused CPU checks passed**, including actual CLI/HTTP bootstrap,
retained-prefix admission, direct-tool grammar, feedback, checks/finish, restart
and unknown-effect refusal. [CPU evidence](../validation/combined-coding-protocol-20261025-bl/cpu-checks.json)
records the modules, source and log hashes. This is not a full-suite or native
behavior qualification; the abandoned trial above remains the actual behavioral
evidence. Both options stay opt-in.
