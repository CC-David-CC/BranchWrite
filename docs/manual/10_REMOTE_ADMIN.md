# Work on a project and an authorized test machine

## For the person using BranchWrite

Start BranchWrite in your project folder, as usual. Your operator supplies the
COW server address, API key and any allowed remote machines. The key stays in
memory unless you explicitly choose to save it. Remote machines appear by short
names such as admin01. No remote target means no remote tools.

You can ask: "Make a little website about dogs. Keep a copy here and put it on
my test machine admin01. Check that it opens." BranchWrite can create and test
the local files, transfer their exact bytes and run allowed commands on that
machine. You can type a change while it works. Enter steers the current task;
Tab queues a later task. The existing server may wait for the current model step
before stopping. Review the final answer and actual page; a selected check passing
does not prove every aspect of an application is correct.

An upload is a private saved copy on the target, not an automatic deployment.
BranchWrite must separately put it into the service's folder and check the service.
If an operation says its result is unknown, retain its run and operation ID.
Do not start it again with a new ID just to clear the error.

## For the operator or an integrating agent

Keep SSH private keys and pinned known-host files outside the project. Supply a
private0600 JSON file through BW_REMOTE_TARGETS. Its schema is1 and its targets
mapping contains aliases. Each target requires canonical numeric host, integer
port, user, absolute identity_file and known_hosts_file references, timeout in
seconds (up to600), and exact owner_hostname of the client. The operator grants
access; model text cannot create targets or grant credentials. Only work mode
receives those capabilities. Plan/chat/aside modes do not.

The client is BranchWrite. Context COW is the inference server and owner of
saved model computation. The workflow harness checks their recorded outcomes
and actual OS/browser behavior. SSH helper receipts supplement the single BW
workflow ledger; they are not another scheduler or history representation.

remote_command(target,command) runs Bash on the selected target. It is a remote
administrative capability, not a promise that a working directory is containment.
check_remote(target,command) records one composite final check per target. Any
later remote operation makes that target's check stale. Local edits still require
current local checks; a remote check cannot cover local changes.

upload_file(target,path) reads only granted local files and freezes their exact
hash. Maximum file size is4MiB. Bytes use stdin, so quoting, binary data, Unicode
and final newlines are preserved. The returned receipt gives source_sha256,
source_bytes and remote_path. Use that actual path for publication; do not rewrite
file contents in generated shell text. Files are staged under the target user's
~/.branchwrite-uploads/<sha256>/<filename>, with read-only files and no symlink
following. Publish separately, verify the live file hash, then make the HTTP check.

One client host serializes target operations. Cross-host target coordination and
privileged/mixed-UID cancellation are not qualified. Upload staging has no automatic
expiry yet; it is separate from the COW RAM/disk checkpoint pools. Completed
transport receipts reconcile without execution. Missing or invalid acknowledgment
requires explicit inspection and never automatic resend.
