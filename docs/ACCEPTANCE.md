# Acceptance and evidence

The active catalogue has **339 planned product cases**: the prior **211** plus
**128 new v0.6 cases**, assigned to **40** dependency-bound implementation tickets.
Every product case is `not_run` in this handoff. Offline test results appear separately.

Case IDs from v0.2.0 remain stable. `migration.tsv` binds each source record digest and
marks language/encoding edits. The original archive contains exact old records, vectors,
fixtures and utilities. The migration changes the model/control representation, not the
required semantic behavior, recovery discrimination or protected acceptance outcomes.
R35 must re-express any old fixture metadata whose path changed before declaring a live
campaign ready. No fixture claim is silently inherited from a missing file.

A product result record must include case ID, source/spec/config hash, outcome, command,
start/end boundary, environment/model/backend where relevant, raw witness references,
expected oracle, observed result and unresolved resource identities. Use typed non-JSON
records in production and TOML/TSV exports. Keep failed/unknown/not-run distinct.

Per-boundary evidence is mandatory: native tokens/logits for sampler law; native matcher
state for grammar progress; real processes and barriers for concurrency; actual denied
syscalls/effects for isolation; actual publication target state for COMMIT; crash/restart
with the original native operation for recovery. Status text is not any of these witnesses.

The reference suite cannot pass product cases. Its deliberate finite matcher and synthetic
RNG do not stand in for native serialization. Target-only and MTP qualification are separate.
Missing advanced controls need not block a working explicitly limited baseline release;
they must block any claim that those advanced controls are enabled and certified.
