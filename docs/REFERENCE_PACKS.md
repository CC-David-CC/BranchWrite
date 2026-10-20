# Rebuildable reference and example packs

A reference pack is a box of selected text that BranchWrite can read before it
starts work. Put worked examples in one section and recorded facts about your
systems in another. Change a source file and build again: the new box gets a new
identity, and the old box stays available. Recorded facts can be wrong or old;
the model must still check the real system with its permitted tools.

This pack is **text**, not a model checkpoint, COW cache, workflow ledger, tool
grant, or independently verified description of a live machine. It never scans
the whole fleet, grants execution permissions, or refreshes an existing model
context behind the caller's back.

## Prepare explicit approved sources on Linux

Use a dedicated source directory on llm-49. Copy only text David approves for
model context into that directory. Do not point the builder at a home directory,
SSH directory, credentials, protected workload answers/checkers, or the entire
fleet. Reviewed examples and recorded system facts must be kept separate:

    /home/dflanag3/branchwrite-approved-context/
      examples/
        terminal-statuses.txt
        quoting-and-unicode.txt
        coding-workflows.txt
      facts/
        machines-and-roles.txt
        project-map.txt

These are suggested paths, not directories automatically created or populated by
this change. No production machine inventory was scraped. Use owned synthetic
examples or explicitly approved records. Failure-class LoRA candidates remain
unreviewed until separately approved; their existence does not authorize adding
them to a prompt or training.

For facts, write an observation date and the evidence/owner in the source file.
The required pack-level `--as-of` value is a caller assertion about the records,
not proof of their accuracy. Include narrower dates in individual files when
needed. When a tool finds a stale fact, report it, update the approved record,
and rebuild a new pack. Keep the actual tool observation in the workflow ledger.
Do not rewrite history to pretend an old pack was current.

## Build and verify

Run on the Linux CLI host, from the BranchWrite checkout:

    python3 -B -m branchwrite.context_pack build \
      --root /home/dflanag3/branchwrite-approved-context \
      --examples examples \
      --facts facts \
      --as-of 2026-10-18T16:00:00Z \
      --output /home/dflanag3/branchwrite-reference-packs

Selections are repeatable relative POSIX paths. A selected directory includes its
descendants; an explicitly selected file does not include its siblings. Do not
put the output directory inside the approved source root. Files must be regular
strict UTF-8 text. Symlinks anywhere in a source path, special files, path escapes
and mid-capture changes fail. There is no silent truncation.

The command prints a JSON receipt including `pack_id`, `pack_path`,
`source_files`, `source_bytes`, `prefix_bytes`, `captured_at`, `as_of` and
the configured limits. The generated directory contains:

- `manifest.json`: selected root, relative paths, sections, hashes, byte counts,
  limits, capture provenance and stable identity.
- `prefix.txt`: the exact rendered reference text, with separate example/fact
  sections, source attribution and a no-authority warning.
- `manifest.sha256`: integrity checksum for the manifest bytes.

Files are created privately and made owner-read-only. The output is published
from a temporary directory after file and directory fsync on the tested Linux
filesystem. This is not a power-loss or adversarial-storage certification.

Verify before admitting a new root:

    python3 -B -m branchwrite.context_pack verify \
      /home/dflanag3/branchwrite-reference-packs/<pack_id>

Exit 0 means fresh, exit 2 means stale selected sources, and exit 1 means an
invalid/corrupt pack or build error. A stale receipt lists changed/added/deleted
paths when comparison is possible; missing, invalid or unsafe sources have an
explicit reason. An unrelated unselected sibling does not stale a file-only
selection. Rebuild with the same selection after edits/additions/deletions.
The builder retains the old content-addressed directory. It does not silently
substitute a new pack or delete old packs.

## Stable identity and freshness

Identity includes the absolute approved source root, sorted relative selections,
section, relative file paths, exact UTF-8 bytes/hashes, rendered prefix digest,
explicit as-of value, format version and resource limits. Identical text at two
different relative paths remains distinguishable. Reordering selectors changes
nothing. Filesystem mtimes and the capture clock do not churn the identity.
A byte-identical rebuild reuses the original immutable pack and capture receipt.

Before each new admission, source bytes are read again with no-follow descriptor
traversal. File identity/statistics and the selected tree are checked around
capture to detect source mutation. This is an admission-time check, not a
filesystem lock: an external fact may change immediately afterward. No checksum
can establish factual truth, source trust, or present tool authority. These are
local integrity hashes, not a signed authenticity scheme.

Use the pinned API from a CLI integration:

    from branchwrite.context_pack import load_verified_prefix
    text = load_verified_prefix(pack_path, expected_id=pack_id)

The optional pin is checked before source capture. The function returns the exact
in-memory prefix whose bytes were integrity checked; it does not verify one read
and return another unverified read. A stale source raises `StalePackError`;
integrity errors or a pin mismatch raise `PackError`. The caller must stop
new model admission on these errors. Existing resumed COW roots retain their
original prefix and operation identity. To use updated records, intentionally
admit a new root; do not replace an existing continuation's preserved prefix.

## Size limits and future long examples

Defaults are 512 files, 8 MiB per file and 32 MiB of total source text, settable
with `--max-files`, `--max-file-bytes` and `--max-total-bytes`. Positive hard
ceilings are 20,000 files, 128 MiB/file and 512 MiB total, plus 20,000 directories
and source depth 128. Limits fail explicitly; they never trim examples.

The pack builder does not tokenize, load a model, choose context capacity,
perform YaRN/RoPE changes, or reserve thinking/output space. The integrated
admission path must apply its actual tokenizer and leave room for the task,
tool results and generation. A large text pack passing these filesystem tests
does **not** qualify 100K+ tokens on the current 98,304-token execution profile.
Larger native capacities and positional profiles require their own tests.

## Executed scope and remaining work

The focused tests use real Linux files, symlinks, FIFOs, process-separated CLI
calls and deterministic source-mutation hooks. They include a pack with more
than 500 KB of exact Unicode text. They verify freshness, stable identity,
corruption rejection, bounded reads, cleanup after a simulated publication
write failure, and returning the exact validated payload.

This standalone work does not measure model reasoning, throughput, example
quality, native token capacity, model restart, power loss, or full G/VC gates.
The parent integration owns the opt-in CLI/config hook and its canonical
request binding. Live ablations must use independent held-out tasks, preserve
all failures, and compare examples versus examples+recorded knowledge without
feeding protected expected answers into the model. More examples are useful
only if the resulting task behavior improves; a single pass is not robustness.

Execution receipt: validation/CONTEXT-PACK-2026-10-18.json. Focused 28/28
and the exact frozen 95-client-test ID set passed (123 total, no skips). Two
earlier broader-module launches retained 3/6 environment import/configuration
errors respectively; those are not silently converted to product passes.

## New coding CLI contexts

An optional top-level host configuration field pins one immutable pack:

    "context_pack": {"path": "/approved/packs/<pack_id>", "pack_id": "<64 lowercase hex>"}

Use this only with cow.bootstrap="coding". New admission verifies the pin and
selected-source freshness before creating a COW namespace or loading its prefix.
The pack is appended to the existing tool instructions and relevant examples.
It does not add grants. An existing workflow resumes its saved COW root even if
the source notes have since changed; it never silently rewrites that root.
Build a new pack and start a new context when you intentionally adopt new notes.

## Component-first measurement

Run each terminal domain independently before an autonomous workload. The
terminal_components command uses real sandboxed commands and preserves exact
raw outputs. Its PASS is a transport result, not model understanding.

The component_model command can then ask a real COW server to report a held-out
observation. It uses the normal BranchWrite HTTP client and a thinking/JSON
grammar that constrains fields but does not force correct values. Cases fork
from one shared reference prefix and cannot execute tools. Supply approved
prefix/cases files, a private credential file and a fresh external output
directory. Start the server with component_model.grammar_registry(). The
current research runner uses4K thinking and reports individual failures,
thinking metadata, output counts and whole-call latency. Context creation time
is not necessarily native prefill time; measure native work separately.

Compare the previous ten examples against five new demonstrations per section.
Keep structurally different held-out cases out of both roots. Large contexts
must pass exact-tokenizer capacity admission before model launch. The current
pinned native profile has98,304-token capacity, so100K+ examples need a separate
larger-profile qualification; bytes are not tokens. More examples and shorter
thinking are hypotheses, never acceptance criteria.

## Refresh after source edits

Use the previous pack's recorded selections and limits:

    python3 -B -m branchwrite.context_pack refresh \
      /home/dflanag3/branchwrite-reference-packs/<old_pack_id> \
      --as-of 2026-10-19T20:00:00Z \
      --output /home/dflanag3/branchwrite-reference-packs

If the selected bytes have not changed, the receipt says action: unchanged.
It returns the old identity and original as-of time and writes no new pack.
Changed sources produce action: rebuilt, previous_pack_id, a new pack_id
and exact added/deleted/modified paths. The old pack is preserved. Unsafe links,
missing explicitly selected files, corrupt packs and publication failures fail
instead of silently changing the approved selection. New files within an
originally selected directory follow that existing directory selection.

This is a point-in-time capture, not a filesystem lock or semantic fact check.
Review the updated records before admitting the returned identity into a new
COW root. Existing worker tips retain their old base. Adoption, automatic
refresh scheduling, verified delta summaries and compaction policy are still
separate integration work. A model may propose them but cannot relabel a saved
computation or grant itself new paths. Use build explicitly to change scope
or intentionally change the as-of assertion without changing source bytes.
