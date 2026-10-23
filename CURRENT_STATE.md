# Current BranchWrite state

Updated 2026-10-23 after bounded stack integration. Earlier notes are preserved under
docs/history/CURRENT_STATE-before-lan-preview-20261020.md.

## Roles

- BranchWrite: directory-based CLI, tools, workflow ledger, saved file versions,
  steering, queued follow-ups, modes and paired file/context branch controls.
- Context COW: authenticated HTTP service, immutable model histories/controllers,
  movable branch references and optional RAM/disk computational checkpoints.
- Strata: native model execution, called by the COW worker.
- Acceptance harness: launches the actual CLI and independently checks effects.
  Its fixtures are specimens, not the standalone-agent completion definition.

## Current qualification and remaining product work

See [STACK-INTEGRATION.md](docs/STACK-INTEGRATION.md) for authenticated COW
capability admission, bounded Wen/Qwen tool/test/finish runs, pause/resume,
completed replay and Wen's verified two-approach selection. The final focused
BW regression selection passed 158 tests. It caught and fixed a completed-replay
dependency on a live COW server. Optional inventory, scheduling, transfers, GPU
roles and tokenization remain COW settings; BW keeps one workflow ledger.

The wider standalone-agent workflow still needs current-version qualification
on unfamiliar repositories and longer tasks, independent acceptance checks that
cover the requested behavior, combined interruption/reconciliation tests, and
the complete review/export/apply/retry path through a fresh installation. Many
components have individual evidence below; a bounded successful coding run does
not establish general task completion. Writing, browser, CAD and Blender work
need their own task-level acceptance evidence. Model failures remain separate
from infrastructure failures and protected test answers.

## Historical LAN preview setup, 2026-10-20

The following setup entries describe the earlier preview, not current running
services. The 2026-10-23 integration uses separate owned test installations.

The preview COW API was http://10.0.7.68:18099 on llm-60. Its owned Python/native
processes restarted successfully in that LAN smoke. The earlier 8099 service was
stopped cleanly; its store and configuration remain intact. Ordinary chat stays
off. Q4 with FP16 KV is the current development model; Q8 remains deferred.

- Server source: llm-60:/home/dflanag3/src/context-cow-lan-install-20261020
- Server runtime/build/store: llm-60:/home/dflanag3/spatial-artifacts/cow-lan-install-20261020
- Published COW main: c59b053bf9799cdb73b799e8913843773770a3e3
- BW execution-preview tag commit: 7e5c32ce59e768151f73b23c5f9d1f1c84d0859a
- Recommended BW tag: lan-preview-2026-10-20.1
- Current agent worktree: llm-49:/home/dflanag3/src/branchwrite-real-project-loop-20261020
- Private backups: box-git:/srv/data/git/BranchWrite.git and private_context_cow.git

## Executed evidence

The GitHub-installed client in the owned Ubuntu VM created a website and made a
follow-up change after closing/reopening the client and restarting both server
processes. Request times were 220.98 and 142.92 seconds. Four independent browser
viewport checks passed. These are whole-request times, not TPS measurements.
The final startup patch also passed real clean non-admin installation, file/shell
doctor, project launch/connection/help/exit, and 28 focused CPU tests with no skips.
See validation/linux-lan-install-20261020 for source attribution and failures.

No new numerical oracle, logit-error maximum, zero-prefix-work trace or cumulative
G1-G5 qualification was obtained in that installation smoke. G0 passed 51/51.
The standalone-agent goal remains active. Existing-project repair, active steering,
queued coalescing, older-context/current-files exploration, paired selection and
cold-process continuation now have bounded executed evidence under
validation/real-project-loop-20261020. Broader unfamiliar projects/admin,
model-directed browser observation, recovery and stress remain to exercise. Extra browser-worker isolation failed on the audit
host; an independent sandboxed Chromium audit passed under a temporary scoped
permission profile, which was removed. The default client file/shell sandbox passed.

## Installation

Start with docs/LINUX-QUICKSTART.md for the human client, and the COW repository's
docs/CONTEXT-COW-SERVER.md for the operator. The client installs a private Python
base and packages; it does not install a model or COW server. Keys stay in memory
unless --save-api is requested. Keep old runtime folders for admitted old work.
No silent cross-version migration or arbitrary task correctness is claimed.

## Steering environment

Development steering now uses Ubuntu-24.04 in WSL and native Linux SSH.
A dedicated WSL public key was registered and passwordless connections to
llm-49, llm-60 and box-git were executed successfully. Private keys stay in WSL;
strict host verification remains enabled. Builds, inference, client trials and
evidence remain on the Linux fleet. This is not a qualification of BW running
inside WSL: the installed client is being tested in the Linux VM on llm-49.

An earlier repair fixture was invalidated because Windows PowerShell's pipe
encoding replaced Unicode characters with question marks before SSH. Its run
and raw results are retained but do not count as Unicode/model evidence.
The replacement fixture's actual destination code points were verified, and
its independent baseline checker rejected the intentionally broken search.
A direct UTF-8 transport probe through WSL also matched exact code points.
