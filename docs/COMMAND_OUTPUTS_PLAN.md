# Bounded command outputs

The host may grant output_paths alongside readable inputs and allow_shell.
Output leaves are canonical relative paths,unique,max64,and require read grants.
A file cannot also be the parent of another output. Existing tasks without
output_paths keep the read-only worker protocol.

Explicit output tasks use worker schema2. Readable inputs stay read-only. Needed
output parents use private tmpfs overlays,with protected input neighbors rebound
read-only. The total private capacity is8MiB,distributed across parents with
space for initial files and temporary writes. Each final file is bounded to4MiB.
Initial outputs retain their bytes/mode;absent declared outputs can be created.
Programs can use temporary files,fsync and atomic rename.

After the command exits,the trusted worker checks for remaining command
descendants and captures stable private files. The host independently proves
namespace retirement before publication. Links,special files,undeclared
persistent entries,overflows and changed directory access are rejected.
This is not a cgroup-based general daemon supervisor;broader hostile lifecycle
qualification remains outstanding.

All current output preimages are checked before publication. Existing anchored
file helpers publish only declared leaves. New bytes are rooted in existing
RuntimeLog artifacts. Deletion receipts retain the old artifact. Unchanged
outputs are not rewritten:mtime stays unchanged and changed=false is recorded,
so stale files do not appear freshly generated.

A failed or timed-out program can leave valid outputs;its actual status remains
failed/timeout. An output-validation failure returns output_rejected with its
reason and publishes no captured outputs. Do not infer success from exit_code
alone. Failure after a visible publication is indeterminate:reconcile the
original operation ID,do not resend. There is no atomic multi-file transaction.

Tests executed:19new boundary/CLI/artifact/lifecycle methods pass;102selected
client-side regressions pass with0failures/errors/skips. This is CPU/OS evidence,
not model qualification. L05 remains NOT_RUN pending the server regression set
and real Q8 CLI→HTTP→COW/GPU campaign. The protected report is produced by the
actual supplied program,never constructed by the operator.

The original test-first failures and subsequent fixes are retained:missing
output grant,missing CLI admission,unrooted artifact bytes,stale-output timestamp
refresh,and inaccessible parent incorrectly treated as deletion. Protected
workload tests and reference outputs were not changed.

## Executed L05 result

Q8/FP16 KV cross-host L05 passed the unchanged protected artifact checker: 11 model calls, 1,360 output tokens, 162.48 seconds. Client CPU selection: 102 passes; server selection: 137 passes; no failures/errors/skips in those selections. Server and native worker exited 0 and the owned SSH key was revoked.

Separate reporting limitation: the model claimed no file modes changed, although the supplied report program replaced its declared output with mode 0600 (previously 0644). Protected source modes remained unchanged. Preserve the functional pass and this reporting failure separately. A metadata-aware reporting example and fresh rerun remain pending; this is not release qualification.
