# Pin the model or hat when continuing training

An agent can choose a job label correctly while intending a different checkpoint.
Use `--expected-parent-sha256` with `--parent-job-id` to make that intent explicit.
PCC refuses a mismatch before queuing; it checks the binding again before work.

```bash
python -m branchwrite lesson train LESSON_ID \
  --operation-id new-owned-block \
  --mode full --parent-job-id completed-parent \
  --expected-parent-sha256 EXACT_TRAINED_MODEL_SHA \
  --learning-rate 0.000001 --batch-size 1 --steps 1
```

For LoRA, choose `--mode lora`, its actual rank, and the **adapter** hash. The base
GGUF hash alone cannot identify a hat. The CLI also supports the guard on lesson
`create` or `submit` when using `--train-now`. COW's `lesson train` and `submit
--train-now` have the same flag. A malformed hash, missing parent or lesson-only
submission with a training parent pin is refused.

This pins the starting artifact, not the optimizer, lesson selection or release
decision. Choose an owner-registered optimizer policy where supported, and
resolve the full base/adapter/scale reference before dispatch. A fresh lesson
block retains the learned weights while deliberately selecting fresh moments;
same-stream resume requires exact saved moments, data order and cursor. Never
silently substitute another parent or reset moments after a failed resume.

Without `--optimizer-profile-id`, the existing client path uses its legacy SGD
recipe. Full AdamW/Muon training needs an explicitly selected registered profile.
Native/offline LoRA AdamW continuation is tested separately; registered optimizer
profiles currently require full mode. Do not label a default LoRA CLI job as
AdamW. Extending those registered profiles to LoRA remains integration work.

The guard is optional; requests that omit it retain their existing fields and
default behavior. Once accepted, an operation ID binds the entire request,
including its pin. Repeat the original command to retrieve the same acceptance,
or inspect `lesson status JOB_ID`. Changing the pin under that operation ID is
refused. An uncertain response is not permission to launch another update.

The parent must be a completed job known to the selected PCC service. An offline
experiment directory is not a job ID. Server filesystem paths remain owner
configuration and are never client training arguments. The artifact itself is
rehash-checked by PCC's native executor before it is consumed.

[S³'s proposal resolution](https://github.com/CC-David-CC/sss/blob/feat/minicpm-baseline-20261024/docs/RESOLVED-LEARNING-PARENT.md)
and [PCC's artifact reader](https://github.com/CC-David-CC/Private_Context_COW/blob/feat/native-learning-curves-20261024/docs/RESOLVING-TRAINING-PARENTS.md)
explain the complete reference and verified milestone-copy path. Resolution and
the parent pin do not approve lessons, allocate hardware or promote a model.

The real CPU transport check exercised six native full/LoRA jobs through PCC HTTP
and both CLIs, with refused wrong parents and no duplicate accepted updates.
Its S³ decision scores are controlled fixtures, not a measured language-model
improvement. Current Muon/AdamW and harness behavior remain separate studies.

The selected PCC service must support this additive request field. An older
service rejects it; do not remove the guard to retry the same intent. Upgrade
the owned service only after its existing jobs have settled.

[Integration evidence](https://github.com/CC-David-CC/sss/blob/feat/minicpm-baseline-20261024/validation/parent-binding-20261025-ay/cli-integration.json)
and [source/regression receipts](https://github.com/CC-David-CC/sss/blob/feat/minicpm-baseline-20261024/validation/parent-binding-20261025-ay/checks.json)
keep the controlled decision scores distinct from actual native execution.
