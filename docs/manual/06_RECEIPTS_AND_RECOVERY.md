# Inspect and recover a saved model answer

BranchWrite gives each model request an operation ID. Keep that ID when you
restart or retry. It lets the client find the exact answer already saved for
that request instead of asking the model to do the work again.

## Look at a saved answer receipt

After a run reports a pending model operation, copy the original operation ID
from `branchwrite status`:

~~~bash
branchwrite status "$HOME/my-run"
~~~

Then inspect the local receipt. This command is read-only and does not contact
the COW server:

~~~bash
branchwrite receipt "$HOME/my-run" --operation-id bwnative-EXAMPLE
~~~

By default, it prints the COW branch and revision, saved snapshot, model and
execution profile, output token count, and answer hash. It does not print the
answer itself. To display the exact saved answer:

~~~bash
branchwrite receipt "$HOME/my-run" --operation-id bwnative-EXAMPLE --show-answer
~~~

For scripts, use `--json`. The JSON includes the answer text only when
`--show-answer` is also supplied.

A `DURABLE` receipt means the exact result and its COW receipt were retained
and validated locally. It does not mean the KV state is still in GPU memory,
and it does not prove that the server or native inference process survived a
restart. The receipt inspection itself does not run inference.

## See where the workflow stopped

To see the last committed workflow steps after reopening a run, use:

~~~bash
branchwrite status "$HOME/my-run" --tail 12
~~~

The tail is a bounded summary of committed ledger events: step names, frame IDs
and original operation IDs. It omits prompts, command output and artifact
contents. Use the specific receipt or review command when you need a saved
result. `--json` includes the same summaries under `recent_activity`; choose
`--tail 0` to hide them or a value through 64 to change the bound.

## Recover the interrupted workflow

If the workflow stopped after the model answer was saved but before the
workflow ledger recorded it, settle that same operation and continue:

~~~bash
branchwrite reconcile "$HOME/my-run" --operation-id bwnative-EXAMPLE
branchwrite resume "$HOME/my-run"
~~~

Do not invent a new operation ID for an uncertain request. If there is no
completed receipt, BranchWrite reports `UNRESOLVED`; inspect status and retain
the original ID. It must not silently regenerate an answer whose outcome is
unknown. Tool side effects have their own receipts and are not settled by model
receipt recovery.

Exit status from `receipt`:
- `0`: a completed, validated local receipt was found.
- `2`: the operation is missing or its receipt failed validation.
- `3`: the operation exists, but its durable outcome is unresolved.

The bounded recovery integration closes and recreates the full Context COW coordinator and Store before BranchWrite reads a saved source branch. It then kills the BranchWrite client after COW commits an answer but before the client publishes its local receipt, restarts the coordinator and Store again, and reconciles the same operation ID. The exact answer becomes inspectable offline, with zero additional forward-token work. The test also confirms the frozen project context contains the latest user-conversation tip.

The conversation tip stays separate from work tips: a worker branch forks from its exact snapshot and does not receive later user turns. The BranchWrite client/HTTP fixture also verifies that 128-byte ASCII COW branch and operation IDs pass end to end, while 129-byte IDs fail closed. COW grammar state names retain their separate 128-byte UTF-8 bound.

The user-facing BranchWrite chat command now keeps a "user-conversation" tip current, streams explicitly provisional text, and recovers a lost client acknowledgment through the same COW operation ID. Its work-fork test confirms a coding branch remains pinned to its original snapshot while the user conversation advances. See [Talk to the model](07_USER_CHAT.md).

These are deterministic CPU-fixture tests. They do not prove native KV restoration across a native process restart, GPU resume, power-loss durability, actual disk-full behavior, or cumulative G2 certification. The chat CLI is a bounded client slice; image inputs, rich interactive editing, multi-user behavior and a graphical conversation interface remain unqualified.
