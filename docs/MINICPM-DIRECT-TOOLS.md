# Optional direct tools and compact coding instructions

For a new `branchwrite code` run, add `--thinking off` to decode directly into
BW's registered tool grammar. Add `--instructions compact` to use short operating
instructions instead of the worked-example prefix. These choices are independent:

```sh
branchwrite code ./project --task-file task.txt --project-files \
  --thinking off --instructions compact
```

The normal connection profile and server key are still required. Use a PCC
MiniCPM runtime with qualified native tokenization and both end tokens. The
model's maximum context is 131,072 tokens; the measured trial used 65,536.

Defaults stay `--thinking standard --instructions worked-examples`. Sampling,
tool authority and verification policy are unchanged by these options. The direct
profile uses a distinct immutable GBNF registration without a thinking ladder.
Compact instructions can start a new root only. Forking a retained root preserves
its prefix; resume preserves its exact saved launch and original operation IDs.
The choices do not silently rewrite partial generations or retry failed effects.

The corrected native MiniCPM path completed one file-repair/output task and
passed independent checks for saved code, output data and input preservation.
That run used six model requests and 275 output tokens; its initial controller
prefix consumed 381 tokens. These are integration findings, not a broad model or
harness ranking. [Evidence](MINICPM-INTEGRATION-EVIDENCE.json) retains earlier
unsuccessful trials, including ones with an unqualified tokenizer.

A host `verified` report means the configured host policy passed. A model-selected
check can omit a requirement. S³ must independently check the task and retention
before accepting a learning-loop improvement. No MiniCPM training or model release
is established by this integration.

## Five-objective follow-up

The qualified native stack completed and independently passed three Python
objectives: empty-input summation, binary search and stable uniqueness. Two shell
objectives failed: quoting a filename timed out with an outstanding request;
propagating a failing command's status exhausted the interpreter step budget.
Input sentinels were preserved. [Evidence](MINICPM-FOUNDATIONS-EVIDENCE.json)
records exact source/model identities and saved-artifact/checker hashes.

These runs used a 64K context, thinking off, compact-v2 instructions, 512 output
tokens per request, 256 interpreter steps and 120 seconds per task. The 12-request
limit applied per model action, **not globally**; the failure-status run made 13
requests. This is not a matched-budget ranking against the external clients.
The original timed-out operation was reconciled as cancelled, not blindly replayed.

At least two peer harnesses passed each shell objective with the same weights.
Investigate BW's tool contracts, errors, verification and stopping behavior before
labelling these model-training failures. The cause is not yet established. Any
fix must preserve the successful Python workflows and independent task checks.
No MiniCPM weight update or accepted learning candidate is part of this screen.

## Shell investigation follow-up

[Trace, changes and rejected variants](MINICPM-SHELL-INVESTIGATION.md) explain
why the original shell runs failed. Narrower tool-card/feedback changes produce
five correct saved artifacts and four completed passes out of five objectives,
with unchanged weights. The failure-status workflow still does not finish.
This development branch is not a broadly accepted repair.
