# Production run records: first interpreter storage boundary

BranchWrite needs to remember which tool it called and what came back. Otherwise,
a restart could make it run the same tool twice. This layer saves that information
and exact result bytes. The decision interpreter that uses it is still being built.

This implements storage primitives supporting R02/R03, not completion of those
registered tickets, the general agent loop, VC09 or original G1-G5. It imports no
reference implementation. The existing COW client journal remains the exact native
transport-intent protocol; it is not copied into a second model transcript here.
One production typed event log will own workflow transitions and opaque references
to COW receipts. JSON/JSON Schema model outputs remain supported under the owner's
explicit retirement of the historical JSON ban; workflow records use this codec.

## Exact typed value format, BWT version1

A value begins with bytes42 57 54 01 (BWT plus binary version1). Every nested item
is one ASCII tag, a big-endian uint32 payload byte length, then its exact payload.
No child carries another file prefix.

| Tag | Exact payload |
|---|---|
| n | Empty, for explicit None |
| b | One byte00 or01; not an integer |
| i | Canonical ASCII decimal integer, no leading zeros, no plus or negative zero |
| f | Big-endian IEEE754 binary64, finite; preserve negative zero |
| d | Canonical Python Decimal string, finite; preserve sign, digits and exponent |
| u | Strict UTF-8 text |
| x | Opaque bytes |
| l | Ordered nested items, returning a list |
| t | Ordered nested items, returning a tuple |
| m | Alternating text keys and values, unique keys in Unicode lexical order |

The parser re-encodes the result and requires identical bytes. Limits are4MiB
per complete value/artifact,40 nesting levels,4096 entries per container,12000
integer bits. Unsupported types, nonfinite values, duplicate/out-of-order keys,
extra bytes and unsupported versions fail. User text that spells an operation or
tool tag remains plain data. The production format is distinct from the protected
reference oracle's illustrative encoding; no production import/fallback exists.
Typed domain references and event schemas are interpreter responsibilities still
pending, not inferred from a generic map containing arbitrary strings.

## Ledger format, BWL version1

The file starts with bytes42 57 4c 31 00 (BWL1 and a zero byte). Each frame has:

1. Big-endian uint64 zero-based sequence.
2. Big-endian uint32 typed payload length.
3. Previous event SHA256,32 bytes; all zero for the first event.
4. Event SHA256,32 bytes.
5. Header SHA256,32 bytes.
6. Complete BWT1 payload.

The fixed header is108 bytes. Event SHA256 covers domain bytes
`branchwrite.event.v1` followed by a zero byte, the8-byte sequence, previous hash,
and typed payload. Header SHA256 covers domain bytes`branchwrite.header.v1`
followed by a zero byte and the preceding76 header bytes. This independently
checks a damaged length before deciding whether a payload is merely incomplete.
The event payload is exactly a typed map with keys`event` (a map) and`artifacts`
(a tuple of `(lowercase_sha256, byte_count)` tuples).

Sequence, previous hash, header digest, event digest, canonical payload and all
referenced artifact contents are checked on reopen. An incomplete trailing frame
is TornTail. A complete bad header, chain or payload is CorruptLog. Missing
referenced bytes are MissingArtifact. These conditions never rewrite/truncate the
file. An explicit tail-recovery policy is not implemented yet. Hashes detect
accidental corruption; they do not authenticate an attacker-replaced control store.

## Ownership and durable ordering

RuntimeLog owns one Linux flock, process and Thread object. Another process cannot
open a writer; another thread cannot read, append or release this writer. Regular
files are required. FIFO artifacts/ledgers fail before a blocking read. Opened
file descriptors use close-on-exec; final filename opens reject symbolic links.
The trusted run store must remain outside candidate capabilities. This is not a
standalone sandbox or a defense against an attacker controlling the same UID/store.

put_artifact writes an owned temporary file, flushes it, publishes by no-overwrite
hard link into artifacts/SHA256 and flushes the destination directory. Existing
bytes are checked. Before appending a reference, the artifact file and directory
are flushed again, including when an earlier publication call failed. The event
frame is written and fsynced before append returns its EventReceipt.

An uncertain event append poisons that writer. Reopen and reconcile recorded
invocation/operation identities before doing more work. Storage alone does not
implement effect idempotency, grants, frame reduction or tool reconciliation.
Distinct invocations remain distinct even when their artifact bytes deduplicate.
Returned event views are detached from caller mutation. Frames are the canonical
history; retained in-memory bytes are a derived replay cache.

## Evidence scope and next boundary

The tests use actual Linux files, independent processes, thread ownership, producer
exit without cleanup, missing/corrupt/reordered records and FIFOs. Fsync/directory
failure injection supplements real filesystem checks; it is not a real disk-full
or power-loss test. No model/GPU inference runs in this storage qualification.

FrameKernel now has bounded component evidence (see FRAME_KERNEL.md). Still
missing: the single step/run CLI and general interpreter integration,
native/tool dispatch bindings, permissions and budget admission, lost-result
reconciliation, end-to-end return-boundary restart, generalized browser actions,
whole-catalogue autonomous runs, sustained log/memory pressure and power-loss or
Windows qualification. Replay currently retains all event payloads in memory;
large-log scalability is unqualified. No claim of independently capable BranchWrite
follows from this storage increment. Natural thinking cutoff remains deferred.
