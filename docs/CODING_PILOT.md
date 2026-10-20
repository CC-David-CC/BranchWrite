# First COW coding pilot

The current client-test environment also needs COW's Jinja2/MarkupSafe template
dependencies for the actual image HTTP/store fixtures. On llm-60 these are
Jinja2 3.1.6 and MarkupSafe 3.0.3, installed in the isolated client environment
alongside its existing Pillow/Playwright. The inference environment is unchanged.
Loss/recovery tests deliberately withhold actual completions; they keep model
quality and durable request mechanics as separate verdicts.

The optional H00 JSON Schema experiment now passes the actual Q4 CLI create/read
path and unchanged protected checker. Select `--arms json_schema` in the enclosing
H00 campaign. Existing coding arms and the canonical workflow remain unchanged.
See [executed H00 JSON evidence](../validation/H00_JSON_Q4_2026-10-17.md) for
test counts, retained failures, reproduction, fingerprints and private backups.

This bounded harness tests the first useful integration. It is not the complete
BranchWrite interpreter or product qualification. The application and COW remain
separate repositories. COW owns model state; the host owns execution permissions.

The harness prepares a context through CowClient, asks for one `.bw` TEXT literal
containing a proposed replacement file, checks its framing and consumed EOS,
freezes its exact bytes and preimage, then uses the registered executor to apply
the permitted edit. Protected tests run in the isolated Linux process boundary.
Their actual output returns to the same COW branch as a new user turn. The model
then describes the observed result. There is one bounded proposal, no automatic
repair, and no arbitrary shell command or model-declared success.

The deliberately broken add and multiply fixtures have fixed protected tests.
The example shows an independent negate repair. Run both fixtures in four arms:
baseline, one example, GBNF, and both. Each arm has distinct operation IDs,
workspace, native context and evidence directory. Grammar constrains framing;
it does not contain the correct patch. Use the same task, model, sampler and
output budget across arms. A passing baseline still gets all four comparisons.

Register the `LiteralContract("replacement", 32768, 256, 4096).gbnf()` grammar
as `BW_REPLACEMENT` and `LiteralContract("report", 8192, 64, 4096).gbnf()` as
`BW_REPORT` in the existing COW server grammar registry before the campaign.
The runner saves its exact grammar source next to each result for comparison
with that pinned registry. A missing state is an explicit server rejection.

Run on llm-60 using its verified interpreter and an owned, pinned COW service.
Keep the ordinary chat server off. The first GPU coding campaign used HTTP.
The assembled client subsequently passed 19 CPU conformance tests against the
combined COW runtime through actual HTTP and CLI subprocesses. That includes
exact machine results and revision-checked rejection; it does not establish
real-GPU coding parity through the CLI.

Example invocation after setting `COW_API_KEY` in the calling environment:

```sh
PYTHONPATH=. /home/dflanag3/src/Strata/.venv/bin/python -B tools/run_cow_coding_pilot.py \
  --url http://127.0.0.1:PORT --endpoint-pin ROOT_OWNED_MANIFEST_DIGEST \
  --source fixtures/coding/add --edit-path src/arith.py --name add \
  --task 'Make add return the sum of its arguments.' --arm baseline \
  --output /home/dflanag3/spatial-artifacts/UNIQUE_CASE --eos-token ACTUAL_PROFILE_EOS
```

Read EOS IDs from the exact pinned model profile. Do not copy a guessed token ID
from another model. The endpoint pin is out-of-band provenance, not an identity
attested by the current HTTP status route. Do not put API keys in evidence.

The result separates structural validity, protected-test success and a narrow
report rubric: it requires the file name, the observed pass/fail word and absence
of the opposite word. This lexical rubric is not a general semantic truth oracle;
retain actual reports for review. A legal wrong patch is a task failure even when
its grammar and report are valid. A failed report cannot change a passed test or
make a failed test pass. The command exits successfully only when the task passes
and the report meets the rubric.

Whole-request timings include client and durable state work. They are not native
decode TPS or TTFT. Keep startup, native timings, pool work and source fingerprints
from the enclosing COW campaign; never infer them from character counts. The
proposal/report token counts are consumed native token counts, including EOS.
Opaque `.cow-answer` files retain native timing fields and actual token IDs.
The scripted-client CPU checks prove orchestration and real tool boundaries only.
The first real-model results are recorded in
[`validation/CODING_PILOT_Q4_2026-10-16.md`](../validation/CODING_PILOT_Q4_2026-10-16.md).
That campaign used the earlier qualified HTTP runtime; new combined CLI/control
coverage remains separate.

The enclosing campaign can select `--transport http` (the default) or
`--transport cli`. CLI selection uses the exact machine-result client with the
frozen COW runtime's `tools/cow_cli.py`, a separate operation journal and CLI
state directory for each case, and the same pinned server. It does not scrape
human CLI display text or silently fall back to HTTP. Both transports execute
the same fixed tasks, four arms and protected tests. Transport selection and
invalid-choice rejection passed 11 focused pilot CPU tests at
`branchwrite-cli-coding-20261016-v1/green-run-v1` on llm-60, following the
preserved failing two-test RED. The subsequent real-Q4 CLI campaign completed
all eight cases on combined COW v16: four constrained cases passed protected
tests and feedback; four unconstrained cases were rejected for framing. Service,
native worker and command/wrapper exits were all zero. See the CLI follow-up
section of the executed result report for pins, timings and limits.

On an uncertain request or interrupted harness, preserve its directory and
original operation journal. There is no automatic tool redispatch or implicit
replay. Full crash-stage recovery, multi-client ordering and the 339 product
obligations remain separate work.

The campaign now validates the actual selected native executable before server
launch. It reads `execution.sut_command[0]`, requires its exact path in the
profile's `native_build.sha256` inventory, hashes the executable and rejects a
mismatch. Thirteen focused pilot CPU tests passed, including changed-file and
missing-pin rejection. Older raw campaigns have a null `native_binary_sha256`
field because the runner looked for a nonexistent scalar profile field. Their
separate checked-in summaries record the independently verified executable
hash; the original raw evidence has not been rewritten.
