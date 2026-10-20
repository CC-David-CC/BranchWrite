# Creating a file in a new directory

A host can grant one exact create path, such as notes/session/report.txt.
BranchWrite creates only that file and its necessary missing parent directories.
The model cannot create a sibling file or choose an arbitrary directory name.
Read, edit and browser operations never create missing directories.

The PLAN step only checks the requested path and bytes; it changes no files.
ACT checks the same dependencies again. It uses pinned directory descriptors
with no-follow opens, creates missing parents with mode0700, flushes each parent,
and publishes the file without replacing an existing name. Existing parent
permissions and neighboring files remain unchanged. Ancestor creation is bounded
by the existing source-tree depth limit of64.

If publication fails, the executor attempts to remove only its own new, still
identical, empty directories. A file that was already published is retained.
An error after ACT starts remains an indeterminate operation, including a lost
receipt: inspect the original operation and actual file instead of overwriting
it or inventing a retry ID. A process crash can leave empty parents. Parent
creation plus file publication is not one atomic filesystem transaction, and
these focused tests do not qualify crash recovery or power-loss behavior.

The existing execution-module and registry-module hashes bind frozen plans to
these semantics. No new model tool, grant field, workflow ledger, shell access,
COW state format or native inference operator is introduced. This host boundary
is still not containment against another hostile process with the same UID;
candidate commands retain the separate registered OS sandbox.

The initial L02 inspection found that the old create_file could not create its
missing parent and there was no directory-creation tool. That is an executor
capability gap, not a model-training failure. The protected L02 task and exact
reference bytes remain unchanged. Actual autonomous L02 validation is next.

Later real Q4 L02 evidence:the missing parent and exact file were created by the
actual client tool,read back and accepted in the DRY0 bounded run. Earlier
model proposals with wrong bytes remained failed;their file writes still matched
the proposed bytes. This qualifies neither arbitrary crash recovery nor model
reliability. See CURRENT_STATE.md for source/configuration and retained failures.
