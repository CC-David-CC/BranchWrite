# BranchWrite + Context COW process-restart check

The client loses its acknowledgment after Context COW commits an answer. The test kills the client before receipt journaling, SIGKILLs the COW HTTP service, starts a new service process against the same Store, then recovers the exact answer using the original operation ID. It checks that replay adds no forward work and a later turn computes only its new suffix and output.

This uses the real COW Store/coordinator/HTTP handler with a deterministic synthetic CPU model. It is not GPU inference, native KV restore, or power-loss qualification.

Five independent process-restart runs passed. The COW client suite passed 17 tests and the chat CLI/HTTP suite passed 6 tests: 28 passing test executions, 0 failures, 0 skips.

tests.log contains command output; result.json records counts, limitations, fingerprints, and hashes.
