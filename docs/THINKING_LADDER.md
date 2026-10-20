# Automatic thinking retries

New coding runs start with a 4,096-token thinking allowance and the standard
4K -> 8K -> 16K -> 32K ladder. The model may finish thinking naturally before
its allowance. A completed finish rejected by the host advances one rung even
when thinking ended naturally.

The interpreter now connects the host verdict, original proposing model frame,
COW planning fork, named thinking grammar and subsequent model FLOW. This is
implemented, admission-tested and now exercised through the real remote CLI,
HTTP server and Q4 GPU. See the bounded live results below.

## New-run configuration

The default coding profile selects thinking_ladder=standard with output_format
thinking and grammar_state BW_TOOLS. The startup registry must contain all the
corresponding immutable named definitions. A host may select lite with its
initial BW_TOOLS_THINK_256 definition; live Lite tests remain deferred.

An explicit profile without thinking_ladder uses its selected single grammar.
A ladder profile must name its initial rung. Unknown modes, text-only ladder
profiles and incompatible starting definitions are rejected before model work.
New admission never rewrites a saved or active controller. Old successful runs
and frozen runtimes remain retained; source identity changes are not silent
migrations of those runs.

There is no 1,024-token final-answer cap. The default model-call resource budget
is 32 requests of at most 2,048 tokens, at most 65,536 consumed output tokens
including thinking, and 262,144 result bytes. These are finite resource bounds,
not answer targets. A reply may continue across requests, but an incomplete
reply is never an executable tool proposal. Larger explicit budgets remain
subject to the existing adapter and context limits.

## What causes a retry

Only an actual completed finish rejected by host verification is a verified
task failure. A failed intermediate test, read, tool rejection, or other ordinary
progress stays on its rung. Infrastructure faults and unknown external effects
require settlement; they do not spend another reasoning attempt.

Verification records its exact tool operation ID and proposing model frame.
The interpreter follows the actual ACT/PLAN binding, not whichever model output
happened to finish last. Unit-test verification requires a joined, visible,
current-registry/current-world test receipt and unchanged file inventory.
Manually supplied proposals do not borrow a model planning origin.

The rung is derived from distinct visible committed failed-finish operation IDs
for the same origin, profile and canonical root. Checking the same finish twice
does not count as two failures. Previously handled failure IDs are recorded in
the next FrozenModelCall. Ordinary later progress does not refork that failure.
No retry database, outer agent driver or second model history is introduced.

## Branches, recovery and real effects

On a new verified failure, retain the failed computational branch. Fork the
failed model call's recorded input snapshot. Preserve its original ask versus
append_user boundary and input parts, including image identities. The new input
adds generic critical-review guidance and already-public observations. It asks
the model to separate givens from assumptions, identify contradictions and try
another approach; it does not reveal protected answers or patches.

COW owns snapshots, native state, grammar/parser progress and RNG. BranchWrite's
planning annotation contains pointers and host decisions, not another transcript.
A retry freezes the verdict/model provenance and a current-world file inventory
witness. Native rollback cannot undo acknowledged filesystem/tool effects.
The model must reobserve current files before further mutation.

planning_retry uses the original FrameKernel: COWForkReceipt, then ModelOutput.
A complete consumed EOS result is required before its caller slot closes.
Dropped acknowledgments retain the original fork/native operation IDs.
Reopening uses existing records; unknown effects block automatic resend.

The last failed rung returns thinking_ladder_exhausted without a new native
request. The existing workflow iteration/step/output budgets are independent.
For example, coding.bw currently allows 16 tool decisions total; it can exhaust
that explicit bound before all four thinking rungs are used. Budget exhaustion
is not a successful answer or proof of cancellation.

## Time allowances

| Mode | Thinking tokens | Declared planning allowance, seconds |
|---|---|---|
| Standard | 4096, 8192, 16384, 32768 | 180, 360, 720, 1440 |
| Lite, opt-in | 256, 512, 1024, 2048, 4096, 8192, 16384, 32768 | 30, 45, 60, 90, 180, 360, 720, 1440 |

These time values are NOT enforced yet. They are not measured speed estimates.
Timing/cancellation must be enforced at an owned, settled generation boundary;
a transport timeout alone never authorizes another attempt.

## Executed evidence and limits

Current regression results: 63 client CPU/browser checks and 60 server CPU/HTTP
checks passed with zero failures, errors or skips. Some unit cases execute on
both hosts; these totals are not unique acceptance IDs or a gate percentage.

The eight new selector tests explicitly script model return values into the
canonical unit ledger. They prove admission/selection behavior, not native
thinking, numerical agreement, autonomous model quality or GPU execution.
Separate actual CPU HTTP/COW tests exercise fork/model transport and recovery.
These scopes remain distinct from the bounded real Q4 trial below.

See these profiles and their verified private raw archives:

- validation/TASK-VERDICT-SCOPE-2026-10-18.json
- validation/PLANNING-RETRY-FLOW-2026-10-18.json
- validation/THINKING-PLAN-CONTEXT-2026-10-18.json
- validation/THINKING-SELECTOR-2026-10-18.json

The initial selector red run had seven missing-feature errors. The first green
attempt exposed a blank line in the new test program; the strict .bw parser
correctly refused it. The fixture was corrected, without changing the parser or
acceptance assertions. The new-default assertion was separately observed red.

Remaining: connected final-rung exhaustion, restart across all connected
selection stages, larger-output behavior,
settled timing enforcement and broader image/controller combinations. General
BRANCH/PARALLEL language forms remain unsupported. Lite live retests and Q8 are
deferred. Full VC00-VC09 and G1-G5 qualification remain separate and incomplete.

## Bounded real Q4 trial: 2026-10-18

The CLI ran on llm-49, the authenticated COW service and real GPU on llm-60.
The ordinary file task passed autonomously: read, replace, read back and finish.
Four model calls used the 4K allowance and produced 257 consumed output tokens.
The source fixture stayed unchanged; only the granted workspace file changed.

A second trial changed the workspace file after an acknowledged finish, before
host verification. No model/tool choice or repair was supplied by the harness.
The host rejected that finish. The interpreter retained its failed tip, forked
the recorded planning point and selected 8K. That attempt repeated a stale
readback assumption and requested finish again. After the second host rejection,
the 16K attempt reread and repaired the file. Both failed tips and their
controller identities remained unchanged. Nine model calls produced 2,471
consumed output tokens; the actual rung sequence was 4K,4K,4K,4K,8K,16K,16K,16K,16K.

All thinking ended naturally. The recovery thought used 1,319 tokens, which
would also fit the earlier allowance. This trial does not show that the larger
cap caused success: accumulated guidance and sampling also changed. The stale
readback observation is saved as an unreviewed failure-class candidate under
/home/dflanag3/src/branchwrite-lora-examples/candidates/
stale-readback-after-rejected-finish-20261018 on llm-60. No training is approved.

The fault trial used 201 separate public CLI steps, with the observer reading
only after each writer exited. Completed workflows reopened with the tunnel
stopped. This is CLI/ledger restart evidence; the native process stayed alive.
It is not a native-process or disk-restart numerical campaign.

Baseline whole CLI time was 27.24 seconds; the fault step campaign took 139.25
seconds including process/reopen audit costs. Server-reported generation rates
were 39.46 and 36.90 output tokens/second, including reasoning/final/EOS and
serving overhead. These are not isolated CUDA decode rates or a controlled
comparison with older 92 TPS runs. No validation-cost percentage is inferred.

The first fault observer launch failed its import preflight before positive
work. Its engineering evidence is retained separately, not a model LoRA pair.
The corrected trial passed. Native integrity mismatches: zero. No fresh-logit
oracle ran, so numerical maximum error is NOT MEASURED, not zero.

See validation/THINKING-LADDER-Q4-2026-10-18.json for fingerprints, exact failed
tips, native work counters and the receiver-verified private raw archive.
Post-run G0 passed 51/51 with no failures/errors/skips. Neither this result nor
the CPU counts promotes original G1-G5 or full VC00-VC09 qualification.
All owned GPU/client jobs exited, temporary SSH authorization was revoked and
the chat server remains off. Q8 and live Lite remain deferred.
