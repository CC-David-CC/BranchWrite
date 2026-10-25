# How BW, PCC/COW and S³ share execution

BW's model calls use its existing COW client, native receipts and workflow
ledger. COW's coordinator dispatches greedy requests to
`BranchingModel.run_greedy_request`; dense MiniCPM then uses the canonical
consumed sampled/state request. Contexts, controllers, forks and native
checkpoint restoration belong to PCC/COW.

S³ now has an optional direct-answer evaluation adapter that calls this same
COW request method. It no longer needs to use its independent fresh-context
correctness oracle as the primary execution path for every generated token.
This shares the engine used by BW without making a frozen arithmetic benchmark
start a BW task ledger or granting a test case tool permissions.

The ownership stays clear: S³ defines and grades skills; BW executes tasks and
records lessons; PCC/COW runs inference and native backprop and owns immutable
candidate/context identities. A newly trained candidate gets a new model-bound
context. It must never inherit the old model's KV materialization.

This connection is opt-in and initially tested on dense MiniCPM F32 with a
512-token context. Its numerical probes are not evidence that BW's shell tasks,
other harnesses or the entire learning loop are all solved. Full behavioral
and timing comparisons retain separate runtime identities and original failures.

See [S³'s execution and scoring guide](https://github.com/CC-David-CC/sss/blob/feat/minicpm-baseline-20261024/docs/COW-EVALUATION.md)
and [PCC's shared request implementation](https://github.com/CC-David-CC/Private_Context_COW/blob/feat/native-learning-curves-20261024/docs/COW-EVALUATION.md).
