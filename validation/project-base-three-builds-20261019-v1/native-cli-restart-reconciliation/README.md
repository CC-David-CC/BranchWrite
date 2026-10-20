Real Q8 restart and CLI reconciliation ? bounded PASS

Client: installed BranchWrite dev21 on llm-49. Server: Context COW source
d0610d46 on llm-60, actual Q8_0/FP16 native engine. New execution identity
aeb19be324aa1e2e4f19a61776b890c6c36bc225095582343dd0885e6d670bfb
binds the changed server source closure; no old-profile checkpoints imported.

A real request committed16 generated tokens. A test-only transport wrapper
discarded the received completion before client journal publication. The
producer client then exited, followed by HTTP server734355 and native734361.
New HTTP server734970/native734976 opened the same store/endpoint. A new client
process invoked the ordinary installed branchwrite reconcile command using the
original ID. Tokens/text/snapshot/thinking and durable receipt matched exactly.
Timing and recovered flags are operational metadata, retained separately.

The workflow ledger did not change. Native trace remained byte-identical:
no native commands, forward tokens, prefill tokens, decode work or state-file
loads during reconciliation. This checks committed-output recovery, not restoring
computation for future generation; the latter has separate existing evidence.
No tool effect was dispatched by this deliberately minimal model-frame fixture.

See server/summary.json for setup failures and limits. Original rejected client
state remains in the Linux artifact directory and was never silently replayed.
The probe scripts retain their actual machine-specific paths/IDs; they are
executed evidence, not a reusable installer. The automated CPU integration
tests in tests/test_coding_reconciliation.py provide the regression harness.

Both owned server/native processes exited0. Owned SSH tunnel stopped, key
revoked, authorized_keys restored byte-exact, ephemeral credentials removed.
Chat remains OFF. No GitHub publication or cumulative gate qualification.
