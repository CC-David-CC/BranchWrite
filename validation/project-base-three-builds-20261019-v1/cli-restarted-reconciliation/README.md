Restart reconciliation integration, 2026-10-19

The installed-style CLI is executed as a subprocess against actual COW HTTP.
The new tests reconstruct the HTTP server and coordinator on the same endpoint,
retaining only the Store, and recover the exact original generation. Assertions
cover unchanged workflow ledger, branch and model trace. Checkpoint-eviction
recovery is a canonical-output replay, not computation-state restoration.

The first run used the historical FlowModel without modern checkpoint receipt
annotations. It exposed a legacy compatibility limit (status and replay receipt
shape disagree, and legacy replay needs numerical files). Those failures remain
in the original before/after logs. New tests explicitly annotate Store.move in
their fixture to match modern native publication; existing fixtures/tests are
unchanged. Modern-before fails2/9; modern-after passes9/9. No tolerance or
numerical equation changed. This is not GPU or process-crash certification.

Reproduce on llm-60 with test-env-complete.json, replacing the old COW source
prefix with context-cow-persistent-operation-status-20261019 in PYTHONPATH:
python -B -m unittest test_coding_reconciliation -v
