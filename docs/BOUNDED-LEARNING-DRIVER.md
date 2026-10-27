# Drive a supported learning round from BW

`branchwrite learning drive` follows the registered PCC learning run until a
round settles, a client bound is reached, or owner input is needed. A person
or an agent can use the same command. PCC owns phase state, native updates,
evaluation and working-parent decisions; BW uses its existing request journal.
S³ owns skills, verified practice and paired learning/forgetting reports.

The service owner first installs a qualified model, native runner, protected
assessments, verified practice registry and learning policy. This command does
not configure those components or approve a model's own lessons. Follow the
[configured COW guide](https://github.com/CC-David-CC/sss/blob/feat/learning-stack-20261026/docs/CONFIGURED-COW-LEARNING.md)
and the [verified practice guide](https://github.com/CC-David-CC/sss/blob/feat/learning-stack-20261026/docs/BW-VERIFIED-PRACTICE.md).
Use the current service's real policy and lesson IDs. Keep connection credentials
in the existing private connection setup and environment.

```bash
python -m branchwrite learning --connection /owned/cow.json policies
python -m branchwrite learning --connection /owned/cow.json \
  start --operation-id study-001 --policy-id REGISTERED_POLICY_ID
python -m branchwrite learning --connection /owned/cow.json \
  drive study-001 --operation-prefix study-001-driver --maximum-seconds 300
```

The first call can run the baseline and return `NEEDS_LESSONS`. Review the
observed failures, create independently verified practice variations outside
the protected assessment, and admit them through the existing lesson pathway.
Then supply the explicit admitted selection:

```bash
python -m branchwrite learning --connection /owned/cow.json \
  drive study-001 --operation-prefix study-001-driver \
  --lesson-id VERIFIED_LESSON_ID --lesson-id VERIFIED_REVIEW_ID \
  --maximum-transitions 16 --maximum-seconds 300
```

The installed policy checks the selection and its full mixed-review batch.
The driver cannot submit scores or change an optimizer, learning rate, native
deadline, context limit or acceptance threshold. It advances pending tests and
reports, waits for owned jobs, and reconciles only advertised original work.

## Read the returned status

The JSON contains the unmodified `server_status`, submitted operation IDs and
one of these client outcomes. A successful command exit means an observation
was returned; inspect `status` before deciding the round is finished.

| Status | Next action |
| --- | --- |
| `ROUND_COMPLETE` | Read the paired report and working-parent decision. Another call does not start another round. |
| `NEEDS_LESSONS` | Select admitted, independently checked practice and mixed review. |
| `WAIT_LIMIT` | The client stopped waiting; the original server work continues. Read status or invoke the same driver again. |
| `TRANSITION_LIMIT` | Inspect the returned phase; invoke again if more advertised steps are wanted. |
| `NEEDS_OPERATOR` | Inspect the original failure and recovery evidence. The driver does not adopt a candidate or retry training. |
| `POLICY_UNAVAILABLE` | Restore the exact owner policy or inspect retained history. |
| `NOT_ACTIONABLE` | Required owner inputs or advertised actions differ. Inspect the original status. |
| `STOPPED` | The run was deliberately stopped. Preserve its history. |

Use the same operation prefix and state directory when resuming. Each revision
selects a stable operation ID. The existing CowClient journal binds its original
request bytes and reconciles lost acknowledgements. A changed lesson selection
at the same original revision is refused rather than given a new hidden ID.
Transport errors terminate the driver; inspect the original operation before
proceeding. Two drivers do not gain permission to race a stale revision.

For an interrupted native process, follow [owner completion recovery](OWNER-COMPLETION-RECOVERY.md):
inspect original receipts, obtain an explicit owner adoption decision if all
existing checks pass, then reconcile that original learning run. The bounded
driver returns `NEEDS_OPERATOR` at this boundary, even if a reconciliation action
is offered. It cannot grant itself adoption authority.

## Preserve and repeat

After a reported full-weight round, preserve the current working parent with
the existing command. This names a private GGUF; it does not upload weights.

```bash
python -m branchwrite learning --connection /owned/cow.json \
  preserve study-001 --operation-id study-001-preserve \
  --name My-Working-Model --notes-file /owned/reviewed-notes.txt
```

The working parent can remain the older model when a candidate fails the
registered decision rule. Preserve a rejected candidate separately through
`branchwrite lesson preserve` with its explicit job, hash and report binding
when retaining it is useful. A local working-parent decision is not permission
to publish weights or a claim of broad model acceptance.

When the owner is ready for another skill block, use explicit `learning advance`
on the completed run, then `drive` with the next verified selection and a new
block prefix. PCC enforces the installed policy's round limit. At that limit,
start a new run bound to the exact completed working parent; keep prior history.
The owner or supervising agent remains responsible for lesson generation,
review coverage, sealed qualification and deciding which experiments to pursue.

## Qualification

The [validation receipt](../validation/learning-drive-20261027.json) records
11 client-control tests plus nine existing lesson/provenance checks. The new
client tests inject wire responses and use the actual CowClient journal.
Separately, S³'s real tiny-model CPU integration completed three rounds and
48 native updates; the driver handled the final round. That integration checks
authenticated HTTP, both CLIs, restart, interrupted dispatch, lost acknowledgements,
stale revisions, paired reports, no-gain parent retention and private preservation.
This qualifies machinery, not MiniCPM capability or a production reliability rate.

Run that independent opt-in suite from the matching S³ checkout:

```bash
python -m sss machinery run learning-rounds-cpu \
  --pcc-root /owned/PCC --bw-root /owned/BranchWrite \
  --executable /owned/cpu-build/pcc-native-train \
  --output /owned/new-private-proof --bounded-bw-driver
```

The suite is separate from the frozen 68-update optimizer comparison. It uses
a generated tiny classifier and disjoint practice/evaluation prefixes, not
protected real-model assessment answers.
