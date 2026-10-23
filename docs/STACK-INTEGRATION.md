# BW, COW and native execution

BW owns tasks, tool grants, verification and one workflow ledger. COW owns
canonical context/controllers, branch publication, checkpoints, GPU scheduling
and cache transfers. Strata and the dense native adapters execute model work.
Cache location and inference placement grant no additional tool authority.

BW now observes authenticated `GET /cow/capabilities` at connection and workflow
admission, including unfinished resume. Completed work replays its original
ledger offline. Discovery checks the pinned model/execution identities and
the required text and inline-grammar features. A present malformed, incompatible
or disabled capability is an error. Only an HTTP 404 permits discovery through
the older `/cow/info` contract; connection failures are not legacy detection.
The observation introduces no second transcript, ledger or dispatch authority.

COW's inventory, transfer-cost scheduler, configured cache peers, independent GPU
roles and optional tokenizer are server settings. BW's existing requests use
them without selecting GPUs or copying cache bytes itself. Ordinary compatible
CLI clients and BW share COW's serving authority; BW retains its additional task,
tool, verification and continuation semantics.

See the COW repository's
[stack capability documentation](https://github.com/CC-David-CC/Private_Context_COW/blob/main/docs/STACK-CAPABILITIES.md)
and [cache controls](https://github.com/CC-David-CC/Private_Context_COW/blob/main/docs/CACHE-FABRIC.md)
for switches, bounds and measured scope. Grouped native checkpoint restore,
cross-profile cache portability and remote inference dispatch are not enabled by
capability discovery. The independently selectable features remain off by default.

## Executed checks

BW revision `211717d` passed 158 focused capability/connection, receipt, retry,
lost-acknowledgment, stream, exploration, review/export and CLI workflow tests
against the actual COW CPU HTTP/CLI stack. That selection exposed and fixed an
unnecessary server-discovery call during completed offline replay. The original
test now closes COW's listener before reopening the finished result. Test
fixtures also received consistent model IDs and explicit discovery metadata;
production compatibility checks remain strict.

After the fix, six retained native workflows (Wen/Qwen tokenizer off/on and
Wen two-approach off/on) reopened with their HTTP listeners stopped. All returned
identical result objects and unchanged ledger/journal bytes, without loading a
model. This validates completed-result replay, not recovery of unfinished work.

The native workflow runs used BW `8b821b0` and COW runtime `10964d0`.
Wen 1.1 and Qwen Flash Q4 completed bounded read/edit/test/finish workflows with
COW's optional inventory/scheduling/tokenizer features disabled and enabled.
The tests paused and resumed admitted work, then reopened the completed ledger:
the final replay did not change COW branch heads. Source projects and frozen
launch configurations remained unchanged. Native servers shut down cleanly and
removed their ephemeral sessions.

A separate A100 run completed the same BW workflow with root prefill on GPU 3
and continuations on GPU 0. LAN cache storage round-trips through llm-49, llm-79
and r730 preserved full native responses when restored on llm-60. These are
bounded integration checks, not proof of arbitrary task quality, hardware
portability or a throughput improvement. The answer-free receipt lives with COW
under `experimental/branching_context/evidence/STACK-UNIFICATION-FINAL-20261023.json`.

Wen also completed a two-approach coding workflow in both modes. Each isolated
candidate passed its own tests; declaration-order `verified-first` selected the
first. Their different workspace inventories were preserved, completed replay
left heads unchanged, no operation journal remained pending and both servers
cleaned up. The test supplied 512 interpreter steps, below the CLI's default
1,024; its initial 128-step test-driver allowance paused before the two scopes
could finish. Frozen model/tool/token budgets were unchanged.

The earlier interrupted two-approach integration also received fixes: a branch
waits for its own direct scope to close after a nested repeat, progress notices
follow actual dispatch/completion, and the overlap test waits for both workers.
See [PARALLEL-EXPLORATION.md](PARALLEL-EXPLORATION.md) and its validation record.
