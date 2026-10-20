# BranchWrite GOLDEN PATH

GOLDEN PATH is a saved project notebook that the model can continue from. Its
beginning holds the goal and useful examples. Later pages hold observations
from the host: which command ran, what passed, which file hash was tested, and
what remains uncertain. Another worker can start from a saved page of this
notebook. Updating the notebook does not change that worker's saved starting
point. More summarizing costs time; measure whether the better guidance helps.

## Initial implementation

`branchwrite.golden_path.GoldenPath` uses the existing CowClient, authenticated
CLI/HTTP, immutable histories, controller state and branch references. It adds
no transcript database, second history, background scheduler or global latest
alias. This is an integration primitive for the existing host interpreter,
not the complete v0.6 runtime.

1. `start` loads a stable purpose and host-reviewed working examples as a closed
   context. These remain at the beginning of its canonical model input.
2. The host creates `Observation.from_bytes(...)` records from actual evidence.
   Each names its observation key, evidence/operation ID, SHA256, byte count,
   statement and time, with optional expiry. Hashing binds bytes; the host must
   verify that its statement follows from those bytes. A model cannot declare
   itself verified by filling in these fields.
3. `refresh` forks the exact prior version to a new candidate branch. It appends
   a deterministic ordered observation manifest, then generates a summary using
   the selected per-generation settings and optional GBNF/JSON Schema state.
   A completed EOS returns a `GoldenVersion` binding parent snapshot, new
   snapshot/revision, operation, endpoint, manifest hash and summary.
4. The existing host ledger chooses which returned version to retain/use.
   Two results may finish out of order; this primitive cannot overwrite a
   newer selection because it owns no shared current pointer. The host must
   perform its normal revision/epoch checks before accepting a result.
5. `fork_worker(version, ...)` starts an ordinary branch from that exact saved
   computation. A worker can investigate or propose an answer. Tool permissions,
   semantic verification, acceptance and publication remain host decisions.

The first summary uses `ask` on the closed purpose context. Later summaries and
worker questions use `append_user` after a consumed EOS. Active partial summaries
must use the existing explicit `continue_`/recovery flow; they cannot be replaced
by a new question or a new grammar. Each branch owns its own mutable controller.

An incomplete summary raises `IncompleteSummary` with its actual committed
partial receipt. The old selected version remains available. A repeated completed
operation may recover only its receipt from the client journal; `SummaryUnavailable`
exposes that result without regenerating. The host must reconcile retained
history to recover answer bytes. Do not give that retry a new operation ID unless
you intend new work.

## Limits

There is no automatic collector of every file, process or ongoing task. The host
selects observations, bounds/redacts them, checks preimages and records evidence.
Time-limited observations reject before a new refresh if expired/future-dated;
historical saved versions still describe their stated observation time. A caller
choosing an old version deliberately receives old knowledge. Revalidate relevant
hashes and leases before effects. A summary may be inaccurate despite valid JSON.

Current bounds: 16 examples of at most 8192 UTF-8 bytes each, purpose 8192 bytes,
64 observations, each statement at most 8192 bytes, manifest at most 256 KiB.
The explicit structured-text load CLI accepts at most 1 MiB and 1024 messages.
This does not qualify a 128K-token example prefix. Changed purpose/examples need
a newly prepared root; changing earlier text does not preserve its old suffix
computation. Compaction, automatic refresh/adoption, full restart/eviction and
multi-client orchestration remain separate work.

Thinking budgets are **not implemented** by GOLDEN PATH. The current executed
profile closes the thinking section and constrains output immediately. See
[the thinking/controller plan](THINKING_AND_GOLDEN_PATH.md). Protect existing
resume guards and test phase/budget state before adding `thinking_length`.

## Run the bounded GPU demonstration

Run on the authorized inference host with a reviewed frozen COW runtime/profile,
an idle GPU, fresh output directory and the pinned client interpreter:

```sh
CLIENT_PYTHON -B validation/run_golden_path_probe.py \
  --cow-runtime PINNED_COW_SOURCE --dependency-root PINNED_DEPS \
  --profile PINNED_PROFILE \
  --h02-result ACTUAL_H02_RESULT \
  --cow-test-log ACTUAL_32_TEST_LOG --bw-test-log ACTUAL_324_TEST_LOG \
  --output NEW_PRIVATE_DIRECTORY
```

The probe owns and stops its authenticated service/native worker. It checks
the supplied successful logs, creates two constrained summaries and a worker
proposal from the older summary, and audits the actual canonical input prefix.
It compares full span identities, not just projected image-padding token IDs.
No candidate command is executed. The worker's allowed investigation choice is
a proposal; it is not proof the investigation ran. Each call goes through the
actual COW CLI. No stateless chat reconstruction or hidden model retry occurs.

Keep raw results private. The report distinguishes completed mechanics from
summary quality, numerical qualification, thinking support and full VC/G gates.
