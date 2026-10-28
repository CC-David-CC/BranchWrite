# Start a coding task

This new entry point uses the existing BranchWrite interpreter and tools. It
prepares their setup for you; it is not another agent loop. Linux is currently
supported. The launcher needs no model files on the client.

The server operator supplies connection.json with exactly endpoint_url,
endpoint_pin, model_contract_id, execution_profile_id and eos_tokens. Use the
actual pinned service identities, not example hashes. Keep the API key in
BW_COW_API_KEY, never in that file. The endpoint pin is a declared host binding;
it is not independent server attestation. Use the established SSH/HTTPS channel.

With the private installed client environment activated:

    branchwrite code /absolute/project --task-file /absolute/task.txt --connection /absolute/connection.json --state /absolute/new-run --branch my-task --read README.md --read tests/test_app.py --edit app.py --test-command 'python3 -m unittest discover -s tests -v'

Use the remote interpreter verified on that Linux client. Each --read, --edit,
--create or --test-command can be repeated. File paths are relative to the
project. Edit/create paths also get read permission so actual observations can
bind edits and newly created files can be inspected. No other file-edit or
creation permission is inferred. The model can run commands in the existing
read-only OS sandbox; command outputs require separately supported grants.
Default command timeout is120seconds; --shell-timeout changes that bound.

The source project stays unchanged. Work goes to new-run/world/workspace.
Inspect that directory and the private ledger before applying anything to your
checkout. Automatic Git publication/COMMIT remains outside this entry point.

The host requires every configured test command to actually exit successfully
in the current workspace, plus a model finish request. This is the existing
command-evidence-and-finish policy, not proof of arbitrary requirements or a
protected verifier against hostile candidate code.

## Keep using a saved train of thought

Add --from-branch earlier-task to fork its current saved tip into --branch.
Add --from-snapshot SHA256 if you want a particular earlier snapshot. The branch
must have a supported stopped-turn continuation boundary. Its context/controller
and checkpoint compatibility are checked by COW. Unsupported states fail;
the launcher never silently replaces them with a fresh conversation.

The selected source snapshot is pinned before the fork mutation. A retry uses
that same source and operation ID even if the earlier branch has since moved.
A new coding run adds its current tool card and task visibly, once. It does not
rewrite the earlier system prefix. COW may restore a checkpoint or explicitly
recompute an evicted history; recovery notices go to stderr.

## Resume the same work

    python -m branchwrite resume /absolute/new-run

This reads the immutable coding-launch.json setup, then reopens the existing
RuntimeLog. It does not reload a changed task file or choose a newer source tip.
The setup file contains no KV state, no second transcript and no credentials.
Changing its task, grants, connection, workflow or pinned fork requires a new
run. --max-steps is a positive interpreter-transition bound (default1024); a
bounded run can stop unfinished and later resume.

Uncertain original external operations retain their journal IDs and require
reconciliation. Resuming is not permission to blindly resend a tool effect.
Existing run/step .bw commands remain available.

## Evidence and unfinished work

The admission/helper and public-command controls pass on the Linux client.
A real CPU-backed COW HTTP test uses subprocess code/resume to admit the root,
register grammars and retain the original setup across bounded execution. It
does not prove autonomous GPU coding through the new launcher.

The earlier SC01-SC03 real Q8 coding runs used the underlying run command and
their campaign driver. They are supporting engine/workflow evidence, not a
live pass of code/resume. A live new-launcher run, protected broader repositories,
project discovery/new-file planning, portable installation, guarded publication,
and combined cancellation/crash/resource qualification remain outstanding.

## Ordinary Git project input (development dev3)

The code command pins a metadata-free project input policy. It copies ordinary
project files into its owned workspace and excludes exact .git entries, including
linked-worktree administration pointers and nested metadata. It never follows
those entries. The original checkout and Git administration remain untouched.
Grants that name .git are rejected. This does not interpret .gitignore, permit
other symlinks, remove copy bounds, or publish edits into the original checkout.

Focused CLI/HTTP admission and safety tests pass. Autonomous dev3 inference and
the broader regression suite still require qualification. Keep old installed
versions for existing pinned workflows; do not migrate them silently.

## Reuse a prepared context (development dev4)

Use --from-prefix BRANCH to start a new question from that branch's initial
context root. Use --from-snapshot ID as well to pin an explicit prepared root.
This forks the saved context and uses the existing first-question ask operation.
The server checks that it is an idle, renderer-matched context-only prefix.

Use --from-branch BRANCH to continue a completed conversation instead. It selects
the current tip by default and uses append_user. Both forms preserve the selected
snapshot in coding-launch.json; retrying setup does not select a newer head.
The two source options cannot be combined. Neither option resumes an unfinished
answer; resume its original saved workflow for that purpose.

The initial unit controls pass. Real HTTP and Q8 qualification of dev4 are pending.
Retain old installed versions and failed operation records; no silent migration.


## Recover an original model reply

With a compatible PCC server, `branchwrite context-budget /path/to/run` reads
the current branch's snapshot-bound token usage and profile capacity. It checks
the saved run's model/profile identity and rejects an observation if the branch
moved during the query. The returned space does not include a future rendered
input; both that input and the requested output must fit. This command does not
change the run, resize a request, compact context, or certify a context length.
The branch can still move after the observation, so a caller must bind any later
action to its original revision and snapshot.

While the original COW coordinator is still running, `branchwrite status RUN`
lists the exact pending operation. With a COW server that supports the live
diagnostic endpoint, `branchwrite diagnose RUN --operation-id ORIGINAL_ID`
checks the saved run and original journal before reading private error details.
The query does not advance the workflow or retry inference. Its process-local
failure is not proof of abort; a result may already have committed. Error messages
may contain private task details. A restarted coordinator may have no diagnostic.
The diagnostic does not validate any durable receipt; use `reconcile` for that.

If a connection or process stops after the server saves a model reply, keep the
same run directory and operation ID. Stop the old client writer first. With the
same server connection and API credential available, run:

```sh
branchwrite reconcile /path/to/run --operation-id bwnative-ORIGINAL_ID
branchwrite resume /path/to/run
```

Reconciliation retrieves the exact output of a proven durable model operation.
It verifies the saved launch, pending model frame, original request bytes,
endpoint ownership and durable receipt. It leaves the workflow ledger unchanged;
`resume` performs the existing workflow transitions. A complete local output
needs no network. Recovery can retain a partial generation without pretending
that it is a completed answer.

An unknown, running or uncommitted operation remains unresolved. This command
does not generate a new answer, repeat a tool effect, bypass grants or migrate
an old interpreter to a new version. Keep the compatible client/runtime for
unfinished workflows. Tool-effect reconciliation and broader upgrade migration
need separate support; never replace the original operation ID just to make an
uncertain action run again.

The initial evidence is real CPU HTTP/subprocess recovery controls. Interrupted
real-GPU coding recovery is a separate campaign; do not infer it from these tests.

`branchwrite status RUN_DIRECTORY --json` now derives model-only recovery
argument lists from pending native frames. This is a local observation, not
proof that the server committed. The reconcile command still requires that
proof. Tool effects are kept separate and must not be retried through model
recovery. The new status guidance is source-tested and awaits dev18 packaging;
installed dev17 supports explicit reconcile/resume without this added guidance.

## Sampler choice for a new coding run (dev19)

`branchwrite code ... --sampler min-p` selects the existing Min-P preset.
Choices are `greedy` (default), `min-p`, and `dry-min-p`. Min-P uses temperature
0.70, min_p0.05, top_k0, top_p1.0. DRY+Min-P uses temperature0.70,
min_p0.05, top_k60, top_p0.95, dry_multiplier0.8, dry_base1.75,
dry_allowed_length2 and dry_penalty_last_n256. These are conveniences over the
existing settings, not new sampler implementations or promises of better answers.

For an alternative approach, use a NEW state directory and destination branch
with the same `--from-prefix`/`--from-snapshot`, source project and grants. Each
run has its own work copy and operation identities. `resume STATE` retains its
saved sampler and never changes an active controller. Reusing an existing run
with a different preset is rejected. Retained prefix compatibility and actual
checkpoint availability remain COW's responsibility. Broader sampler settings
remain available through the existing explicit `run --config` path; this menu
exposes only these three presets. Source CPU/HTTP admission tests passed; this
change has no fresh live-Q8 sampled coding-quality claim.

## Pinned reference packs for a new coding run

The source CLI now accepts --context-pack ABSOLUTE_PACK_PATH together with
--context-pack-id EXACT_PACK_ID. This uses the existing bootstrap and canonical
workflow input; it does not add a transcript or checkpoint store. For example:

    branchwrite code /home/me/project --task-file /home/me/task.txt \
      --connection /home/me/connection.json --state /home/me/run-state \
      --branch coding-v2 --read app.py --edit app.py \
      --test-command 'python3 -m unittest' \
      --context-pack /home/me/packs/EXACT_PACK_ID \
      --context-pack-id EXACT_PACK_ID

Both values are required. A new admission validates the pack identity and source
freshness. Packs are exclusive with --from-prefix, --from-branch and
--project-bases: changing a saved prefix requires a new root, not an appended
replacement for its initial instructions. The existing saved launch retains the
path/identity, and its configuration digest is bound into the workflow ledger.

Use branchwrite resume RUN_STATE for admitted work. Resume retains its original
canonical COW root even when reference source files later change. Refresh the
pack and start a separate run when new work should use updated references.
Existing tips are never silently rebased. Automatic refresh/adoption is still
unfinished; neither the model nor a pack grants new execution capabilities.

Executed CPU/HTTP coverage uses the actual CLI subprocess and original launcher
fixture assertions, including a changed source between code and resume. It does
not establish installed-wheel or real-GPU qualification for these new options.
The interruption boundary between root publication and initial workflow admission
still needs a separate recovery campaign; the demonstrated resume has an admitted
workflow ledger.

## Interrupted acknowledged bootstrap

The client now reads an acknowledged original context-root result from its
existing operation journal when a process stopped before initial workflow
admission. It validates the original endpoint/root/profile and does not reread
changed reference files or send the root request again. A CPU HTTP regression
actually exits the CLI process with code91 immediately before Interpreter.start,
changes the reference source, and resumes successfully with the same root record.

A pending or unrelated bootstrap intent is rejected without resend or rendering.
Explicit reconciliation for pending pre-workflow bootstrap operations is still
unfinished: the current reconcile command owns pending model frames, not this
earlier setup boundary. The diagnostic names the original bootstrap operation;
do not work around it by changing IDs. This test is not power-loss or GPU-crash
qualification.

## Explicit recovery of a lost bootstrap acknowledgment (dev23 source)

The existing branchwrite reconcile STATE --operation-id ORIGINAL_ID command now
also supports the exact bootstrap owned by a saved launch before workflow frames
exist. It derives that operation ID from the frozen launch, validates its retained
context intent, and asks COW for durable commitment proof. Only then may it replay
the original bytes to recover the original root receipt. Reconciliation leaves the
workflow ledger unchanged; ordinary resume admits the workflow afterward.

An unknown or uncommitted operation returns unresolved exit4, leaves its journal
pending, and performs no new root work. Unowned IDs are refused. A changing
reference source does not rebrand the saved root. COW's modern persisted-root
lookup supports reconstruction and optional checkpoint eviction; legacy roots
without durable receipt metadata remain unsupported. No alternate history or
operation journal was added.

The CPU HTTP regression actually exits the CLI with92 after reading a committed
root response but before the journal can acknowledge it. It then changes source
text, reconciles, and resumes. Source CLI/recovery tests34/34 pass. Installed dev23 has now passed a bounded
real-Q8 restart and coding run:15780prefix tokens restored without recomputation,
explicit original-ID reconciliation, then autonomous repair with independent
tests. See validation/project-base-three-builds-20261019-v1/dev23-q8-restart-coding.
Earlier failed harness/backend attempts remain recorded. This is not broad
coding-agent or numerical-gate qualification. Dev22 remains installed unchanged.
