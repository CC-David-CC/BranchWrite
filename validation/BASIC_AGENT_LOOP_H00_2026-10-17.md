# H00: actual Q4 create/read PASS

The first Basic Agent Loop target passed through the actual BranchWrite machine
CLI, COW HTTP service and pinned Q4 GPU worker on llm-60. One generation produced
the file contents. The host's explicitly granted create tool wrote a new file;
the read tool returned its actual bytes. The independently supplied H00 checker
then passed. There was no repair attempt, candidate execution or model change.

`hello.txt` contained exactly 13 bytes, `Hello, loop.` followed by LF. Created
and read-back SHA-256:
`3c9684133d84aa9fd70b0e61911712040fa1dd994f4fd223ec7053ec8adf1a39`.

This establishes bounded H00, not H01 browser capture, H02 image delivery, H05
repair, a complete BranchWrite agent interpreter, numerical COW equivalence, or
VC00-VC09/G1-G5 qualification. The protected checker explicitly reports native
delivery/agent-loop checks as not_run; the separate actual CLI receipts and native
trace establish the model call here. These distinct evidence paths are retained.

## Change

`Grant` adds separate exact `create_paths` and `read_paths`, defaulting to empty.
Existing edit and test grants authorize neither operation. `Executor.create_file`
publishes a bounded file without replacing an existing name; `read_file` captures
actual bounded bytes in a hashed artifact. Directory handles and no-follow opens
reject link escapes; read checks reject special files, hard links and mutation.

These host actions are serialized. They do not isolate a hostile process sharing
the host uid. Candidate processes still require the registered OS sandbox. A
failure after file publication can leave the file created without a result receipt;
callers must reconcile instead of treating an error as proof of no effects. General
durable workflow idempotency is not supplied by these file operations alone.

The existing coding pilot gains a specific create/read operation; its model prompt
contains only the selected task and format instructions. The existing campaign
owner accepts the pinned supplied pack for H00 and runs its protected checker only
after the file round trip. No protected verifier/source/expected values are inserted
into the model context. The original 122-file workload and assertions are unchanged.

## Executed checks

| Run | Result |
|---|---|
| File-tools RED | 13 errors: missing create/read grant API |
| File-tools + old executor GREEN | 20 passed |
| Client RED | Import error for missing FileTask; zero new cases executed |
| First expanded client run | 59 passed, one missing llguidance dependency error |
| Expanded client, existing pinned dependency path supplied | 60 passed, no errors/skips |
| Frozen final campaign source, focused checks | 60 passed, no errors/skips |
| Frozen source full suite | 300 executed: 298 passed, two failures, zero errors/skips |
| Unchanged base 6bebc2f full suite | 282 executed: 280 passed, the same two failures, zero errors/skips |
| Real Q4 H00 | FILE_CREATED_AND_READ; protected check exit0; BOUNDED_H00_PASS |

The unchanged catalogue assertions `test_active_python_has_no_json_or_pickle` and
`test_active_files_no_json_extension` fail on both base and candidate. The existing
COW wire client imports JSON, and the base already includes two JSON evidence files.
They were not weakened or removed. The H00 implementation introduces no additional
full-suite failures. A full-suite PASS is not claimed. An initial discovery command
also failed before tests because `-t .` requires an importable tests package; the
existing suite uses namespace-style tests. The corrected command omits `-t .`.

The first tmux launcher treated the shell builtin `exec` as an executable argument;
no session, process or run directory survived. The corrected launcher uses one shell
command. This happened before the sole model attempt; both launch scripts remain.

## Runtime and timing

- Model: Qwen3.8-Flash-Next UD-Q4_K_XL, established pinned FP16-KV profile, GPU=[0].
- Native SHA-256: `ae62045f75a8e11ba9d01b4da301d3bb87fe4ff342bab0ea7edc57276377824e`.
- Execution profile: `e729ab6d912d67861176bf0bd719554c5ecd68905b051159b0bc383fbc85d864`.
- COW runtime: frozen `vc07-dry-entropy-source-v8`, unchanged by H00.
- BranchWrite source base: `6bebc2f94b56b96b91d07b839432f2d1ddd6aee8`.
- Executed source archive SHA-256: `3573e9f721a77dcda0c2d67c343d1af27d0fe73879ef5cb21cc277644f4d77c9`.
- Client interpreter: `/home/dflanag3/spatial-artifacts/branchwrite-client-env-20261017-v1/bin/python`.
- Server interpreter: `/home/dflanag3/src/Strata/.venv/bin/python`.
- Startup19.467s; prepare0.825s; proposal1.450s; create/read case2.346s total.
- Proposal12 native tokens including consumed EOS. This tiny run is not a TPS benchmark.
- Service4187624/native4187630 exited0, graceful shutdown; both observed absent.
- GPU wrapper/command exits0/0. Chat server stays off.

## Reproduction and private evidence

Source and run root:
`/home/dflanag3/spatial-artifacts/cow-vision-20261016-v1/`.
The frozen source is `branchwrite-h00-campaign-source-v1`; the GPU result is
`branchwrite-h00-cli-gpu-v1/result.json`. The exact launch driver is
`run-branchwrite-h00-gpu-v1.py`; its arguments, interpreter and native receipts
are retained. Every rerun must use fresh output/source/run directories.

Focused command from that frozen source, with the existing llguidance dependency
path in PYTHONPATH:

```text
/home/dflanag3/spatial-artifacts/branchwrite-client-env-20261017-v1/bin/python -B -m unittest tests.test_file_tools tests.test_execution tests.test_cow_coding_pilot tests.test_coding_contract tests.test_cow_client -v
```

Private raw backup, independently size/hash-verified on box-git:
`/srv/data/git/private_context_cow.evidence/20261017-branchwrite-basic-loop-h00-v1/`.
`evidence.tar.gz`: 3,491,354 bytes,157 members, SHA-256
`242bc742bf6156d4f5bb8a5c4a865a6e06a74fb0cc75bd04110fae38c3b01400`.
It includes source archives, original failed/green runs, client receipts, file bytes,
protected checker output, native traces, profiles and an explicit inventory.
Two derived native checkpoint payloads totaling246,159,544 bytes are excluded and
identified by hash; this is not a numerical-restart archive. Canonical records and
checkpoint manifests are retained. No checkpoint payload has been deleted here.

NEXT: H01 real URL navigation and source-bound 640x480 browser capture; then H02
actual image bytes through the existing BranchWrite client. JSON Schema support in
COW is a separately authorized feature; it must share the grammar/controller path
and pass syntax/schema, recovery and timing checks before claiming support.
