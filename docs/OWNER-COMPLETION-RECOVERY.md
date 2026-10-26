# Recover an original completed training job through BW

This is an owner administrative workflow for a person or an owner agent. It uses the same PCC service and BW operation journal as the learning loop. It never runs training, inference, or model promotion. The student's tool registry does not gain these commands or approval permissions.

Use it when PCC reports `needs_operator` with `operator_reason_code: native_job_unresolved`: the original native process may have finished, but the service did not durably acknowledge its candidate. Do not submit a replacement training job or edit saved run files to escape this state.

## 1. Inspect the original boundary

With your existing BW connection and private state directory, read the original run and job:

```sh
branchwrite lesson --connection owner-connection.json --state-dir owner-state learning-status ORIGINAL_RUN
branchwrite lesson --connection owner-connection.json --state-dir owner-state inspect-completion ORIGINAL_JOB --output original-completion.json
```

Keep the run's `training_job_id`, run ID, revision, lesson IDs, and parent identity. These identify the work that actually happened. The inspection file is newly created with owner-only permissions and binds the original job, model contract, endpoint URL/pin, validated PCC inspection, and inspection digest. It contains administrative metadata, so keep it private. BW refuses overwriting it, symlinks, changed digests, other jobs, models, and endpoints.

Read `inspection.state`, `reason_code`, and `next_actions` in the returned document:

| State | Meaning and owner action |
|---|---|
| `eligible` | PCC freshly verified original completion evidence. Explicit adoption is available. |
| `adoption_pending` | Retain `pending_operation_id` and the exact original approval; resume only that metadata transaction. |
| `adopted` | The original completion is freshly verified and already adopted. Continue with the original learning run. |
| `unavailable` | HOLD. The worker boundary is busy, the original process is live, or evidence is incomplete. |
| `ineligible` with `original_job_already_complete` | No adoption is needed. Inspect the original job and learning status; this ordinary completion is not invalid model evidence. |
| Other `ineligible` reasons | HOLD. Provenance is missing, bytes/gates are invalid, or the transaction conflicts. |

A normal complete job reports `next_actions: ["inspect_original_job", "learning_status"]`, including when completion recovery was disabled. Read it with `branchwrite lesson status ORIGINAL_JOB` and `learning-status ORIGINAL_RUN`; do not attempt adoption.

A HOLD does not authorize another training job, a new approval ID, or manufactured historical provenance. Diagnose the stated reason and inspect again after the actual boundary changes. Unknown server responses also HOLD.

## 2. Explicitly approve the original completion

For an eligible inspection, choose one stable approval operation ID:

```sh
branchwrite lesson --connection owner-connection.json --state-dir owner-state adopt-completion ORIGINAL_JOB --inspection-file original-completion.json --operation-id adopt-original-job --approve-original-completion
```

The file supplies the three original compare-and-swap pins; you do not need to copy hashes by hand. PCC independently checks the current job record, evidence, and candidate bytes against them. A stale file is refused rather than silently replaced. A manual route is also available with all three `--expected-job-record-sha256`, `--expected-evidence-sha256`, and `--expected-candidate-sha256` values from a fresh verified inspection; do not mix that route with `--inspection-file`.

BW durably journals the exact metadata request before sending it. Lost acknowledgments remain unresolved until the original operation receipt proves commitment. An explicit retry retains the exact same endpoint, approval operation ID, job, body, and pins. Only this original metadata approval may resume; BW does not replay a native training job. For `adoption_pending`, the supplied operation ID must equal PCC's `pending_operation_id`.

A successful acknowledgment has `adopted: true` and `promoted: false`. It proves that transaction committed at that time. It is not a fresh byte check: run `inspect-completion` again when current evidence matters. Model/optimizer acceptance thresholds are unchanged; adoption does not approve a lesson, accept a candidate's learning quality, or promote serving weights.

## 3. Return to the original learning round

```sh
branchwrite lesson --connection owner-connection.json --state-dir owner-state learning-status ORIGINAL_RUN
branchwrite lesson --connection owner-connection.json --state-dir owner-state reconcile-completion ORIGINAL_RUN --operation-id reconcile-original-run --expected-revision ORIGINAL_REVISION
```

This dedicated command accepts only the exact `needs_operator` / `native_job_unresolved` boundary where PCC advertises `reconcile` with no required fields. The owner explicitly supplies the current original run revision. The service freshly validates the adopted completion and moves the same round to `candidate_pending`; no native or inference dispatch occurs in reconciliation.

If a response is lost, retain the same reconciliation operation ID and original revision. BW looks up the original acknowledgment before applying current-phase checks, because commitment may already have moved the run. If no acknowledgment exists, a retry can POST the same metadata step only while the exact recovery boundary and revision still hold. A changed or uncertain boundary HOLDs, with the journal preserved.

Then use the normal `branchwrite learning status`, `round`, and `advance` commands on that same run. Candidate evaluation can make inference calls at that later, explicit learning-loop step. Learning/forgetting assessment and any later promotion remain separate from completion recovery. Diagnostic rejection can retain a candidate for approved future practice without promoting it; this recovery route changes neither policy.

## Qualification scope

The focused BW contracts use controlled nonmodel metadata, real private files and operation journals. The cross-project HTTP tests additionally use PCC's saved-evidence fixture; those fake candidate bytes are explicitly not a model. They verify real routes, identities, strict acknowledgments, compare-and-swap refusal, replay boundaries, and no-dispatch behavior. They do not establish numerical correctness or reload equivalence for a real trained model. Legacy jobs lacking original predispatch provenance or required numerical gates remain refused. A bounded real-model qualification is a separate step.
