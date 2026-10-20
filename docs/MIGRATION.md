# Migration from v0.2.0 / contract v0.5

This is a replacement design, not a compatibility layer around a flat seven-verb runner.
The original 211 case IDs and original archive remain traceable. Active cases retain
behavioral obligations while explicitly migrating old language/JSON shape requirements.
`acceptance/migration.tsv` identifies altered fields and the original per-case digest.
Do not execute the source archive as part of the new product or support both protocols.

| Old assumption | Replacement | Consequence |
|---|---|---|
| Seven verbs are the executable kernel. | Fourteen explicit operations, one typed computation contract. | Historical programs must be deliberately rewritten, not guessed at runtime. |
| ASK covers every generation phase. | EXPAND and CONTINUE differ by actual native turn state. | Active partials preserve parser/sampler progress; no accidental new user turn. |
| CHECK both reasons and adopts. | VERIFY/CHALLENGE/COMPARE/SELECT expose provenance and decision boundaries. | Criticism cannot impersonate observed evidence. |
| DO executes or publishes. | ACT executes bounded effects; COMMIT publishes a verified result. | No generated finish message becomes publication authority. |
| JSON-shaped model decisions and schema templates. | Strict `.bw` and canonical type-derived grammar/validation. | No JSON mode, tool envelope or repair feature needed. |
| Global latest state indicates plan freshness. | Exact relevant dependency projection. | One sibling's unrelated progress does not stale another's plan. |
| Branch means context plus an output. | Context, grammar, decoder, world and typed-frame ownership are explicit. | Native snapshot qualification must include non-KV state. |
| Forks provide diversity by themselves. | Exact clone versus recorded seed/profile/task changes. | Greedy duplicate work is not counted as exploration gain. |
| Add one sampler after another as a dependency ladder. | Shared state/transaction contract, then independent components. | Adaptive-P need not wait for Mirostat's algorithm. |
| Token-only accept/replay restores all state. | Stateful selection proposals are transactional and recoverable. | Probability feedback and consumed randomness cannot be silently dropped. |
| Every parallel join publishes. | Join output contract decides whether publication is required. | Planning/verified artifact groups can return without external publication. |

## Retained without weakening

Native COW rather than stateless conversation replay; one local interpreter; exact original
request recovery; typed nested call/return; active-frame retirement without history deletion;
parent locals, epochs and named parallel slots; source-bound annotations and templates;
real OS enforcement; private protected tests; one/two-service role semantics; budgets;
unknown-effect preservation; guarded Git publication; independent platform qualification.

## No-JSON scope

Model generation and BW control/return syntax do not use JSON. Active handoff files are
TOML, TSV, `.bw`, GBNF and Markdown; exact artifacts remain bytes. Historical files are
unchanged provenance. The old native CLI described JSON receipts/internal envelopes;
this is not evidence that the model supports structured JSON generation. Preserve the
actual native transport contract instead of designing a replacement transport by assumption.

The canonical reference codec is a small non-JSON typed framing oracle. Production can
reuse a sound existing canonical binary codec only after explicitly binding the same
round-trip/type/recovery guarantees; do not add duplicate semantic state representations.

## Corrections to earlier sampler guidance

Typical can discard the maximum-probability token. It is therefore not safe to assert that
Typical + greedy is always identical to greedy. Positive temperature alone does preserve
argmax; the result of a filter may not. Independent RNG objects initialized to the same
state preserve replay, not diverse samples. Native sampler clone support does not by itself
prove restart serialization. Some selectors update during sampling, not token acceptance;
state replay must account for that. Adaptive-P is the intended name, not “Adaptive 2”.

The earlier suggested Top-K/Top-P/Min-P stack is retained only as a named comparison
configuration. The minimal baseline avoids redundant filters until measured benefit exists.
