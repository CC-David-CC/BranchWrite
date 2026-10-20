# Use reviewed changes in a new project copy

Run:
branchwrite apply changes.zip --source /path/to/original --destination /path/to/new-project --sha256 HASH

Use the archive SHA256 printed by export. The destination must not exist and
must be outside the source tree. Application never modifies the original checkout
or carries over its .git administration. The result is a standalone project copy.

The original complete project inventory must match the reviewed immutable input,
including protected files and modes. Each changed file also has an exact preimage
check. Archive hash, payloads, paths, sizes and final inventory are validated.
Staged file and directory bytes are flushed before Linux renameat2 publishes the
tree with NOREPLACE. An existing destination, including one created in the final
publication race, is preserved. No check-then-replace fallback is allowed.

If application loses its acknowledgment, retry with the original --operation-id.
New publications carry directory ownership metadata so exact retries can verify
the same root and return the same receipt. Old outputs without metadata remain
preserved and refused. See APPLY_RECONCILIATION.md for scope and subprocess tests.
Power-loss recovery and orphan-stage cleanup remain unqualified. This does not
mutate a workflow ledger or implement the language COMMIT operation. In-place
checkout updates and Git integration remain configured future boundaries.

Scope is Linux/local filesystem with renameat2 support and exclusive owned
staging. A malicious same-UID process changing staging/path ancestry is outside
the current boundary. Input archives are explicitly hash-pinned; this is not a
signature or proof that an arbitrary third-party archive was authorized.
The current archive read/expansion bound is256MiB with4MiB file payloads.
