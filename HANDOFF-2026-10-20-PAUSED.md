# Paused handoff ? BranchWrite + Context COW, 2026-10-20

Owner requested a handoff and pause. No new implementation, model runs, independent audits or qualification campaign should start until the owner resumes. This document is the current entry point; earlier evidence is retained, not superseded by inflated pass claims.

## What we are building

BranchWrite (BW) should be a practical autonomous coding client: open a terminal in a project, start a conversation, request a change, steer while it works, inspect a useful result, and resume after interruption. A beginner should not need an agent beside them to supply file names, interpret generic progress messages, locate the output or learn recovery internals.

Context COW supplies the inference service and canonical model histories: shared prefixes, independent continuations, sampling/grammar state, checkpoints, RAM/disk pools and durable native receipts. BW supplies the workflow, project context, tool isolation, local operation receipts, user interaction and reviewed export. BW consumes COW through HTTP; the client on llm-49 does not import or bypass the GPU engine on llm-60.

The larger goal remains several related work trees and thought branches with reusable computation, useful autonomous work and honest recovery. Workload catalogues are probes of that product, not the product definition. One active inference request per GPU is the present scope. Future independent GPU lanes must not require a second history representation.

## Current state in plain language

The engine can do useful bounded work. The human interface is not yet as steerable or self-explanatory as Codex. David's actual dogs-page run worked and he viewed the result. Enter at the last prompt kept the saved work and skipped making an extra copy; it did not discard the page.

The old coding screen David used does not read user messages while its workflow runs. Typing during work does not amend the task and can leave input buffered for a later prompt. New chat queue/stop-add operations exist, but are not integrated into the active coding screen. A chat branch update does not automatically change an already-started worker's pinned source.

## Locations and versions

Everything below is on Linux. Windows is the SSH steering machine; no new source, wheels, test outputs or model files were written to the Windows host in this work.

| Piece | Host and path | Version / branch |
|---|---|---|
| Current BW integration | llm-60: `/home/dflanag3/src/branchwrite-standalone-followup-20261020` | `work/standalone-followup-20261020`; this handoff is committed with the resolved integration |
| Existing beginner base | llm-60: `/home/dflanag3/src/branchwrite-beginner-flow-20261020` | base `8f4779158a63b48bf9e1e0903700ffb8bfd1140a` |
| Incoming private BW integration | private BranchWrite repository | `910a2d2eb8af44c6297fd8747329355b69dfd665`, `feat/explicit-model-reconciliation-20261019` |
| Installed new client used by all four journeys | llm-49: `/home/dflanag3/spatial-artifacts/branchwrite-dev38-conversation-20261020/installed-check/venv/bin/branchwrite` | wheel `0.1.0.dev38` |
| Actual hostname of llm-49 | `r4090` | The new client prints the actual hostname, not the SSH alias |
| David's earlier installed client | llm-49: `/home/dflanag3/spatial-artifacts/branchwrite-dev33-project-20261020/installed-check/venv/bin/branchwrite` | dev33; not silently replaced |
| Candidate COW integration | llm-60: `/home/dflanag3/src/context-cow-bw-conversation-20261020` | `work/bw-conversation-integration-20261020`, `42aae89bc10d1a628489e32dfa50490b156f4601` |
| Actual live COW source | llm-60: `/home/dflanag3/src/context-cow-client-setup-20261020` | `feat/client-connection-info-20261020`, `4b1f8fda22c493a6772896e7e008730f3c767868` |
| Actual live COW runtime | llm-60: `/home/dflanag3/spatial-artifacts/branchwrite-dev29-live-q4-20261020` | existing store/profile/configuration |
| Candidate rollout evidence | llm-60: `/home/dflanag3/spatial-artifacts/branchwrite-dev37-live-q4-20261020` | failed candidate startup, then rollback; not live |
| Four usability journeys | llm-49: `/home/dflanag3/spatial-artifacts/branchwrite-usability-20261020` | completed client runs, incomplete independent audits |
| Proposed independent-audit directory | llm-60: `/home/dflanag3/spatial-artifacts/branchwrite-usability-audit-20261020` | directory created; no independent audit executed before pause |

Private Git destinations only:

- BW: `box-git:/srv/data/git/BranchWrite.git`, explicit branch `work/standalone-followup-20261020`.
- COW: `box-git:/srv/data/git/private_context_cow.git`, explicit branch `work/bw-conversation-integration-20261020` (42aae89b already pushed).
- Do not infer a push destination from `origin`. GitHub requires fresh owner approval; Strata also waits for Niko's approval. No GitHub publication in this handoff.

Preserve the unrelated dirty `tests/test_chat_cli_http.py` in llm-49's `/home/dflanag3/src/branchwrite-model-reconciliation-20261019` (HEAD previously 12d88b2). It is not this integration worktree.

## Built in the current BW integration

- `branchwrite talk`, or `/chat` from the original startup prompt, uses the existing canonical chat operations.
- Two or more conversation turns can lead to `/code TASK`. Coding forks the exact completed conversation tip into its own workflow branch.
- Pending replies, active controllers, unsent queues, changed tips and incompatible profiles are not silently admitted as a coding source.
- `/history`, `/status`, `/continue`, `/reconcile`, `/exit` and exact chat resume instructions exist.
- Whole-project file scope is the simple default. Work still occurs in an isolated copy with a reviewed export boundary.
- API key stays in memory unless the user explicitly chooses `--save-api`.
- Startup identifies the client machine and explains that project files live there, while inference is on the server.
- Durable project/operation receipts, context refresh, chat queue bundling and stop-add pieces from the private integration are included. Several queued messages form one next user turn, as requested by David.
- Beginner/manual documentation was updated. See `docs/manual/00_START_HERE.md`, `06_FIRST_TASK.md`, `07_USER_CHAT.md`, `08_FRIEND_FIRST_RUN.md`.

Limits: the new interactive loop is synchronous; queue/stop-add requires another terminal. Coding does not yet accept live steering, does not automatically return to a conversation with its result, and does not automatically put worker results into the user-conversation tip.

## Executed tests and honest outcomes

CPU integration: **296/296 PASS**, 0 failures, 0 errors, 0 skips, 86.771 seconds. Source fingerprints were unchanged during the suite. This covers client setup, real PTYs/subprocesses, CPU COW HTTP/admission/recovery, chat and exact-tip handoff. It is not GPU or G1?G5 qualification.

Evidence: `validation/standalone-followup-20261020/dev38-cpu/result.json` and `tests.txt`. Earlier red runs, initial merge failures and the 295-test intermediate pass are retained in the same directory.

Paired COW integration: **G0 51/51 PASS**. Evidence is committed in its repository under `experimental/branching_context/evidence/runs/bw-conversation-integration-20261020/`. Original cumulative G1?G5 remains unqualified. No gate percentages are newly measured by these usability tests.

Clean dev38 installation plus real bubblewrap file/shell boundary probe passed on llm-49. Wheel SHA-256:
`05a2ef7d7fe9334fe7a12dc2e02c7a48d3b7ebaeed212d1072cbd0b520cb33f1` (231,498 bytes).
The installed package does not bundle the inference engine or tests. Package manifests remain in the dev38 artifact directory on both hosts.

The four live journeys used the installed dev38 client, actual Q4 HTTP service and unmodified task prompts. No human supplied code fixes during those journeys. All original fixture project directories remained unchanged; no API key was saved. **An exit code of zero or a model-selected check pass is not independent task acceptance.**

| Journey | Elapsed | Observed result | Still required |
|---|---:|---|---|
| U01, beginner dogs page | 121.76 s | Conversation led to index.html with yellow background, three dog cards and Woof button; selected checks passed | Independently click the real button, check visible result and phone overflow in isolated Chromium |
| U02, researcher mean function | 236.73 s | Repaired mean.py and added tests; recovered from an actual read-only `__pycache__` test failure without help; selected checks passed | Independent numerical/edge-case checks using a sandbox and hidden holdout cases |
| U03, household checklist | 74.85 s | No coding run started. Model produced a long answer; one `/continue` still left controller active; `/code` was rejected | Fix repeated budget status and harness logic; shorten the conversation behavior; rerun the same task |
| U04, fleet SSH/SCP | 193.02 s | Requested remote task did NOT complete. Model reported failed SSH/SCP/DNS honestly. Only local prerequisite check passed | Expose final report correctly; define separately authorized fleet tools and test actual remote receipts |

U03 has two problems: the UI checks budget state after `send`, but not after `/continue`; the harness relies on the pause message and advanced to `/code`, then exited after rejection. Do not blame this entire outcome on model capability or call it a successful household task.

U04 is a concrete presentation/acceptance gap. The model's final report begins ?Not done. I attempted the remote operations, but both failed.? The guided UI hid that report and printed ?BranchWrite ran its chosen checks successfully.? The recorded verification covered presence of the local file, ssh and scp, not successful remote work. A read-only check found the requested destination `/tmp/branchwrite-usability-U04/fleet-note.txt` absent on llm-60. The isolated tool environment has no network or host credentials and is not yet a fleet-administration capability. Do not remove isolation or hand over arbitrary SSH credentials to make this probe pass. No software installation was tested in this campaign.

Read-only extracted outcomes, final model reports and selected-check scope are in `validation/standalone-followup-20261020/usability/pause-observations.json`. Raw terminals and canonical workflow logs remain in the llm-49 artifact tree. The top-level `result.json` is execution evidence, not a pass summary.

Conversation mode also printed lengthy model reasoning and code, even after a request for a brief explanation. A beginner should not have to interpret this. Presentation must use explicit controller/phase metadata; do not blindly strip literal `</think>` or tool-like text. Literal tag handling is an existing correctness concern.

## Important deployment failure and rollback

The candidate COW source passed CPU tests but did not load the real model successfully. Its runtime profile updated source/native-build provenance while retaining the old execution_profile_id. The backend correctly rejected it with **?Strata execution profile fingerprint mismatch.?** Candidate PID907730 exited. The original pinned server source/profile/store were restored and ready before the four journeys.

Those real-GPU journeys therefore validate the new client against the **older live server**, not candidate42aae89b. Explicit cancellation/128-byte-name/metadata candidate changes are CPU-tested, not newly GPU-qualified here.

On resumption, read the actual identity function in `context_time_travel/strata_backend.py`; `_validate_execution` expects `_digest(dict(build=native_build, execution=execution, hardware=hardware))`. Use the implementation, not guessed JSON serialization. A changed execution identity needs honest client pinning and an isolated store/profile trial. Do not bypass the identity guard, rewrite old receipts or pretend checkpoints from different profiles are interchangeable. No CUDA rebuild was required by these Python-only changes; no new native executable was built.

Retained rollout files: `preflight.json`, `server.log`, `rollback.json`, `run_server.py`, `profile.json` in the candidate runtime directory. Small nonsecret copies/excerpts are in `validation/standalone-followup-20261020/candidate-rollout/`.

## Runtime at pause

- Four journey runner and client processes have exited: recorded PIDs2412812,2413276 and the old user client2411261 were absent from /proc at pause.
- Dedicated Q4 API remains running on `http://10.0.7.68:8099` with existing configuration; ordinary browser/chat server stays OFF. Do not restart it.
- Last observed dedicated wrapper/native PIDs:911143/911158. Recheck process identity, not just PID, before any future lifecycle action.
- Endpoint uses the existing private API key file; do not print it, copy it into evidence or commit it. Keys were consumed from a private FIFO for the journey runner, then the FIFO was unlinked.
- Actual model: Qwen3.8-Flash-Next UD-Q4_K_XL, FP16 KV, GPU[0], context capacity98304, prefill512. This is the existing serving profile; the recorded native invocation includes `--spec 2`. Do not describe it as a new no-speculation qualification or alter it silently. No MTP training/work was performed here.
- Model contract: `387bbc46f184b148ff455b50a9037132da32d6fed83abba7eb63e57b33f12b53`.
- Live execution profile: `62a8bc71db2436477fc6e5c010d4357287034c04ea41123a887418694a5d42b6`.
- RAM pool24GiB, disk pool64GiB, idle expiry1800seconds from the retained runtime configuration. Do not expand testing into long runs while paused.
- The dogs-page HTTP preview and Windows SSH tunnel were closed at David's request. No new preview or tunnel should start automatically.

David's saved page:
`llm-49:/home/dflanag3/.local/state/branchwrite/runs/bw-make-a-simple-website-static-htm-84ea2b92/world/workspace/index.html`
SHA-256 `0e016fe4d71a2b1226a2f549745c3e0a944f4f80ef1a29aacffa9126f8494718`,4933bytes. No extra project copy was made after Enter. It is on llm-49, not WSL and not the Windows filesystem.

## Ordered next steps after explicit resume

1. **Make reporting truthful and useful.** Render the actual final `finish` answer from canonical records before the file-copy prompt. Show which checks ran and distinguish verified checks from completion of the user's task. Add a regression based on U04: failed remote operations plus a passing local prerequisite must not be presented as a completed transfer. Do not classify success by English substring matching; plan an explicit bounded outcome/disposition contract. Preserve existing result records and version any necessary contract change.
2. **Finish the observations already collected.** Independently audit U01 with actual Chromium interaction and mobile layout, U02 with independent arithmetic/edge checks, and record U04 as unsupported remote execution. Audit model-authored code inside the existing execution boundary. Do not claim researcher-level capability from one mean-function exercise. Preserve old runs; no rewriting failures as passes.
3. **Repair conversation controls.** After every `send`, `continue` or reconciliation, inspect canonical controller state and show whether the answer is complete or paused. Correct the journey driver to follow actual state instead of a one-time message. Retest U03. Add an EOF/Ctrl-C test at the `/code` task prompt: the outer handler currently risks saying nothing was sent despite an earlier saved conversation. Fix presentation of reasoning/final text through explicit phase information, not tag heuristics. Keep the requested4096 default thinking allowance and existing successes intact.
4. **Add real same-terminal steering.** Keep a visible input area while the coding worker runs. Persist new messages locally before acknowledging receipt. Offer (a) queue for the next safe step and (b) stop-and-amend. Combine pending messages in arrival order into one instruction bundle. Bind each bundle to canonical workflow/COW operation IDs and a defined consumed-state boundary. A running tool is an effect, not disposable text: settle or reconcile it before changing course; never repeat it because the user pressed stop. Test input during model output, during a tool, between steps, after completion, during lost acknowledgment and after client restart. Assert that queued text cannot accidentally answer the export YES prompt. Keep coding and user-conversation tips distinct and show which instruction version the worker has adopted.
5. **Show meaningful progress and return to conversation.** Name the file/action/check being performed, show the final answer and changed files, allow a follow-up edit to the existing work, and explain remote output location. Preserve the existing guarded project export; the old request did not authorize replacing the live project blindly. Agree on a simple viewing/export path instead of requiring ad hoc tunnel setup each time.
6. **Qualify the paired server candidate.** Correct its execution fingerprint using the real identity function; use an isolated pinned profile/store. Run a small GPU conversation/cancel/recovery/handoff trial before switching any user session. Existing CPU296 and G051 results remain valid within their recorded scope; do not relabel older-server journeys as candidate results.
7. **Rerun the four user journeys end to end.** Start from clean client state with the corrected UI. Use actual installed package over LAN, not source imports bypassing HTTP. Preserve input tasks and independently check artifacts. Add steering instructions mid-run and an interruption/recovery case. Test that the model can report a blocker without disguising it as success.
8. **Only then expand fleet capabilities.** Define host-selected, explicit remote command/transfer destinations, identity/host-key verification, no secret exposure, bounded file transfers, receipts, timeouts and recovery. Installation/privilege changes need distinct scope. The current read-only no-network tool environment is a coding boundary, not a remote admin shell. An approved feature can add capabilities without weakening every coding session.

Other outstanding work remains: broader BranchWrite workload catalogue, image/controller combinations, complete original G1?G5 campaigns, current sanitizer/soak/pressure matrix, later Q8 end-to-end requalification, training/example curation. None was completed by the four short journeys. Prioritize a coherent human-facing loop before more repetitive inference benchmarks.

## Guardrails and restart commands

Read AGENTS.md in the selected worktrees. Linux hosts do edits/builds/tests. Windows uses `python` if a local interpreter is ever necessary; never `python3` on Windows. Keep one active inference job per GPU, inspect ownership first, and preserve unrelated dirty files. Do not start the ordinary chat server. All backups private LAN only. No changing frozen equations/tolerances, no mocked-GPU pass claims, and no silent replay where strict restore is promised.

Read this file from the steering terminal:

```powershell
ssh llm-60 cat /home/dflanag3/src/branchwrite-standalone-followup-20261020/HANDOFF-2026-10-20-PAUSED.md
```

After the owner explicitly resumes, begin with repository status and the recorded outcomes. The CPU runner is `tools/check_client_setup.py`; read its actual arguments before rerunning. It needs the paired COW source and its Python dependencies. The real journey runner is `tools/run_user_journeys.py`; do not start it with a command-line API key. Its current pause-detection bug must be corrected before the household repeat.

Suggested resumption message:

> Resume from HANDOFF-2026-10-20-PAUSED.md in llm-60:/home/dflanag3/src/branchwrite-standalone-followup-20261020. Keep Linux execution and private box-git only. First expose the canonical final report and separate selected-check success from actual task completion; then finish independent audits of the existing journeys and repair conversation-budget handling. Build same-terminal queued/stop-and-amend steering through the existing workflow and COW receipts. Preserve the current live server until the candidate fingerprint and isolated GPU trial are correct. Do not start unrelated long campaigns or the ordinary chat server.
