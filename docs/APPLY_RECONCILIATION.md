# Retry after application loses its acknowledgment

Application accepts --operation-id ID. Retain that ID for retries. If omitted,
a stable destination-scoped ID is derived from archive hash, canonical source
and destination paths. A different ID denotes different work; it cannot claim an
existing output. IDs are destination-scoped, not global workflow operation IDs.

Before publication, the staged root receives a user.branchwrite.apply.v1 extended
attribute binding operation intent, archive hash, expected inventory, device and
inode. This metadata moves with the atomic directory rename; no receipt/project
file or second workflow ledger is introduced. Linux filesystem support for user
xattrs is required; unsupported storage fails before publication.

Retry verifies ownership metadata, the same root identity and the full current
result inventory, repeats flush boundaries and returns the SAME result. It does
not require the original input bytes to remain unchanged after a successful
publication. An unrelated directory, changed result, new operation ID or copied
receipt cannot turn into success. Hostile same-UID metadata forgery remains
outside the existing OS ownership boundary.

Actual subprocess os._exit tests pass before rename and after rename/before the
parent flush. These are process-crash tests, not power-loss qualification. A
prepublication crash may leave a task-owned .bw-apply- staging directory. No
automatic orphan sweep is provided. Never remove other workers' staging files.
Existing pre-feature outputs without ownership metadata cannot be reconciled;
they remain preserved and refused. No in-place checkout application is added.
