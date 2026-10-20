# Scope of these executable oracles

These modules are small independent specifications used by the handoff test suite.
They are not a partial production interpreter to deploy or import into the target product.

- language: strict syntax and canonical rendering for the illustrative `.bw` subset.
- grammar: finite-language token-piece prefix masks and exact sibling progress.
- codec: canonical typed framing, preserving primitive type distinctions without JSON.
- sampling: synthetic Min-P, Typical, DynaTemp and XTC arithmetic and deterministic selection.
- state: immutable snapshots, exact clones, explicit seed splits and component-local draws.
- plans: exact dependency freshness and resource-conflict/eligibility predicates.
- returns: pure named-slot/epoch/result delivery and resumption event reduction.

No native GBNF engine, model, tokenizer, COW transport, native DRY/Mirostat/Adaptive-P,
OS containment, real scheduler overlap, filesystem power-loss durability or performance
claim is implemented here. The synthetic RNG is versioned separately and is not meant to
match any native library RNG sequence. Production acceptance remains not_run.
