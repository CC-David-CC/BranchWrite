# Preserve a BW failure and its correction

These optional commands archive private workflow evidence. They do not grade the
task independently, approve a lesson, select training targets or update weights.
The existing `lesson create` command keeps its host-authored schema1 meaning.

Capture the failed state **before** changing its files:

```sh
branchwrite lesson capture-failure /absolute/run --output /absolute/new-failure-capture
```

After the correction has current passing host checks and an explicit successful
finish, capture it against the original failure:

```sh
branchwrite lesson capture-correction /absolute/corrected-run \
  --failure-capture /absolute/new-failure-capture \
  --output /absolute/new-correction-capture
branchwrite lesson capture-show /absolute/new-correction-capture \
  --expected-capture-id SHA256_FROM_CAPTURE_RESPONSE
```

The task, original project baseline and model contract must match. A correction
can use a later boundary in the same run or a separate run of the same task.
An earlier failing check does not reconstruct files that were never captured.
Keep both archives and their returned identities. Output directories must be new
and outside the run, input project and original failure archive. Failed capture
attempts retain an incomplete private directory; absence of `capture.json` means
no completed archive. Do not reuse that directory for a retry.

A correction archive embeds a verified copy of its preceding failure archive.
Reading it does not consult original run, source-project, world or native-journal
paths. Both boundaries bind the same task, original baseline and model contract;
a correction in the same run must also extend the captured failure ledger bytes.
The reader pins the actual installed BW Python validator/helper source closure.
Use the matching reviewed source to read an archive; source drift requires an
explicit reviewed migration rather than silently changing its validation rules.

The supported initial boundary is one local filesystem/terminal world. It copies
exact file bytes and basic modes, complete original ledger/artifact bytes, saved
launch and locally retained COW journals. It holds the existing ledger read lease
through settlement checks, file copying and final source comparisons. A BW writer
cannot resume under that lease. Already dispatched tool effects are checked
separately; the lease alone is not settlement proof.

File reads/edits and `run_shell`/`run_check` are supported. Commands need actual
completed terminal receipts and retired process namespaces. A stopped workflow
may be archived without finishing its program graph when no dispatched effect or
logical model output remains unresolved. A failure need not have run any check:
the initial no-check path accepts the exact recorded baseline with only settled
read/finish observations. Its evidence honestly contains `checks: []` and the
original absent/false workflow verdict. It is not an independently established
failure. Unchecked writes currently refuse because this path does not reconstruct
their complete resulting world. Where checks exist, their inventory must bind the
captured files; stale or unrecorded changes refuse. Corrections always need current
passing checks and explicit successful finish. These are archival boundaries, not
independent model capability scores.

Complete local native generations are validated with the existing COW journal
reader and model-response checks. Capture performs no network requests, recovery,
model execution or tool execution. Pending, missing, partial or conflicting
native evidence refuses. Remote, browser, CAD/Blender, parallel-world and other
unsupported effects refuse rather than claiming generic settlement. The initial
path also refuses `run_tests`; use its already supported bounded terminal command
form through `run_shell` or `run_check`.

Paths must be real owned directories/files. Symlinks, file hardlinks, special
files/modes, changed inventories and overlapping output paths refuse. Existing
executor per-file limits apply; total world content is at most64MiB and20,000
entries, and the full capture is at most256MiB. Nothing is truncated. Archive
objects are private, read-only files; hashes detect changes when an archive is
opened with its owner-pinned capture ID. This is not protection against a trusted
owner deliberately replacing every proof record and its external identity.

Reusable Python readers are `capture_failure`, `capture_correction` and
`read_capture(expected_capture_id=...)` in `branchwrite.lesson_capture`. They
return an immutable `LessonCapture` handle; `manifest` returns a detached value
and `file_bytes(path)` returns verified exact bytes. `independently_verified` and
`training_approved` are always false. SSS must independently execute its own
registered practice oracle against those exact bytes before any provider can
approve a lesson. A passing model-selected BW check is not that oracle.

CPU tests script choices through BW's normal coding workflow and real COW HTTP,
grammar, canonical state and isolated terminal boundaries. They establish capture
machinery only, not native model quality or learning. No GPU is required.
