# Native COW client interface (draft)

Status: design note for the first BranchWrite client slice. The interface maps
to the existing COW HTTP service and `tools/cow_cli.py`; it does not add a COW
wire endpoint or make the client a second workflow interpreter.

## Typed boundary

The client exposes one transport-neutral protocol. HTTP is the normal transport;
the conformance transport invokes the installed COW CLI as a subprocess and
parses its documented stdout/stderr result. Neither transport is allowed to
infer success from generated text or process exit alone.

The initial value types are:

- `ServiceObservation`: configured endpoint, authentication mode, observed
  `/cow/status` capacity, and optional externally pinned service identity. An
  endpoint URL is not a store/model identity.
- `BranchHead`: branch name, revision, tip snapshot and root snapshot returned
  by `/cow/head`.
- `OperationIntent`: operation ID, HTTP method/path, exact request body bytes,
  branch and expected revision where applicable, client frame key, and the
  endpoint identity/pin used for dispatch. Its `COWSourceBinding` also captures
  source branch, snapshot and revision when the request continues existing
  state; the HTTP body still uses COW's existing revision/CAS fields.
- `GenerationResult`: bounded provisional text/progress, terminal answer, and
  validated durable receipt. Provisional data is never represented as an
  acknowledged generation result.
- `OperationStatus`: COW's process-scoped operation status and optional
  durable receipt. It explicitly records that a 404 after restart is
  indeterminate rather than proof that the operation did not commit.

The transport protocol covers status, head/history, operation lookup, prepare,
answer/ask, fork, continue, `append_user` for returning bounded tool observations
as a new user turn, saved-answer retry, and original-request retry. It also
provides namespace creation for the prepare flow.
Sampler settings are forwarded as the exact supported settings object. A
BranchWrite profile identity is client-side provenance; it is not sent as an
invented COW `profile_id` field.

## Identity and ordering

Every dispatched computation has a stable `FrameKey`:

```text
FrameKey = (run_id, invocation_id, parent_id, attempt_id,
            child_id, result_slot_id, continuation_epoch)
```

It is bound to the exact COW endpoint pin, branch, source snapshot/revision,
operation ID, and operation intent digest. It is created before dispatch and
never derived from queue order, completion time, or arrival position. A return
must match the complete key and the original operation/source binding before it
can fill the named slot. An identical duplicate for an already filled slot is
idempotent; a stale epoch, other child, different operation, or conflicting
result cannot replace it.

Computation eligibility, completion, and delivery are separate. On a single
GPU, COW may serialize A and B; BranchWrite still stores each result under its
own slot. Tests will compute A then B and deliver B before A, redeliver delayed
A, and restart the parent between returns. These tests exercise identity and
recovery, not concurrent GPU execution. The client reserves advertised COW
capacity once. It does not bake a global one-request limit into IDs, seeds,
joins, or result-slot semantics, so a later service with N advertised slots
can dispatch independent eligible work without changing the graph contract.

## Durability and recovery

Before any mutating HTTP request or CLI command, the client durably journals the
original operation ID, exact method/path/body, expected branch revision,
endpoint pin and `FrameKey`. Journal data contains no API key or authorization
header. It may contain submitted source/text because exact original bytes are
needed to reconcile the operation. The journal is a client intent/recovery
record, not a COW transcript or authoritative generation history.

An uncertain send is reconciled by querying the same operation ID and
validating a returned receipt against the original intent. A COW operation
lookup is process-scoped; after restart, 404 or unknown status remains
indeterminate and does not authorize blind resubmission. A user can explicitly
recover with the original journaled request only through a route whose COW
idempotency contract binds that exact request. Saved-answer retry is a separate
operation: the client first reads COW retry information and uses COW's retry
route; changed generation settings require a new operation ID and must retain
their original-source binding.

For streaming requests, text and progress are provisional. The client enforces
byte/line/deadline bounds, rejects malformed or truncated event streams, and
returns a generation as durable only after validating a complete event and its
structured branch receipt. A receipt's snapshot must match the branch tip, and
the answer snapshot, when present, must match that same receipt. Error/failure,
EOF, timeout, or missing completion is not successful completion.

Grammar state is an optional named server-owned state on a generation boundary.
It is passed through only where the pinned COW endpoint accepts it. Continuing
an active grammar turn preserves the saved parser state; selecting another
state mid-turn is a COW rejection, not a client-side reset. Sampler settings
are likewise forwarded as the exact supported per-generation mapping and are
never inferred from a BranchWrite profile name.

## Existing COW routes and identity limitation

The client uses the inspected service routes: `GET /cow/status`, `/cow/head`,
`/cow/workspace/history`, `/cow/operation`; `POST /cow/namespace`,
`/cow/text/prepare`, `/cow/text/answer`, `/cow/text/ask`, `/cow/text/resume`,
`/cow/text/append-user`, `/cow/fork`, `/cow/text/retry`, and
`/cow/publication/retry`. Exact endpoint and receipt shapes are implemented
against the pinned COW source, not guessed from a mock.

Current `/cow/status` reports worker/pool capacity metrics, but does not expose
a stable, authenticated identity for the active store, model, tokenizer,
native build, or execution profile. Startup readiness output includes an
execution profile ID but is not available through the HTTP client. Therefore
the initial client can record a user-configured endpoint pin and observed
status, but must label service identity unverified unless a separately
provisioned, integrity-checked service manifest binds those values. A URL by
itself is never proof that a restarted endpoint serves the same store.

## Current qualification boundary

The model-free CPU checks pass the 16 client unit tests and actual FlowModel
HTTP/CLI workflows (prepare, answer, fork, continue, append-user, history,
status, and stale-CAS rejection before inference); the combined focused run
passed 19/19 tests. An earlier CLI FlowModel
run passed before the client started passing expected revisions; it does not
qualify the current CLI source. The
client now supplies `--revision` on answer, ask, continue, and append-user, and
prechecks the observed head. The corresponding COW CLI change must preserve
that exact revision into the service request so its CAS closes the race; a
source version without that option is incompatible and must not be treated as
conforming.

There is also an exact-text framing gap in the existing human CLI output. It
prints streamed text followed by a display newline, while its durable receipt
contains the branch/snapshot transition but not the canonical answer text.
The client cannot safely remove one final LF because the answer itself may
legitimately end in LF. The companion COW change adds opt-in `--machine-result`
output containing the exact complete-event answer and receipt, and saves that
answer in the COW CLI request journal for local completed-operation replay.
The BranchWrite parser now accepts only that envelope for streamed CLI
requests. It preserves an answer object without `text` for prepare/context
operations, while requiring exact string text for answer-bearing generation
routes. Client tests cover envelope decoding with a trailing LF and the
no-text prepare shape. Against the frozen combined COW CPU candidate, actual
HTTP and CLI FlowModel conformance passed for prepare, answer, fork, continue,
append-user, and history; the HTTP stale-revision race was rejected before
inference. This is CPU fixture coverage, not model/native qualification. The
HTTP peer tests cover intent-before-send,
changed-request rejection, pending lost-ack behavior, cached receipt replay
after the observed head changes, and unknown process-local operation status.
Slot tests deliver A/B in reverse, reload the slot record, redeliver an
identical result, and reject stale or conflicting identities. These checks do
not claim model/native qualification, an actual parent-process restart,
parallel GPU execution, or reserved capacity.

## Bounded model-quality ablation

The client interface leaves prompt and grammar choices explicit so a pilot can
compare four controlled conditions even when the baseline succeeds: baseline,
one targeted example only, GBNF only, and the same example plus GBNF. The task,
sampler policy, output budget, and protected tests stay fixed across arms. A
run record should retain the exact added prefix tokens and grammar definition
identity, task correctness/quality, legal-format success, refusals and rejected
actions, output counts, and latency. Grammar validity is one measured outcome;
it is not an automatic adoption rule. The host still validates and authorizes
every proposed action before the tool executor runs it.

The client does not infer that an arm is better from formatting success alone,
and it does not silently grow examples after runtime errors. Each arm has its
own COW source identity and operation IDs so delayed results cannot be
misattributed to another arm. The current COW HTTP status route reports
capacity but offers no reservation token; the initial client therefore
observes capacity without claiming a reservation. Its slot identity remains
independent of the currently configured one-worker/one-GPU execution limit.
