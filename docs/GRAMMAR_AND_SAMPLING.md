# One decoder boundary, frozen per generation

## Law and state

A profile specifies a hard legality stage, ordered soft stages, exactly one terminal
selector, algorithm/version identities and state reset/continuation rules. Parameters alone
are not an identity: changing order changes the distribution. Never modify a live profile
because the task label changed. New profiles enter at an admitted generation boundary.

BW's proposed certified law begins with grammar/suppression/stop legality, then stages
operate only on surviving candidates. No tail filter or repetition handler can unmask a
forbidden token. Every local filter retains at least one candidate from its own input.
If the hard legal set was empty, fail. Do not revive globally forbidden candidates as a
“min_keep” workaround. Grammar only restricts syntax; semantic admission stays mandatory.

## Profiles

| Name | Proposed order after hard legality | Purpose |
|---|---|---|
| control | greedy | Short typed choices and deterministic control records. |
| explore | DRY → fixed T → Min-P → random distribution | Existing general exploration baseline. |
| typical | fixed T → Typical → random distribution | Isolated test of typicality filtering. |
| dynamic | DRY → DynaTemp → Min-P → random distribution | Entropy-responsive open content. |
| xtc | fixed T → Min-P → XTC → random distribution | Deliberate proposal diversity. |
| mirostat | fixed T → Mirostat 2 | Feedback-controlled alternative selector. |
| adaptive | mild Min-P → Adaptive-P | Alternative probability-target selector. |

This is BW's explicit proposed order, not a claim about any native backend's defaults.
`configs/profiles.toml` carries benchmark starting parameters, not tuned universal settings.
The prior DRY/T=.7/K=60/P=.95/MinP=.05 combination is an additional recorded comparison,
not the minimal default. Selectors that are unavailable remain unavailable.

For control records, do not turn on XTC or heavy DRY merely because those samplers exist.
Forced keywords, delimiters and repeated identifiers are legitimate. An open-text generation
can have its own pinned grammar/profile within the same invocation kernel. Structural
safety never depends on temperature or a probability threshold.

## Algorithm expectations

Min-P retains `p_i >= min_p * max(p)` at the stage where it runs. It usually cannot alter
argmax when followed immediately by greedy; it changes a stochastic candidate set.
Typical computes entropy H, ranks by `abs(-log(p_i)-H)` and retains mass up to its threshold
with an explicit tie/minimum rule. The modal token can be removed.

DynaTemp maps normalized entropy to a bounded temperature; its input candidate population
must be defined. BW computes it after hard legality and any prior score transform, before
soft filtering in the dynamic profile. No entropy divide-by-zero for a singleton; no
NaN/non-finite temperature. It does not estimate whether a predicted answer is true.

XTC consumes randomness to decide whether to exclude leading high-probability choices.
Its trigger, threshold comparison, keep-floor and tie handling must be pinned. With zero
activation probability it is a no-op and consumes no random draw in the reference law.
That draw policy is part of reproducibility, not an incidental optimization.

Mirostat 2 regulates a surprisal statistic; Adaptive-P tracks a selected-token-probability
statistic with feedback. Their statistic's reference distribution, update timing, clamp,
initialization, reset and source version must be pinned. Do not implement a vague
“Adaptive 2” approximation or call any temperature feedback loop Mirostat. Unattainable
targets under forced syntax are expected conditions, not convergence-test failures.

## Atomic token transition

Conceptually `propose(snapshot, logits)` returns a token, provisional next decoder state
and a trace. The accepted state becomes current once; rejected proposals do not. A native
sampler may internally mutate during apply, so adaptation must occur on a staged clone or
qualified checkpoint. Snapshot/restore must include every random draw, feedback update,
DRY history, matcher state, output turn/stop state and any pending draft state.

Do not reconstruct a feedback sampler by calling accept(token) alone when its update used
probabilities. Do not send a second duplicate request to find out what the first sampled.
Persist native receipts and exact state references. A seed by itself is not a checkpoint.

## Forks

An exact clone shares immutable input state but copies future progress logically. With
identical choices, logits and RNG state, both branches may be identical. For diverse
exploration, record a seed split by run/attempt/child/component identity, or a changed
prompt/profile. A duplicate greedy fork is a useful parity test but not useful best-of-N.

A mid-output fork copies grammar progress; a new output contract starts a new matcher.
Test both separately. Branch A reaching END cannot move Branch B's grammar state to END.
Resource interleaving cannot change RNG consumption in B. Shared compilation caches need
immutable entries or thread-safe construction, not shared live matcher stacks.

## What the offline code does not claim

It exercises Min-P/Typical/DynaTemp/XTC arithmetic on finite synthetic candidates and tests
snapshots containing DRY/Mirostat/Adaptive-P state. It does not implement or certify native
DRY, Mirostat 2 or Adaptive-P algorithms, full GBNF, GPU distribution parity, MTP or model
quality. Product cases require exact source-bound golden vectors and actual native runs.
