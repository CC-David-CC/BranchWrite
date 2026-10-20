# Basic Agent Loop Ladder: integration review

Reviewed the owner's `branchwrite-workloads/basic-agent-loop-codex-handoff-v0.1.0`
against the actual BranchWrite coding pilot and current Context COW implementation.
All 122 supplied files match `FILES.sha256`; there are no missing, changed or extra
files. Manifest SHA256: `12a60740aeb1eee5f6cc23071bb54583f94f5cb633f574e355d6f39e0c0631a3`.
The input package, protected checks, expected answers and acceptance records are
unchanged. This review has made zero model calls and executed no candidate code.

The ladder is suitable for finding real integration failures. Its initial scope
is H00-H02. Its supplied 47 offline/inline passes do not qualify our client. Its
reported browser policy failure belongs to its preparation environment; whether
our browser can navigate remains to be tested here. There is no reason to begin
H03-H12, new samplers, branching research or a replacement runtime first.

| Target | Existing pieces | Actual gap and next distinguishing check |
|---|---|---|
| H00 file tools | `branchwrite.execution.Executor` copies owned workspaces, checks grants, captures artifacts and replaces existing file contents. | It exposes no registered general create/read operations. Add the smallest bounded operations at this existing boundary, then create `hello.txt` and read actual bytes through those operations. A host code block or direct oracle write does not qualify the client. |
| H01 render | Chromium is installed on llm-60 at `/snap/bin/chromium` / `/usr/bin/chromium-browser`; Pillow is available. | The selected `/home/dflanag3/src/Strata/.venv/bin/python` has no Playwright. BranchWrite currently has no browser tool interface. Qualify the actual browser tool against the supplied immutable source, real navigation and a 640x480 screenshot. Do not substitute inline HTML. |
| H02 image-only observation | Current COW CLI/HTTP has real image upload, native embeddings and image-aware continuation evidence on Q4. | `branchwrite.cow_client.CowClient` currently exposes text preparation/questions, not an image-upload/ordered-parts interface. Extend that client using the actual COW upload and typed-input contract. Prove server acceptance of the exact screenshot before interpreting model answers. No generic chat or text-only fallback. |

The trusted `tools/lab.py doctor` was run on llm-60, with command/wrapper exit0.
It reports Python3.12.3, Playwright false, Pillow true, and no native client/model
contact. Chromium path discovery does not establish launch, navigation or sandbox
qualification. No package/browser was downloaded, service restarted, privileged
command run or global configuration changed for this workload review. The pack's
AGENTS.md explicitly says "No auto-install, package download, browser download";
any needed installation requires owner authorization rather than a hidden retry.

Use the supplied verifier as a protected oracle, not a competing tool runtime.
Candidate-visible inputs must include only the selected small workspace and task.
H02 observers receive only neutral screenshot bytes/opaque handles and the neutral
question; no HTML, expected side, references, verifier output or prior answer.
Keep transport acceptance, interpretation and mechanical checks separately recorded.
The existing finite grammar may admit LEFT, RIGHT and NOT_VISIBLE without encoding
which is correct. No new sampler is needed.

Initial allocation remains one selected target, one generation/observation and at
most one optional repair, with every attempt retained. H05 later requires distinct
before/after image observations, exact source lineage, one bounded edit and protected
verification. Do not mark H05 from a reference screenshot or the coding pilot below.

Related current evidence: the existing BranchWrite CLI coding pilot completed eight
real Q4 cases on the frozen image-capable COW build. The four GBNF/constrained cases
passed real protected edit/test/feedback; the four unconstrained cases were rejected
for formatting and not applied. Overall status is MODEL_OUTCOMES_RECORDED, not a full
pass. The service/native worker exited0. Separately, 32 CPU client/pilot integration
tests passed. Those results establish a useful starting boundary, not H00-H02 passes.

Review evidence is external under
`context-cow-vision-artifacts/BASIC-LOOP-INVENTORY-2026-10-17.json` on the controller
and `/home/dflanag3/spatial-artifacts/cow-vision-20261016-v1/basic-loop-doctor-run-v1/`
on llm-60. NEXT: add and test the missing H00 file operations in the existing executor,
then advance only when the actual-client result is source-bound and verified.

Owner-approved dependency follow-up: Playwright and Pillow are now installed in
`/home/dflanag3/spatial-artifacts/branchwrite-client-env-20261017-v1`, a dedicated
BranchWrite client/tool environment. COW's inference venv is unchanged. Reuse the
installed `/snap/bin/chromium`; no browser was downloaded. The install receipt
and exact dependency lock are adjacent validation files. The client-environment
`doctor` now reports both libraries present. This clears the dependency gap,
not the missing browser tool, browser qualification or image client integration.