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

## Registered native optimizer jobs and private model checkpoints

With the matching PCC native-learning-path version, BW can discover an owner's
AdamW/Muon policies, request a single-example or batched full-weight update,
continue a registered parent's weights, and preserve a named private GGUF.
BW owns the client request journal; PCC still owns native math, resources,
optimizer state and immutable candidates. No optimizer is implemented in BW.
S3 owns checked practice, evaluation and next-block proposals.

```sh
branchwrite lesson optimizers
branchwrite lesson submit checked-lesson.json --operation-id example-01 \
  --train-now --mode full --steps 68 --learning-rate 0.000001 \
  --optimizer-profile-id PROFILE_SHA256
branchwrite lesson train LESSON_ID_1 LESSON_ID_2 --operation-id block-02 \
  --parent-job-id example-01-train --mode full --batch-size 2 --steps 68 \
  --learning-rate 0.000001 --optimizer-profile-id PROFILE_SHA256
branchwrite lesson status block-02
branchwrite lesson preserve block-02 --operation-id preserve-02 \
  --name MiniCPM-Local-02-F32 --expected-sha256 CANDIDATE_SHA256 \
  --notes-file model-notes.txt --report-sha256 S3_REPORT_SHA256
branchwrite lesson exports
```

Use the connection already configured for BW and `BW_COW_API_KEY`. A profile ID
binds the owner's exact rate, optimizer settings, fresh/resume state policy and
optional training-phase time budget. Current learning curves use a null time
budget: explicit updates and consumed practice presentations define exposure.
The 68 steps above illustrate a declared update count, not a universal training
recipe or the end of the learning loop. Use the advertised rate explicitly. Fresh
moments are appropriate for a changed block while retaining learned parent
weights; resume continues the exact saved dataset order, moments and cursor.
Clients supply registered IDs, never model/executable/state paths or GPU grants.
Explicit profiles require full-weight mode and currently cannot be combined
with the legacy `--skill-guard` multi-round wrapper. Jobs without a profile
retain the previous path.

If a deliberately timed profile is selected, it can finish before visiting every
selected lesson. Check actual
completed updates, presentations and `consumed_lesson_ids_this_job` /
`unconsumed_lesson_ids_this_job`. Queue selection is not proof of consumption.
The tiny proof deliberately exercises this distinction. A lost response is
reconciled using the original request bytes and operation ID; another ID would
request another update. Preservation also reconciles its original operation.

Preservation names a completed full-weight checkpoint privately using a bound
manifest and hardlink in PCC's store. It performs no model upload, quantization,
weight replacement or quality approval. Record a measured S3 report and the
reasons to try the model. Keep development and sealed qualification distinct.
The owner may retain a useful working checkpoint despite some regressions and
practice their families in the next mixed block; preserve those measurements.

[Real tiny CPU BW-to-PCC proof](../validation/native-learning-cli-20261024/results.json)
passes four native jobs across AdamW/Muon, single and batched requests, parent
weight continuation with fresh moments, actual coverage reporting, repeated
operation reconciliation and private named preservation. Six CLI refusal cases
and nine lesson tests plus 22 client transport tests pass, including lost export
acknowledgments and
forged different-weight receipts. This is mechanics qualification, not a BW
shell-task repair or full-model GPU qualification of BW's client.

[Owner configuration and PCC commands](https://github.com/CC-David-CC/Private_Context_COW/blob/feat/native-learning-path-20261024/docs/NATIVE-LEARNING-JOBS.md).
[Full-model learning measurements](https://github.com/CC-David-CC/sss/blob/feat/minicpm-baseline-20261024/docs/MINICPM-NATIVE-LEARNING.md).
The automatic durable multi-round coordinator and shared inference/training
forward graph remain unfinished. This client adds supported pieces to the
existing service rather than introducing another workflow runtime.

The [per-update MiniCPM study](https://github.com/CC-David-CC/sss/blob/feat/minicpm-baseline-20261024/docs/MINICPM-NATIVE-LEARNING.md)
compares four full-update regimens and native AdamW LoRA at matched practice
exposure. The LoRA curve currently uses PCC's qualified owner/native route,
not BW's registered full-weight optimizer-profile selector.
[Precision-retention results](https://github.com/CC-David-CC/sss/blob/feat/minicpm-baseline-20261024/docs/MINICPM-QUANTIZATION-RESULTS.md)
measure whether smaller inference artifacts retain learned behavior; exporting a
GGUF alone does not establish that.
