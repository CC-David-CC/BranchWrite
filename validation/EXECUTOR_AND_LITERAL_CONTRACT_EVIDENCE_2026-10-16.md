# Bounded executor and literal-text contract evidence

This note records implementation checks for the first BranchWrite execution
boundary and the host-owned literal result contract. It is not a product
acceptance result and does not change the acceptance catalogue.

## Registered executor

`branchwrite.execution.Executor` copies a regular-file source tree into an
owned workspace, rejects symlinks and `.git` administration data, and bounds
the copied tree by 64 MiB, 20,000 entries, and 64 directory levels. Its only
process operation is fixed `unittest` discovery in bubblewrap. The test process
gets a read-only workspace, isolated namespaces, no host home or network mount,
a fresh 64 MiB `/tmp`, bounded output capture and a deadline. File replacement
requires an exact host grant, SHA-256 preimage and one exact byte match.

Resource limits are scoped: `prlimit` CPU/address-space/file-size limits apply
per process, not as aggregate process-tree memory limits. This implementation
does not claim universal containment for arbitrary code.

The llm-60 run at
`/home/dflanag3/spatial-artifacts/branchwrite-exec-20261016-v1/green-run-v6`
passed 7 executor tests with command and wrapper exits 0/0. The tests cover a
real failing test followed by an exact permitted edit and passing test, denied
and stale edits, protected tests and an unmounted host sentinel, timeout, absent
test grant, symlink rejection, and a colliding run-directory owner sentinel.
The initial missing-module RED remains at `red-run`; sandbox setup failures and
their corrections remain in the versioned run directories.

## Literal text result

`LiteralContract(name, max_bytes, max_lines, max_line_bytes)` accepts only the
framed `TEXT <name>` form. Each body line starts with one `|`; parsing removes
that prefix and preserves the line's LF. A prefixed empty line is a blank source
line, while no body lines represent an empty payload. Thus this subset returns
LF-terminated UTF-8 source text; non-LF-terminated byte artifacts need a
separate artifact contract. `END`, `ACT`, and tool-looking strings remain data
when they occur on prefixed lines. The parser rejects malformed framing, CR,
NUL, invalid Unicode, and configured byte/line overflows without repair. The
generated GBNF bounds framing, line count, and per-line character count; the
host parser enforces UTF-8 byte bounds. The grammar does not contain a task
solution.

On llm-60, the focused parser test run `contract-green-run-v1` passed 6/6
(command/wrapper 0/0). The broader `unittest discover -s tests` run
`contract-full-run-v3` passed 250 tests (0/0). Both used the pinned llguidance
1.9.1 dependency. The final handoff verifier run `contract-handoff-v7` reported
`HANDOFF_VALID: 339 not-run product cases; 40 planned tickets; 77 hashed
payload files` (0/0). Its AST policy rejects any `json` or `pickle` import in
the active tree; these additions use neither.

The actual pilot grammar bounds were then instantiated through the COW
`GrammarEngine` with `Tokenizer.from_gguf` on the Q4 tokenizer (CPU metadata
only; no model load or inference). The external probe run
`contract-bound-compile-v1/run-v9` passed 0/0. It compiled the replacement
contract at 32,768 UTF-8 bytes, 256 lines, and 4,096 bytes per line in 0.661 s,
and the report contract at 8,192 bytes, 64 lines, and 4,096 bytes per line in
0.500 s. Grammar hashes were respectively
`cc006e4966f9050cf67576a4a54e06987297996e06fe8a749b24c2e1e48c56b2` and
`04715507fb900151aca56c907e997cec7cb858a4afdfd63b9e5f717bcf7ac84e`.
The probe script is retained outside the product payload at
`/home/dflanag3/spatial-artifacts/branchwrite-exec-20261016-v1/contract-bound-compile-v1/compile_literal_bounds_probe_v5.py`
(SHA-256 `b8183ed4046130bd89a7a4fa5ee1ffe8b621c95ed2055cb99d28fd36f3cca0d3`).
It loaded profile
`/home/dflanag3/spatial-artifacts/grammar-first-20261016-v1/profile-candidate-v2/profile.json`
(SHA-256 `bd02b4af425b44291054ae07fb20ea28f63d8f6dc7a4aff52541e6fcc7ce2410`)
and imported `grammar_first.py` from the frozen CPU source (SHA-256
`192a3b53046969e3eef8410d3ca3e30d9e86597e32437abfffb6fb34ec8ae956`).

The focused run receipts are under
`/home/dflanag3/spatial-artifacts/branchwrite-exec-20261016-v1/contract-green-run-v1`;
the broad suite is under `contract-full-run-v3`; handoff verification is under
`contract-handoff-v7`; and actual-bound compilation is under
`contract-bound-compile-v1/run-v9`. Setup/invocation failures are retained in
the sibling versioned run directories, including the initial command that
attempted to execute the non-executable wrapper directly, missing import roots,
and an unknown matcher-state label. No GPU or model inference was involved.
