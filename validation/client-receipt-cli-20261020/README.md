# BranchWrite client receipt CLI - bounded evidence

Source commit: `92a68349bdbac5e2e2d58f11a358a91aad4b4f62`
Private branch: `feat/explicit-model-reconciliation-20261019`

The user-facing client now exposes the exact saved answer for an operation through:

~~~bash
branchwrite receipt STATE --operation-id ORIGINAL_ID
branchwrite receipt STATE --operation-id ORIGINAL_ID --show-answer
branchwrite receipt STATE --operation-id ORIGINAL_ID --json
~~~

The command reads the local operation journal and validates the retained COW
receipt. It does not contact the server. It withholds answer text by default.
An unresolved operation remains unresolved and must keep its original ID.
`status` prints the receipt command next to model-recovery guidance.
`reconcile` and `resume` continue to use that original operation.

Executed evidence:

- 84 focused BranchWrite tests passed, zero failures/skips.
- 8 Context COW HTTP integration tests passed, zero failures/skips.
- Client processes were killed with exit codes 78 and 79 at two durable-publication
  boundaries. The answer receipt was inspected/reconciled while the HTTP service
  was stopped and the API key absent. After the service returned, resume consumed
  the same receipt without extra fake-backend forward work or branch movement.
- Installed private wheel dev31 and ran CLI help, receipt help and doctor.
- llm-60 GPU0 remained idle; inference used a deterministic CPU fake.

This is a bounded client receipt milestone, not full server restart recovery.
The Context COW coordinator, Store and fake native backend remained alive while
the HTTP service was stopped and recreated. No GPU/model quality or throughput,
power-loss, full native process restart, tool-effect recovery, or broad coding
reliability claim follows. A durable answer receipt proves saved output, not GPU
residency or that KV state remains available.

See `result.json` and the raw logs in this directory. The package wheel and
install smoke files are under
`/home/dflanag3/spatial-artifacts/branchwrite-dev31-package-20261020-v1/`.
