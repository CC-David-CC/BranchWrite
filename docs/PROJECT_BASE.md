# Project Base

Project Base is the accepted user-facing name for the existing GoldenPath
component. `ProjectBase` aliases that exact class in branchwrite.golden_path;
there is one implementation,version type and canonical COW history. No stored
record is renamed. Actual source remains in Git/worktrees;model context is
reusable derived knowledge,not another authoritative copy of the source tree.

Use start for a closed reference root,refresh for a separate evidence-bound
candidate version,and question to ask from an exact version in a separate
continuation. Each question supplies explicit destination,fork and generation
operation IDs. Questioning never changes the source or adopts the answer.
A root uses ask;completed summary versions use append_user after the fork.
Input errors fail before a fork. A repeated original request retains its IDs;
missing answer bytes are never repaired by hidden regeneration.

Multiple candidates may share a parent. Two candidates may both be version1;
number is lineage depth,not a globally unique version or a winner. Exact snapshot,
branch and endpoint pins identify each. Existing continuations stay pinned when
a new candidate is chosen. There is no mutable global latest selection here.
Host verification/adoption and normal workflow ownership remain required.

Executed:16combined CPU/HTTP tests pass,including6new question/candidate cases.
An earlier environment omission lacked a test-only audit helper;failed output
retained and the unchanged suite reran after supplying it. No autonomous/GPU or
physical-sharing certification from these tests. The dedicated prepare-base CLI
now builds a project-derived pack and publishes a COW root. Automatic base
selection in ordinary coding startup and multi-base consultation remain future
integration work.

## Three-build comparison and recursive development

Compare all product Python source;compact overview with selected modules;and
compact plus owned generic tool examples. Pin the same Git source commit and
exact file selections. Do not label product-module coverage full repository
coverage. Check actual tokenizer counts against capacity before inference;
never silently truncate the large candidate. Keep cold build/restore and warm
question costs separate. Use common tasks,budgets,model/profile and independent
checks. A different-length model answer is not an isolated speed comparison.

Q8 BranchWrite may implement bounded pieces in an isolated owned candidate.
Allow up to four FULL BranchWrite attempts per failing piece,each through
CLI/HTTP/server/model/tools/tests. Between attempts the parent can improve
reusable steering,examples,grammar and guards based on concrete evidence.
Retain all attempts and label guided development. The final frozen rerun must
have no intervention;independent review/tests decide integration. Never alter
protected tests or let the candidate approve itself. Capture genuine model
failure classes for the existing LoRA collection. No training or publication.

## Three complementary bases, independent consultations

The current comparison prepares A (all product source), B (compact overview and
selected modules), and C (that compact context plus generic worked examples).
They are separate immutable computations, not three copies of a mutable global
memory. A worker can ask one or several bases using question(), each in its own
fork. The host must retain the exact source version, question, returned tip and
operation IDs in its existing workflow ledger. Shared purpose does not mean
shared mutable grammar, sampler progress, tool results or working files.

For example, an editing tip may ask A which callers depend on a function, B what
boundary the module owns, and C for a relevant implementation pattern. A synthesis
step can compare these answers and cite their source references. None proves that
a file is current or a test passed. Conflicting answers stay visible; check current
source and actual command receipts before adopting a change. A base cannot grant
permissions, publish a working tree or silently replace the selected project base.

The question API and competing-version fixtures exist. Native preparation, a
three-way live coding comparison, combined consultation and automatic selection
are distinct milestones; the latter two are not yet integrated into normal code
execution. Do not describe a text pack as a prepared GPU checkpoint.

## Expected refresh during real coding (owner clarification, 2026-10-19)

A saved Project Base becomes stale as the working files and completed phases change.
That is expected. Never relabel its immutable checkpoint as current or move existing
worker tips behind their backs. Retain the exact revision and observation identities
on which each consultation relied. Source-file hashes establish freshness, not truth
of a model summary. Working-tree changes require a content manifest as well as a Git
commit ID; an unchanged commit does not mean unchanged files.

Use the existing refresh() path for small, host-selected observations: changed code,
actual test results and phase outcomes. The returned branch is a candidate version,
not an automatic winner. A host must validate summaries and select a version before
future workers use it. Old tips and source versions remain available. Failed tests,
unresolved tool effects and uncertain observations must remain explicit.

When accumulated updates or obsolete details make that continuation unwieldy, build
a new compact reference from current approved sources and verified observations and
prefill it as a new root. This recomputes the new prefix honestly; it does not rewrite
old KV state or promise identical logits to the older context. Record the old-to-new
provenance in the existing workflow ledger. Refresh/rebuild can occur at phase
boundaries or after enough source changes; no timer or automatic summary adoption
is enabled yet. The automatic freshness/refresh policy and its CLI integration remain
implementation work. Existing context-pack source validation and explicit refresh()
provide building blocks, not a claim that ongoing work is automatically refreshed.

The source API now includes base_choice.resolve_base_proposal: a pure validator for
an untrusted model's offered-base choice. It checks the host catalog, source/profile
identities and token headroom and returns a detached host record and reason. It does
not select a live checkpoint, restore state, grant tools or execute work. The reviewed
implementation was authored through the Q8 BranchWrite CLI from base B and independently
tested. Normal CLI automatic selection remains unintegrated; COW still validates actual
checkpoint compatibility and availability when materializing the selected reference.

## Explicit proposed choice in the source CLI

New source admissions may replace --from-prefix with --project-bases CATALOG.json,
--base-choice PROPOSAL.json, --base-revision HOST_REVISION, and
--base-reserve-tokens HOST_TOKEN_HEADROOM, supplied together. The catalog is the
host-approved list accepted by resolve_base_proposal; the proposal is exactly
schema1,base_id,reason. It is data, never permission to execute a tool. The selected
profile must match the connection. A conflicting explicit source is rejected.

The existing frozen coding launch stores the selected branch/snapshot and the
validated decision as a Text input binding. Resume retains it without rereading
changed choice files; changed new admission bytes require a new run state. No
new workflow ledger, mutable global base pointer or checkpoint representation is
introduced. The host-supplied revision expresses its required reference version;
this is not an automatic proof that an uncommitted working tree is identical.
COW still checks actual checkpoint compatibility and resources.

Thirty-five focused source checks pass, including six new selection/launch cases,
eleven validator cases,thirteen existing launcher and five sampler-choice cases.
The CLI-parser selection test stubs execution at run_saved; these are admission
and persistence checks,not new HTTP/GPU evidence. Installed dev19 is unchanged.
The model does not yet automatically propose a base during normal code admission.

## Source changes and immutable refresh (2026-10-19)

The reference-pack refresh command now detects selected source byte changes and
builds a new immutable pack using the original selections and limits. It is
available as python3 -B -m branchwrite.context_pack refresh; see REFERENCE_PACKS.md.
An unchanged pack keeps its original identity and as-of time. The HTTP integration
fixture admits the returned prefix into a separate COW root, preserving both the
old root and an existing worker fork.

This does not automatically refresh the catalog or an active coding tip.
A source pack is derived text; a Project Base version references canonical COW
computation. The normal workflow still needs to coordinate new-root admission,
record the new reference, and explicitly choose it for future work. Delta
summaries, compaction thresholds and automatic role selection remain unfinished.
No silently moved latest pointer or second history representation was added.

## Preparing a refreshed pack as a Project Base

ProjectBase.prepare_pack(branch, purpose, pack_path, expected_pack_id,
operation_id, source=None) admits the exact verified current pack through the
existing COW load_context operation. It returns the existing GoldenVersion type.
The manifest_sha256 field binds the pack identity; the COW snapshot binds the
actual purpose and rendered input as well. Missing/stale/incorrect pack identity
and a foreign parent endpoint fail before context admission.

Supply source=previous_version to record a rebuild's provenance. The number
advances, and parent_snapshot identifies the previous version. That provenance
does not claim the new root computationally descends from the old root: its
prefix is genuinely computed. Existing references and worker forks are unchanged.
Use a new destination branch and operation ID. An existing base cannot silently
be overwritten. A repeated identical admission retains its original operation.

A rebuilt version is still a closed context root, even if its number is greater
than zero. It has no summary yet. Questions/observation updates therefore use ask;
only completed summary versions use append_user. The version number describes
lineage depth, never the COW turn boundary. No persisted version fields changed.

This is a usable API seam, not automatic normal-code admission. The workflow
still needs to retain the returned version in its existing ledger, propose and
validate a base choice, and decide when to refresh or compact. There is no
background job or global mutable latest base.

## Opt-in host selection during coding admission

Development source now accepts `--project-bases CATALOG --auto-base` together
with `--base-revision REV --base-reserve-tokens N`. Do not also supply
`--base-choice`. The host catalog must contain only task-appropriate approved
bases. `host-longest-fitting-v1` filters exact revision/profile and token reserve,
then selects the longest prefix; the smallest base ID breaks ties. This is a
simple reproducible host policy, not model judgement or a cache-residency probe.
A longer prefix does not prove better answers or lower latency.

The exact chosen snapshot and policy reason enter the existing immutable coding
launch and canonical input binding. Resume retains that choice even if the
catalog changes. No fit is a clear error; there is no silent fresh bootstrap or
weaker profile fallback. Explicit model-proposed choices remain available via
`--base-choice`. Catalog freshness, summary adoption, refresh/compaction and
consultation scheduling still require host coordination. In particular, a Git
revision does not prove that working-tree files are unchanged.

Executed: five new selection/admission checks and 36 combined focused checks
pass. Automatic selection now additionally passed actual CLI subprocess and authenticated
local COW HTTP with a CPU inference fixture, including rejection before state
creation, exact fork, grammar registration and independent child continuation.
All 53 combined checks passed. No Q8/native qualification of automatic selection
has run. It is not in the dev26 wheel.

## Source freshness for pack-bound catalog entries (development source)

A host catalog entry can additionally contain both `reference_pack_path` (absolute
local pack directory) and `reference_pack_id` (exact64-hex pack identity). These
fields refer to the existing immutable reference-pack format, not a second source
inventory. Admission validates the pack identity and rechecks its selected source
bytes. Explicit proposals fail on a stale chosen pack. Automatic selection excludes
stale packs; when any offered entry carries a binding, automatic selection cannot
fall back to an unbound legacy entry. Corrupt/missing packs fail explicitly, rather
than being silently treated as stale. Incompatible entries are not opened.

The selected entry and binding remain in the existing frozen launch. Resume does
not replace an admitted base because external files later changed. New work can
refresh the pack explicitly and prepare a new base; automatic rebuilding/adoption
is still unfinished. The trusted host supplies the association between pack and
COW snapshot. This check does not independently attest that snapshot's actual
prefix contents, validate a summary's truth, or lock changing external files.
Legacy catalogs without bindings retain their earlier host-asserted revision scope.

Eight new tests and80 combined checks passed, including stale CLI rejection before
state creation/dispatch. This source change is not in the installed dev27 wheel;
its separate Q8 result is not retroactively extended to these new checks.

## Derive an offer from a prepared pack root (development API)

After `prepare_pack`, call `catalog_entry(version, pack_path=..., source_revision=...,
execution_profile_id=..., capacity=...)` on that same ProjectBase/client. It requires
the completed original context operation in the existing OperationJournal. It
checks exact request bytes against the current verified pack, branch/namespace/
operation ownership, the returned snapshot/profile, and the server history's exact
root/tip input counts. A moved reference, summary version, missing count metadata
or mismatched receipt fails; no tokenizer estimate or native-trace scrape is used.

The result is a detached host catalog entry compatible with normal `--auto-base`
admission. Its ID binds the offered fields and endpoint identity. Save/publish it
through host coordination; this API does not create a second workflow journal or
silently update a global latest pointer. Source revision and context capacity remain
explicit host configuration. The pack-to-snapshot association is checked through
the client's original request and authenticated server receipt; this is not an
independent numerical attestation. `prefix_tokens` counts canonical model-input
cells (text tokens plus image rows), not GPU residency or compute savings.

Requires COW canonical-counts source89525144. The previously tested pinned Q8
server does not yet supply those fields; it fails explicitly rather than guessing.
46 CPU/actual local HTTP+CLI checks passed, including substituted request ownership,
wrong bytes/profile/snapshot, missing counts and existing question/refresh regressions.
No new native/GPU campaign. CLI preparation and atomic catalog publication remain
next integration work. Installed dev27 remains unchanged.

## Prepare a catalog through the development CLI

`prepare-base` now freezes setup arguments in an immutable private setup file,
journals original HTTP intents with the existing OperationJournal, prepares a
pack-backed context root, verifies its model/profile receipt and exact count,
then atomically publishes `STATE/base-catalog.json`. It creates no tool grants or
mutable latest-base pointer. The setup file is admission metadata, not another
workflow history. One nonblocking preparation lock serializes a state's writers.

From the current Linux source checkout, with the same environment and connection
file described in the manual (the installed dev27 wheel does not have this command):

~~~bash
python -m branchwrite prepare-base \
  --connection "$HOME/branchwrite-client/connection.json" \
  --state "$HOME/bw-runs/project-base-v1" \
  --branch project-base-v1 \
  --purpose "Provide approved source and examples for this coding project." \
  --context-pack /absolute/path/to/packs/EXACT_PACK_ID \
  --context-pack-id EXACT_PACK_ID \
  --source-revision EXACT_SOURCE_REVISION \
  --capacity 262144 \
  --operation-id project-base-v1-prepare
~~~

Replace the identity/revision/path placeholders with actual verified values. Use
the pinned profile's real capacity. The server must include canonical count source
89525144 and have a profile with verified runtime sources; the older pinned Q8
server will not supply these fields. Do not remove source-hash validation to run it.

Exit0 reports PREPARED, catalog path and root identity. Supply that catalog to a
new `code --project-bases PATH --auto-base --base-revision REV
--base-reserve-tokens N` run. That run still needs ordinary project grants, task,
connection, state, branch and verification command. A prepared reference is not a
GPU lock. A generic factual pack is not automatically the same tool-example prefix
as the separately tested dev27 coding bootstrap; model quality needs its own trial.

Retry with the original state, operation ID and arguments. Setup changes fail and
existing catalogs are never overwritten with different bytes. Reconstructing a
missing derived catalog reuses the original preparation. Exit4 means unresolved:
retain the state. Explicit `--reconcile` can replay the original idempotent namespace
admission and reconcile only a proven durable context result; unknown model work
stays unresolved. A new ID means new work. Bounded client-process-death/lost-ack tests now pass through real HTTP with CPU
inference fixtures; native process death and real-Q8 recovery remain unqualified.
Clean retry and derived-publication recovery were also exercised. Completed old workers keep their original roots.

51 combined checks pass, including actual CLI/HTTP preparation, identical replay
from a separate state, zero added model work on retries, publication alias rejection
and changed-setup/catalog rejection. No new GPU or installed-wheel qualification.
Automatic source refresh, catalog adoption and compaction remain unfinished.

## Preparation crash-boundary evidence

Three additional actual CLI process-death cases passed, with54 combined checks:
namespace committed before local acknowledgment; context committed before local
acknowledgment; and client intent recorded before context send. Recovery of the
namespace admits exactly one initial prefix computation. Recovery of the committed
context adds zero forward work. A context with no durable server result remains
unresolved after explicit reconciliation: no new branch/catalog, no forward work.
Namespace count does not increase during replay. These are CPU-backend HTTP tests,
not GPU/native restart or power-loss certification. The initial namespace fixture
mistakenly expected zero work before any prefix existed; its failed output and
corrected exactly-once assertion are retained in validation/prepare-base-cli-process-death-20261019.


## Client-side durable project-context receipt

The project context builder is a BranchWrite client responsibility layered above
Context COW. Context COW remains canonical for saved conversation histories,
branch references and computational checkpoints. BranchWrite captures an
explicitly selected set of project files plus completed, revision-pinned COW
branch histories into an immutable reference pack. The receipt records selected
file hashes, branch root/tip/revision and history hashes, snapshot identity, pack
identity, and durable progress. Old conversation text is marked as evidence,
not current source truth or tool authority.

Use the dedicated `prepare-base --project PROJECT` command to build this source
context; pass each approved file/directory with `--read` or `--read-dir`, and
each saved branch to include with `--source-branch`. It does not scan the whole
project or include unselected secrets. It rejects active/unknown branch
controllers and text-incompatible branch history. `context-status STATE`
reports the last durable steps and the original COW operation receipts after a
restart. If it stopped after freezing inputs, repeating the same operation and
state reuses those exact inputs; changed source files or moved branch tips are
captured only in a new state.

The source snapshot and pack are derived client records, not another mutable
conversation history. The prepared Project Base is still materialized into
Context COW through the existing context operation. A lost acknowledgment is
reconciled using the original operation ID and COW journal. Do not start a new
operation ID while the original is unresolved.

The normal `branchwrite code --build-project-context` path now uses this
builder before it publishes its immutable coding launch, and pins the source
receipt hash into that launch. It is opt-in and uses existing explicit read
grants; it does not scan the whole project or refresh every run automatically.
The client receipt and CLI assembly have CPU tests. They have not yet had a new
real-GPU run or broad process-crash testing across every server publication
point.
