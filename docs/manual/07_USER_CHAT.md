# Talk to the model through one saved conversation

This is the small user-facing conversation command for the private prototype. It
uses one COW branch named "user-conversation" as the current conversation. COW
stores the actual messages and model context. A coding run starts from an exact
saved point and gets its own branch, so later user updates do not appear halfway
through work already underway.

## Simple interactive entry

Run `branchwrite talk`, or type `/chat` at the ordinary startup prompt. Type a
question, then use `/code YOUR TASK` to start the existing coding workflow from
the conversation's exact committed tip. No project files are read in talk mode.
`/exit` prints the exact resume command. An unfinished or unresolved answer must
be continued or reconciled before its tip becomes a coding source.

This uses the same `chat` operations documented below; it adds no transcript
store. The first terminal loop is synchronous. Queuing or stop-and-amend while
an answer is running still uses the commands below from another terminal.

## Who owns what

- **BranchWrite** is the client program and coding workflow. The command
  "branchwrite chat" sends a user message, shows the reply, and keeps the local
  operation receipt needed to recover after a lost acknowledgment.
  "branchwrite code" starts a separate, permission-bounded coding run from a
  chosen saved branch.
- **Context COW's HTTP service** accepts the client's requests, applies the
  conversation operations, and publishes durable results.
- **Context COW's canonical store and context-time-travel core** own the
  immutable message history, branch references, controller state and optional
  native checkpoints. COW is the authority for the current conversation tip.
- **The inference backend** performs prefill and generation. A streamed token is
  provisional until COW publishes the completed receipt.

BranchWrite does not keep a second conversation transcript. Its private local
state contains connection/profile identities, the current branch/tip, an
in-progress request when one needs recovery, and the client's exact operation
journal. The journal preserves original request bytes and completed receipts;
COW remains the canonical conversation history.

## Start a conversation

Use the client and server setup guides first. On the Linux machine where
BranchWrite is installed, create a private state folder and start a conversation:

~~~bash
export BW_COW_API_KEY='your server key'
branchwrite chat init \
  --connection "$HOME/.config/branchwrite/cow-connection.json" \
  --state "$HOME/.local/state/branchwrite/user-chat" \
  --branch user-conversation \
  --title "My current work"
~~~

The connection JSON contains these fields:

~~~json
{
  "endpoint_url": "http://127.0.0.1:8080",
  "endpoint_pin": "my-pinned-server",
  "model_contract_id": "my-model",
  "execution_profile_id": "my-execution-profile",
  "eos_tokens": [2]
}
~~~

Use the actual identities and EOS token IDs from your server configuration.
Keep the API key in the environment or your approved secret manager, not in this
JSON file. "init" creates a COW namespace; the branch history is created with
your first message.

## Talk, continue, and inspect

~~~bash
branchwrite chat send "$HOME/.local/state/branchwrite/user-chat" \
  --message "Help me understand the current project."
~~~

You can use "--message-file FILE" for a long message or exact Unicode and newline
tests. Assistant text appears as it streams. BranchWrite labels it provisional
until the COW completion receipt confirms that the answer was durably published.
If the process stops or the network fails during a reply, the state stays pending;
do not start a different operation.

If the assistant stopped at its token limit and COW says the controller remains
active, continue the same answer:

~~~bash
branchwrite chat continue "$HOME/.local/state/branchwrite/user-chat" --max-tokens 4096
~~~

Only after the assistant turn is complete can a queued user message run.
To save a follow-up while a reply is in flight, use another terminal and run:

~~~bash
branchwrite chat queue "$HOME/.local/state/branchwrite/user-chat" \
  --message "Also check the log from this morning."
~~~

The queue belongs to BranchWrite, not the server. It writes a private,
checksummed FIFO in this chat's local state directory before waiting behind the
active chat request. When that answer completes, BranchWrite takes the messages
already in the queue, joins them in arrival order with a blank line, and sends
one combined user turn to COW. For example, "Also check the title" followed by
"Change the background to blue" becomes one request containing both instructions;
they are not two separate model turns. Follow-ups that arrive after that combined
request has started stay queued for the next turn. This also applies when the
follow-ups describe a correction, a configuration change, or a change in the
project goal: their text reaches the agent together, while explicit CLI generation
options remain request settings. Separate machines or separate state directories
have separate queues. If the assistant reaches its token limit first, queued
messages wait until chat continue finishes the turn; chat drain can explicitly
retry a saved queue after a client restart.

If the client dies while the previous answer is running, restart with the same
state folder and run chat reconcile first. Once COW confirms the original
operation, BranchWrite completes the saved answer and submits the still-local
queued bundle once. Every queued item keeps its local operation ID; the combined
COW operation gets a deterministic ID bound to the ordered items and their exact
text. BranchWrite removes the items only after the combined turn is durably
confirmed, including after a restart. You may set a queue-item ID yourself;
otherwise BranchWrite creates one. IDs may be up to 128 ASCII bytes.

## Stop an answer and add missing information

If you notice a missing detail while a new user-turn answer is still running,
open another terminal and run:

~~~bash
branchwrite chat stop-add "$HOME/.local/state/branchwrite/user-chat" \
  --message "The test must preserve the final newline."
~~~

COW receives a cancel request for the exact in-flight operation. BranchWrite
waits to learn whether cancellation or durable completion won. If cancellation
wins, it retries with the original user message and the added detail together,
using a new operation ID. If the first answer had not yet been published, it
keeps the old attempt as a separate COW branch and makes the amended branch
current. If publication won the race, that answer is kept and the new detail is
sent as the next user turn. If COW cannot prove either result, BranchWrite keeps
the request pending and asks you to reconcile it.

Streamed text from the stopped attempt was provisional and is not saved as an
answer. This first implementation supports stopping a new user-turn answer;
a token-limited continuation must be completed before adding another user turn.

~~~bash
branchwrite chat history "$HOME/.local/state/branchwrite/user-chat"
branchwrite chat status "$HOME/.local/state/branchwrite/user-chat" --json
~~~

History comes from COW. Status shows the current branch and any operation waiting
for recovery. "chat.json" is a small private state record, not a message database.

## Recover after a stopped client

If BranchWrite says the operation is unresolved, keep using the same state folder.
Reconcile the pending operation before sending anything else:

~~~bash
branchwrite chat reconcile "$HOME/.local/state/branchwrite/user-chat"
~~~

To name the exact operation, inspect the status first and pass its ID:

~~~bash
branchwrite chat status "$HOME/.local/state/branchwrite/user-chat" --json
branchwrite chat reconcile "$HOME/.local/state/branchwrite/user-chat" --operation-id bwchat-example
~~~

Reconciliation asks COW for the outcome of the original operation and recovers its
exact saved answer. It does not invent a new operation or silently generate a
replacement. If no durable result can be proven, the request remains pending and
the error is shown.

## Start independent coding work

A coding task should use its own BranchWrite state and branch, based on a specific
saved COW tip. The shared conversation may continue receiving your latest updates;
the worker keeps the source point it started from. Use the documented coding
launcher and its explicit file grants, test commands and review/export steps.
A worker branch is not automatically merged into the conversation or your project.

## Current limits

This is an early CLI path, not a multi-user chat application. CPU-only
CLI-to-HTTP-to-COW-store tests now cover current-tip updates, worker-branch
isolation, provisional streaming, recovery after client death, 128-byte names,
FIFO queueing while a request is active, and stop-add both after a completed
turn and before the first answer. The stop tests use the real COW HTTP handler,
coordinator and Store with a synthetic model; they do not qualify GPU
cancellation or native-state recovery. A token-limited continuation must finish
before a new user turn can be added. The queue command persists its message
before waiting for the active chat lock, then sends after the assistant is
ready. Public service, chat attachments and a graphical interface remain
unqualified.
