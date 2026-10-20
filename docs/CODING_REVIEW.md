# Review and export a coding run

Run branchwrite review STATE to inspect changes; add --json for structured output.
Run branchwrite export STATE /another/directory/changes.zip to save a complete
reviewed bundle. The destination must be new and outside both the original
project and run state. Existing files are never overwritten.

For newly admitted projects with an immutable input baseline, review compares
every file and directory. This includes changes made by shell commands. It
rejects changed protected files, ungranted creations/modes, unsupported deletions,
directory-mode changes and unexpected directories. New parent directories are
permitted only for granted creation paths. Bytes, hashes, modes, binary status
and final-newline flags accompany file diffs.

Review requires completed recorded verification and a current workspace matching
the inventory frozen before the last successful command. Thus a command that
edits files needs a subsequent verification command. Review does not rerun tests.
It excludes unjoined workflow work and never dispatches tools or inference.

Older runs without the initial baseline remain readable as recorded-file-tools
coverage; complete_project_patch is false and export refuses them. We cannot
reconstruct an immutable original from today's mutable checkout.

The ZIP contains manifest.json and deduplicated payloads named by SHA256. Its
format is bw.review-export.v1. Staging bytes are flushed before exclusive final
publication and parent-directory flush. The private archive has mode0600.
A crash may leave a staging file; power-loss and all publication crash points
remain unqualified. After a lost export acknowledgment, inspect the existing
archive rather than replacing it.

Export is an artifact handoff. It does not apply a patch or publish a Git commit.
Guarded application, destination-preimage validation and transactional recovery
remain outstanding. Do not blindly extract this archive over a checkout.
