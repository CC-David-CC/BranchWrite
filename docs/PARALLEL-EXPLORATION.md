# Two checked approaches

New coding launches can opt in to two independently writable project copies:

```sh
branchwrite code ./project --task-file task.txt --project-files \
  --test-command 'python3 -m unittest discover -s tests' --explore
```

Provide `--approach 'instruction'` exactly twice to choose the directions.
`--select-candidate verified-first` chooses the first declared passing candidate
after both settle. Choose `first` or `second` to require that specific candidate
to pass. There is no model-selected or completion-order tie breaker. If neither
candidate passes, neither is selected. Read-only launches and shared remote
mutation capabilities are not admitted for this option.

The interpreter owns one ledger, forks the same prepared COW source for each
arm, steps both scopes and collects worker observations. Each arm has a separate
Executor world. A two-slot host dispatcher can overlap model requests and tool
execution; COW chooses physical inference placement. The same workflow can use
a one-worker COW server, which queues its inference requests, or several COW
workers. This feature does not federate separate COW HTTP endpoints.

New exploration launches freeze eight tool-decision iterations per candidate,
512 tokens per model request, eight requests and 4,096 output tokens per decision,
and aggregate limits of 128 requests and 65,536 output tokens. The interpreter
checks conservative upper bounds before admission. Ordinary launches retain
their existing program and budgets. Resume keeps the admitted configuration.

Verification uses actual check receipts and the candidate's current inventory;
one candidate's check cannot certify the other. Review and export resolve the
recorded selection to that owned workspace. The source project stays unchanged.
Post-check file changes prevent selection or export. A passing command verifies
its stated checks, not arbitrary semantic task quality.

Workers never mutate the workflow ledger. Original dispatched operation IDs
and durable receipts remain recovery authority; a lost acknowledgment does not
authorize a fresh dispatch. Exiting the interpreter drains already-dispatched
effects before closing its ledger. This is bounded concurrency, not immediate
preemption of an arbitrary running tool. Tool timeouts remain in effect.

CPU boundary evidence is in `validation/parallel-exploration-20261022.md`.
Autonomous Wen task quality and end-to-end GPU scheduling measurements are
separate qualification steps.
