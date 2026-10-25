# Experimental compact model-visible tool feedback

An owner may opt in on a new coding launch:

```python
launch = build_launch(project, task, connection, branch=branch, project_files=True)
launch['config']['tool_feedback'] = {'schema': 1, 'format': 'compact-v1'}
save_launch(state, launch)
```

Omit this setting for the existing presentation. No new CLI flag is added.
The original saved launch, host configuration and interpreter identity bind the
choice; do not switch formats while resuming an admitted workflow.

The compact representation removes repeated plan/output hash renderings from
model-visible text. It retains the operation ID, exact executed command, status,
bounded stdout/stderr text, truncation flags, file observations, shell boundary
instructions, diagnostic guidance and unchanged verification. A `streams` mapping
retains each raw stream's byte count, displayed byte count and lossy-decoding flag;
`decoding` records UTF-8 replacement behavior. Raw outputs, hashes, original
ToolOutcome records and verification proof artifacts remain in the existing ledger.

This changes presentation only. It executes no extra tool, changes no grants,
rewrites no shell command or output, changes no grammar, and does not turn a
passing command into a completed workflow. Explicit finish and stale-check
refusal still apply. The setting is also inherited by isolated candidate worlds.

CPU checks exercise real namespace execution, binary/truncated output, unchanged
canonical receipts, restart without effect replay, frozen configuration and the
existing finish/selected-check policy. These CPU checks establish mechanics;
the live development measurement below assesses behavior. Fresh variants and
independent artifact plus whole-workflow checks are still required before
adopting a new default.

A CPU-only rendering measurement over 12 saved tool-feedback messages from the
remaining shell diagnostic used the official MiniCPM5-2B F16 GGUF vocabulary.
The same feedback values occupied 6,336 reference-tokenizer tokens with the
existing rendering and 3,925 with `compact-v1` (38.1% fewer). UTF-8 text fell from
18,526 to 14,080 bytes (24.0%). This measures these messages only, not whole-task
context, inference speed or behavioral improvement; protected task content stays
in private evidence. The host card and first task request are unchanged.

Default and compact live controls must use this same source build: BW already
binds source hashes into interpreter identity, so updating source can change
opaque operation IDs even when the option is omitted. Omission retains the
existing rendering path and fields, not the old build's source-bound identity.

## Same-source live development probe, October 25

A bounded baseline-versus-compact probe ran the five original development
objectives through actual BW tools and PCC native inference on an RTX 4090.
Both conditions used this same BW source, the original MiniCPM5-2B F16 weights,
the same qualified PCC runtime, fresh workflow states and identical paired task
and checker commitments. Only the owner-selected `tool_feedback` option changed.
No model training occurred.

| Measurement | Baseline | Compact |
| --- | ---: | ---: |
| Correct saved artifacts | 4/5 | 5/5 |
| Completed independent passes | 4/5 | 4/5 |
| Whole-workflow model requests | 36 | 39 |
| Generated output tokens | 1,857 | 2,231 |
| Newly supplied tool-feedback tokens | 16,399 | 11,522 |
| Native forward tokens | 30,811 | 26,347 |

Both conditions completed the first four objectives. On the remaining
failure-status objective, the baseline repeated the same exploratory shell call
ten times without editing the source, registering a check or finishing. Compact
saved a correct repair and reached four named checks, but repeated checks without
requesting finish. Both exhausted the 256-step cap after 13 model requests.
Compact therefore recovered one saved repair in this probe; it did **not** solve
workflow termination. Keep it opt-in.

Observed feedback tokens fell 29.7% across these live trajectories, while model
requests increased by three and generated output by 374 tokens. Native forward
tokens fell 14.5%, but the trajectories differ: neither number establishes an
end-to-end speedup or lower overall compute cost. The earlier 38.1% reduction
measured identical saved feedback rendered both ways and is a different result.

The new-source baseline did not reproduce the older control's correct saved
repair. BW source changes affect source-bound operation IDs and hash-bearing
feedback, so the old-source trial is historical evidence rather than an
interchangeable control. Five original development objectives, one run per
condition, establish neither a failure rate nor unseen transfer or mastery.
This is a harness-only result; [native model-learning results](https://github.com/CC-David-CC/sss/blob/feat/minicpm-baseline-20261024/docs/MINICPM-NATIVE-LEARNING.md)
belong to a separate experiment.

The [shareable aggregate](../validation/minicpm-compact-feedback-20261025-bh/results.json)
records exact model/runtime identities, qualified source and grader hashes,
independent outcomes and measurement definitions. Original prompts, solutions,
raw outputs and owner-local evidence stay private. A full post-run source audit
reported three concurrent S³ Markdown edits; their expected and actual hashes
are recorded without changing the original manifest. BW code, S³ grading inputs,
PCC runtime, native dependencies and weights remained unchanged.

All 105 COW journal operations settled. Only the owned probe server and child
were stopped; its port closed and GPU lease was released. No uncertain operation
was replayed.

## Reproduction protocol

Use the aggregate's frozen BW source hashes, original F16 weight hash and
qualified PCC profile/runtime closure. The recorded original PCC commit matches
all 672 selected runtime files; changing that source requires an explicit new
execution identity and qualification rather than silently updating hashes.

Create fresh projects, saved BW launches and COW branches for every condition
and objective. Obtain the five declared cases through S³'s
`sss.suites.code_foundations.cases`; keep independent checker programs outside
model-visible projects. Preserve identical paired instructions and protected
input bytes. Omit `tool_feedback` for baseline; set the option shown above for
compact. Keep host cards, grammar, grants and readiness configuration unchanged.

Use 65,536 context tokens, thinking off, greedy sampling, 512 output tokens per
request, 12 requests and 6,144 output tokens **per model action**, 256 interpreter
steps, a 120-second task guard and a 20-second shell timeout. There is no global
12-request cap. Run baseline then compact on cases 0, 2 and 4; reverse that order
on cases 1 and 3. A blocked condition must not silently change its budget.

After each workflow stops, independently grade the actual saved files with
S³'s `run_check` and `grade`. Score artifact correctness separately from BW
verification, explicit finish and zero pending operations. Count admitted tools
from read-only canonical ledger replay, not proposed model actions. Feedback
tokens mean newly appended feedback content, not accumulated context; native
forward counters measure actual recorded processing under its caching path.

Stop on an unsettled native request, preserve its original immutable handle and
reconcile that operation before replay, continuation or shutdown. After all
operations settle, release only the owned server and verify its process, port
and GPU lease. The original owner-held protocol has SHA-256
`7f8fbf48e9a86de7246b053407592761429986b6e74938e95029ab0fd216e894`;
its raw diagnostic material is deliberately excluded from this public report.
Qualify any proposed default on separately specified fresh transfer variants.
