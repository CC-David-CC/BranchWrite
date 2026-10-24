# Teach a checked correction

The tree, skill tests and repair curriculum are owned by the separate
[Skills³ (S³)](https://github.com/CC-David-CC/sss) project. Install the optional
`skills` extra or install the matching S³ checkout into BW's Python environment.
BW owns lesson evidence from its real task ledger; S³ owns the test/practice
policy, and PCC owns native updates, context/model identity and GPU resources.

`/skills` displays the broad S³ map. `/lesson skills` displays the server's
configured active curriculum. Model proficiency is not inferred from tool
availability. For guarded training, add `--skill LEAF_ID` when writing a lesson
and `--skill-guard --batch-size 8 --steps 16` when training. The explicit step
budget bounds interleaved practice and repair rounds. Status includes per-skill
results and qualification; no candidate is automatically promoted.

An optional PCC server feature lets you turn a checked correction into a short
lesson. You choose what to teach. PCC trains a separate candidate; it does not
silently replace the model answering your existing conversations.

After BW has failed a check, been corrected and passed verification, use:

```text
/lesson create --prompt "def double(n): return" --completion " 2*n" --title "Use multiplication" --operation-id double-lesson --train-now
```

This uses the latest Work task. It can include both the failed and passing checks
in one run. `--turn NUMBER` selects another entry in `/history`; `--failed-turn`
selects a different original failure. BW reads the canonical run ledger and
checks the corrected files have not changed since verification. Unsettled or
timed-out tool operations and an unverified correction are refused. The owner
still decides whether the cause was a model error and whether the lesson is useful.

For longer teaching text, use `--prompt-file` and `--completion-file`. Outside
the interactive session, run `branchwrite lesson create --corrected-state
/private/bw-run ...` and optionally `--failed-state` for a different original run.
The draft is stored privately outside the project by default.

Replace `--train-now` with `--queue` to collect lessons for later:

```text
/lessons
/train --pending --operation-id batch-1 --batch-size 8
/training batch-1
```

The equivalent shell commands are `branchwrite lesson list`, `branchwrite lesson
train ...`, and `branchwrite lesson status ...`. Existing authored files can be
queued with `branchwrite lesson submit /private/lesson.json --operation-id NAME`.
The standard COW CLI supports the same submission, selection and status actions.

`--pending` means never selected for a previous job. Explicit lesson IDs select
exact examples; `--all` deliberately includes previously selected ones. The CLI
requests enough mini-batches to cover the selection once. A final short batch
gets equal example weights. Use the same operation ID to reconcile the same
request after an uncertain response; it does not issue another update. Selected
lists stay frozen across retries. Failed/interrupted selections need explicit
review before another job.

Add `--parent-job-id PREVIOUS_JOB` to continue a completed LoRA and retain its
rank. `--mode full` updates the model's own weights; its parent must also be a
full candidate. No adapter is merged. `--learning-rate` and `--rank` are optional
settings subject to server limits. Defaults use rank 4 LoRA and native SGD at
0.0001, not a guarantee of useful learning from one example.

The server owner must enable authenticated native training and configure the
model, executable and RAM/GPU budgets. Ordinary servers remain unchanged. The
current trainer supports specific dense Wen/Qwen3.5 BF16/F32 models. Quantized
Flash serving, every home GPU and general large-model CPU training are not
qualified by the CPU wiring test. A 24 GB card cannot hold this Wen trainer's
roughly 32 GB of F32 base weights by itself.

The CPU wiring harness exercises real isolated BW checks and real native updates,
including batching, saved-candidate continuation, reload and duplicate-request
handling. Its tiny generated model is not a language-quality result. The separate
Wen study uses checked variations, unseen evaluations and unrelated preservation
cases. Only those measurements can establish whether a candidate is useful.

The completed 1,000-variation Wen study improved its selection cases from 2/48 to
48/48, but unrelated controls dropped from 16/16 to 11/16 and differently worded
blind cases improved only from 2/16 to 3/16. It failed the declared quality gate.
The candidate remains unpromoted. These controls support experimentation; a
reliably improving everyday BW assistant has not been demonstrated.

The independent [S³ project](https://github.com/CC-David-CC/sss) owns the skill
tree, scoring and mixed replay. The completed five-skill A100 pilot preserved
earlier correct answers but stayed at 14/40 held-out checks after four rounds,
16 updates and 128 mixed example slots. No hat qualified. See
[the full result and limitations](https://github.com/CC-David-CC/sss/blob/main/validation/README.md).
The separate [paired Wen tool benchmark](https://github.com/CC-David-CC/sss/blob/main/docs/MODEL-COMPARISON.md)
uses mock files; actual BW task quality still needs real execution evidence.

After evaluation, the server owner can prepare a new PCC model/adapter
configuration. New BW work can use that connection; saved work keeps its original
identity. Training alone does not promote a candidate or prove an always
improving model. See the matching PCC preview's server-side learning guide for
configuration, native build instructions and the quality harness.

To reproduce the CPU wiring proof on Linux, build PCC's CPU native trainer, then
run this from the matching BW checkout:

```sh
python -m sss_integration.lesson_native_cpu --bw-root /path/to/BW --pcc-root /path/to/PCC \
  --native-executable /path/to/cpu-build/pcc-native-train \
  --workdir /private/new-cpu-proof
```

Run that command from the S³ checkout with its package installed. The harness
creates its own tiny byte-vocabulary model and real controlled BW
tasks. It uses an authenticated training-only HTTP fixture, rather than starting
a production inference server. It refuses an existing output directory, retains
private evidence, and requires single/batch updates, continuation, reload,
unchanged base weights and duplicate prevention to pass.

## Fixed-weight harness improvement is a separate experiment

[S³'s harness comparison](https://github.com/CC-David-CC/sss/blob/feat/foundations-20261023/docs/HARNESS-COMPARISON.md) distinguishes
baseline, a general improvement probe, a task-specific probe and a composed
fourth execution. These are four task runs, plus proposer/composer model calls
and independent transfer/retention runs. The design is strengthened by ideas
incorporated from [Harness²](https://arxiv.org/abs/2610.14224).

BW's existing two-approach exploration supplies isolated alternatives; it does
not itself implement the entire four-condition study. S³'s offline auditor is
implemented and tested. A qualified exporter and proposer/composer integration
for real BW observations are still required. Do not substitute mock-tool
fixtures for measured BW behavior or replace BW's workflow ledger.

The separate [Wen full-update pilot](https://github.com/CC-David-CC/sss/blob/feat/foundations-20261023/docs/WEN-FULL-UPDATE-PILOT.md)
scored 19/54 versus 17/54, with three gains and one lost success. The candidate
was rejected, not installed as BW's model.
