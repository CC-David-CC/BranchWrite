# Frozen project input

New metadata-free-project-v1 runs capture the initial owned workspace before
inference/tool dispatch. File payloads and chunked directory/file inventories are
immutable artifacts in the existing RuntimeLog. A Text-valued root input binds
the manifest's hash and size. It is derived project evidence, not model history
or a second workflow log.

The existing private no-follow reader, 4 MiB per-file limit, 64 MiB project limit
and 20,000-entry limit remain. Manifests chunk at512 entries to preserve canonical
codec limits. Directory modes, empty directories, binary bytes, file modes and
content hashes are retained. The full workspace inventory is checked before and
after capture. This detects ordinary concurrent drift; it does not promise an
atomic snapshot against a malicious same-UID process changing and restoring data.

Restart loads and validates the original retained manifest/payloads. It never
recaptures the modified workspace. Missing state is an error. Runs admitted before
this feature cannot silently acquire an initial baseline after tools ran.
Legacy generic runs without this project policy retain their existing behavior.

Artifacts are currently retained by RuntimeLog; no artifact GC is introduced.
Any future ledger GC must traverse the manifest -> chunks -> file payload
references rooted by this canonical input, as well as existing nested tool and
result references. Merely retaining direct event roots would be incorrect.
Capture/validation costs occur at admission/reopen, not on every generated token.
Their cost for larger projects remains to be measured.

This supplies the input required for full-project review/export, including shell
edits. That comparison and guarded export/application remain the next work.
