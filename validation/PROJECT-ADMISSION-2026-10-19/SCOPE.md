# Metadata-free project admission

A normal Git checkout and a linked-worktree .git file previously stopped the
public code command before HTTP. Both distinguishing cases failed first.

The coding launcher now pins source_policy=metadata-free-project-v1 in its
existing saved host configuration. The one existing Executor creates the owned
workspace, excluding exact .git entries at every directory level without reading
or following them. Its default source admission still rejects Git administration.
Project grants cannot name Git administration. Other symlinks, special files,
copy bounds and race checks remain unchanged. Original source/admin are untouched.
No Git executable, second workflow ledger or model-state representation was added.

Five focused methods pass, including real CLI subprocesses reaching a deliberately
unauthorized HTTP server with clean workspace copies, directory/file/symlink Git
metadata, retained ordinary .github files and rejection of non-Git symlinks.
Thirteen launcher regression methods pass. No autonomous dev3 GPU result yet.
Dev3 separates the changed executor/source-policy identity from dev2's live trial.

Limits: this copies bounded regular project inputs, not a Git-index selection.
.gitignore filtering and large dependency-tree discovery remain future work;
links outside excluded metadata still fail closed. Publication back into a live
checkout is not implemented here. The source remains untouched.

Broader suite initially failed1/152: wrong-host admission created local state before rejection. Fixed actual host admission order without weakening the existing test; corrected152/152pass,0skips. Actual Git-created checkout and linked-worktree subcases pass. Fresh installed dev3 controls pass, wheel0a8aa263... . Autonomous dev3 remains unexecuted.
