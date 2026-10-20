# Scoped permission changes

The CLI can grant mode_paths and a mode_mask (an integer bit mask in0..511).
Both must be explicit and nonempty together. Each mode path also requires read
permission. No existing grant gains this capability by default. Edit permission
does not imply chmod permission,and chmod permission does not imply editing.

The model requests set_mode with a relative path and four octal digits such as
0740. Only basic rwx bits are accepted;no setuid,setgid or sticky bits. The
desired/current difference must fit the host mask. For owner-execute-only work
use mask64(decimal),equivalent to0o100. Other existing bits must remain equal.

A visible read binds the content preimage. PLAN binds current content and mode;
ACT rechecks dependencies and uses an anchored no-follow descriptor. Symlinks,
hardlinks,stale plans and out-of-mask changes fail. Contents are checked unchanged
on that same descriptor before/after fchmod and fsync. The receipt reports actual
before/after modes and content hash. A post-effect receipt failure is indeterminate;
reconcile the original operation ID,do not blindly repeat it.

The executor lock serializes trusted operations. This does not defend against a
separate malicious same-UID process mutating the workspace between system calls.
Untrusted commands retain their existing OS isolation;this capability does not
make their file projection writable or grant broader host access.

This is a BranchWrite host-tool feature. It changes no COW snapshot representation
and requires no GPU model modification. Real-model L04 qualification follows the
CPU boundary/CLI/grammar checks;CPU tests alone are not that qualification.

File completion expectations may include an optional four-digit mode alongside
path and sha256. Such a policy checks actual bytes,visible readback and current
permissions before finish. Byte-only policy identities/results remain unchanged.
Mode-aware policies receive an explicit v2 identity.

Terminal projections now preserve basic file modes and include them in input
receipts. The read-only namespace mount remains mandatory. Previously every
projected file became0400,which hid correct execute-bit changes. The real
regression observes640→740,denied→successful direct execution,and rejects a
write even when a copied mode contains owner-write. No live run is mutated
across this change;fresh attempt identities and worlds are required.

Executed on2026-10-19:118selected CPU regressions passed(no skips). The real
Q8/FP16-KV CLI49→HTTP→GPU60 L04 trial passed with no additional task example,
7model calls,1309output tokens and108.392s whole positive CLI. The original
L04 checker,real126→0 execution results and640→740 modes agreed. Initial
0400-projection attempt was stopped and retained as a harness defect.
