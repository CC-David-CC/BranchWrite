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
