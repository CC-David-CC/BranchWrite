# Q4 coding pilot: executed results

The first bounded real-model campaign completed on llm-60 using the qualified
Qwen3.8-Flash-Next UD-Q4_K_XL profile. It used the earlier frozen COW HTTP runtime,
not the subsequently combined seed/STOP/machine-CLI candidate. The ordinary chat
server stayed off. One native GPU worker served all requests serially.

| Task | Baseline | One example | GBNF | Example + GBNF |
|---|---|---|---|---|
| Fix addition | Framing rejected | Framing rejected | Tests and feedback pass | Tests and feedback pass |
| Fix multiplication | Framing rejected | Framing rejected | Tests and feedback pass | Tests and feedback pass |

All eight proposals contained the correct arithmetic change by inspection. The
four unconstrained proposals ended with `END` and omitted the required final LF.
The strict parser rejected them; they were not applied and their post-edit tests
were not run. The four constrained proposals included the LF, passed the real
protected tests in the isolated workspace, and returned a report meeting the
disclosed lexical rubric after receiving the actual test output. The example
alone did not cure framing in these two tasks. This is not a general coding or
answer-quality benchmark, and grammar acceptance alone was not counted as success.

The campaign correctly reported `MODEL_OUTCOMES_RECORDED`, not a full pass.
There were no infrastructure failures. Command/wrapper exits were 0/0, as were
service and native-worker shutdown exits; both recorded PIDs were absent afterward.

## Work and timings

Eight prepare requests resolved to four unique canonical snapshots. Submitted
prefix lengths totaled 2,116 tokens; the four unique prefixes totaled 1,058.
Canonical feedback suffixes added 628 tokens. The native counter recorded exactly
1,686 prefill tokens = 1,058 unique prefix tokens + 628 feedback tokens. Thus the
repeated requests avoided evaluating 1,058 prefix tokens. Checkpoint file-load
bytes were zero. This proves measured prefix reuse across distinct work IDs;
it does not prove a latency win at these tiny sizes (225-304 prefix tokens).

The native process recorded 2,074 forward tokens = 1,686 prefill + 388 generated
tokens including EOS, 308 grammar selections, zero sampling calls, and zero
integrity mismatches. It wrote 2,528,987,960 file bytes during the campaign;
retained native checkpoint files totaled 2,044,828,368 bytes at inspection.
Counter memory values describe the last measurement before native teardown,
not allocations remaining after process exit.

Startup took 20.57 seconds. Tiny 20-text-token constrained proposals took
0.209-0.212 native generation seconds (roughly 94-95 text TPS); unconstrained
19-token proposals took 0.169-0.181 seconds (roughly 105-112 text TPS). Each
condition ran once per task. These short, differing token sequences do not
establish a sustained throughput regression or the validation-overhead target.
Whole proposal calls took 0.75-1.38 seconds, including state and client work.
No TTFT or long-context speedup is inferred. Larger-prefix break-even tests
follow core CLI integration, with small states allowed to remain in RAM or be
recomputed rather than requiring disk restoration on every transition.

## Source and evidence

Raw run and executed source:
`/home/dflanag3/spatial-artifacts/branchwrite-coding-pilot-20261016-v1/`.
The GPU run used `green-source-v1`; full result SHA-256 is
`a080ece0e5ec1592d3b767bf2d54a2e177b4e16b0133328ff17e0fa7275585da`.
Q4 profile SHA-256:
`3551eeb132aeb7642cd3868acb9c940210ec0e9be97018bebff82a907f88b32a`.
Native binary SHA-256:
`c674659df23ace94dfb29023d4f1dec1bd9f4f219df0ddb4802e0300b11ad87e`.
The machine-readable summary, exact model/profile identities, native counters,
source hashes and per-arm outputs are in the COW repository at
`experimental/branching_context/evidence/BRANCHWRITE-Q4-CODING-PILOT-2026-10-16.json`.
No numerical-frontier oracle ran in this campaign; its error is unmeasured.

Private raw-evidence archive:
`box-git:/srv/data/git/private_context_cow.evidence/20261016-branchwrite-q4-coding-pilot-v1/evidence.tar.gz`.
SHA-256: `2bfbda81ace6e0e4f419ba3a2b17159032e1e5fb84146d51db9b8ac62e74fa1c`;
size 9,465,024 bytes. Source and receiver hashes match. It retains executed
source, logs, canonical records and manifests, original profile, and the v2
summary. Native `.state` payloads are excluded; the measured payloads remain on
llm-60. The v3 reuse analysis was derived afterward from the same backed-up
canonical history and terminal counters.

## Subsequent checks and remaining boundaries

Nine scripted-client CPU pilot checks passed on llm-60 at `hardening-green-run`
(command/wrapper 0/0). They execute the real registered test tool and cover
correct/wrong patches, malformed/incomplete output, four-arm controls, rejected
paths, existing output ownership, subset result labels and secret-safe progress
errors. Original missing-module RED and hardening RED (two missing-helper errors)
remain preserved. This is orchestration evidence, not nine extra GPU cases.

The assembled follow-up source passed 38 focused CPU tests at
`candidate-units-v3` (0 failures/errors/skips; command/wrapper 0/0), covering
the pilot, client, executor and literal contract. The frozen exported payload
passed its SHA-256 inventory check at `candidate-manifest-v3` (0/0).
The handoff-only checker actually failed at `candidate-handoff-v3` (1/1) with
`HANDOFF_INVALID: active JSON/pickle dependency`; its assertions were unchanged.

The current branch also contains the newer exact CLI transport. Nineteen CPU
client conformance tests passed against the frozen combined COW v13 source,
using actual HTTP and CLI subprocesses, with command/wrapper exits 0/0. The
complete 278-method BranchWrite suite ran against that runtime: 277 passed,
one failed, zero errors or skips. The failure is
`test_catalogue.CatalogueTests.test_active_python_has_no_json_or_pickle`.
Raw logs are in `full-cpu-v13-cow-v1` under the campaign root above. All executed
client flow tests passed; HTTP GPU evidence still does not establish GPU CLI
coding parity. The inherited handoff-only verifier
forbids every JSON import, including the native COW transport that v0.6 permits.
It has not been weakened to hide that mismatch. Full product acceptance,
durable workflow recovery, exploration samplers, fork/compare/adopt through this
client and COW G1-G5 qualification remain separate outstanding work. The
combined COW seed/STOP GPU probe stopped at its reseed command because the
harness supplied `--revision`, which that CLI command did not accept. This
failure is preserved separately in COW's `gpu-cli-results-v1`; it did not reach
the restart or STOP portion. It is not a logit-comparison failure.

## Actual CLI follow-up

Private BranchWrite commit `74361a6ce6d9d94b4fc6e81217b375bf5cfa1ce5`
subsequently ran the same eight cases through real machine-result CLI
subprocesses, COW HTTP/server and one real Q4 worker. The four constrained
cases passed protected tests and the feedback rubric. The four unconstrained
cases again omitted the terminal framing LF and were rejected without applying
their proposals. This repeats the useful coding flow through the CLI; the
overall outcome remains MODEL_OUTCOMES_RECORDED, not eight task passes.

Runtime: `seed-stop-combined-20261016-v1/combined-cpu-v16/source` on llm-60.
Profile SHA-256: `682b7f8ea85487c0617333636a274e33022c07c57567df9ee8762defb5c5740b`.
Execution profile: `8db64e3cbef0906e7757875483d1c9548d09198a5cd6a999c8329be30e422695`.
The model and native binary are unchanged from the pins above. This source
passed 338 COW CPU checks and G0 51/51. Test-only reseed acknowledgment parsing
is being corrected separately; this coding run did not exercise reseed/restart.

The eight prepare calls again resolved to four canonical snapshots. Native
prefill work was 1,686 tokens: 1,058 unique prefix + 628 feedback, avoiding
1,058 repeated-prefix tokens. Native generated work was 388 tokens including
EOS, with no native checkpoint-file loads or integrity mismatches. Startup was
20.00 seconds. Tiny constrained proposals measured 94.5-95.6 native text TPS;
whole proposal CLI calls took 1.01-1.45 seconds and feedback calls 1.63-1.81
seconds. These one-off, short-output results are not sustained throughput or
TTFT measurements. No fresh numerical-frontier oracle ran.

Raw root: `/home/dflanag3/spatial-artifacts/branchwrite-cli-coding-20261016-v1`.
Command/wrapper exits were 0/0; service PID 3679930 and native PID 3680012
exited zero and were independently observed absent afterward. The exported
95-file inventory passed SHA-256 verification. COW's machine-readable record
is `experimental/branching_context/evidence/BRANCHWRITE-CLI-Q4-CODING-2026-10-16.json`.

Verified private archive:
`box-git:/srv/data/git/private_context_cow.evidence/20261016-branchwrite-cli-q4-coding-v1/evidence.tar.gz`.
Size 14,519,214 bytes; SHA-256
`04a649eed076875e353b160ad11a4cc054fb5eaeeecfcc2bb5069a31c6405907`.
It includes executed BranchWrite/COW source, profiles, raw CLI/counter logs,
canonical records and the preceding seed/STOP v2 harness failure. Native
`.state` payloads are excluded; 2,044,828,368 bytes remain on llm-60. Source and
receiver archive hashes match. No public remote was updated.

## Subsequent executable-fingerprint correction

The campaign runner incorrectly read a nonexistent `native_build.binary_sha256`
field, leaving that field null in the original raw campaign records. The
independent compact summaries above contain the actual verified ELF hash.
Original raw records remain unchanged. The corrected runner resolves
`execution.sut_command[0]`, requires a matching entry in `native_build.sha256`,
and hashes the file before launching the server. A changed or unpinned binary
is rejected rather than recorded with an unknown identity.

Test-first evidence on llm-60:
`/home/dflanag3/spatial-artifacts/branchwrite-fingerprint-20261016-v1`.
The RED ran 13 tests: 11 passed and two errored because the helper was absent.
The GREEN ran 13/13 successfully, with zero failures, errors or skips and
command/wrapper exits 0/0. This metadata correction does not rerun or broaden
the GPU coding results. The previously reported full-suite JSON-import policy
failure remains outstanding.
