# Hash-bound exact file upload

Executed2026-10-20. Dev51 installed on llm-49, real pinned SSH into the owned
admin01 VM. Current combined CPU/PTY/HTTP-fixture suite:450/450, no failures,
errors or skips; source unchanged. Three installed CLI upload cases passed:
Unicode/spaces/quotes/$HOME filename,2MiB binary payload, and client exit72 after
remote acknowledgment followed by original-receipt recovery. The recovering
client was forbidden to resend the original SSH operation. All11 installed remote
workflow regressions passed too. These are not autonomous-model claims.

The first dev50 installed attempt failed honestly: ~/.local/share on the VM is
0775. Receiver refused that mutable shared parent. Dev51 uses one dedicated
~/.branchwrite-uploads directory; existing shared permissions stay unchanged.
The failed first archive and449-test intermediate suite are retained separately.

upload_file(target,path) requires both a granted target and local read scope.
PLAN freezes the source hash; ACT rejects changed source. Bytes travel as a
bounded4MiB stdin payload, not generated text or a shell argument. Receipt metadata
binds source path, hash, size and actual remote staging path. Empty payloads retain
ordinary schema1 transport; nonempty payloads use explicit schema2 with bound stdin.
Unknown effects never resend. Reconciliation uses retained original input bytes,
not the current local file. Cross-client target checks become stale after upload.

Receiver checks exact bytes/hash, walks parents with directory descriptors and
O_NOFOLLOW, writes/flushed a temporary file, publishes without replacing an existing
name, validates content and fsyncs its directory. Files are read-only0400 in
content-addressed staging. Existing corrupt or linked files fail instead of being
silently overwritten. Staging is not the live website and is not COW's KV cache.
Remote publication still requires a separate granted command and final check.
Automatic upload-cache expiry and privileged process cancellation remain open.

Wheel SHA256:8299bf8569420897ee1cb30e62ba14026cf9eb5ab53892ee6ffd7ce41d5e7dce.
An autonomous Q4 coding-to-upload-to-deployment trial is running separately at
llm-49:/home/dflanag3/spatial-artifacts/bw-code-deploy-q4-dev51-20261020/.
Its independent browser/HTTP acceptance is not yet established.
