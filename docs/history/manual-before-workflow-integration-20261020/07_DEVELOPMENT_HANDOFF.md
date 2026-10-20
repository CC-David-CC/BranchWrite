# Development handoff: simple client startup, 2026-10-20

Goal remains a standalone coding agent using Context COW branches and saved prefill. These changes repair setup; they do not complete the goal.

## Current source and package

- Client, llm-60: /home/dflanag3/src/branchwrite-beginner-flow-20261020
- Client branch: work/beginner-flow-20261020
- Client private Git: box-git:/srv/data/git/BranchWrite.git
- Server, llm-60: /home/dflanag3/src/context-cow-client-setup-20261020
- Server branch: feat/client-connection-info-20261020
- Server private Git: box-git:/srv/data/git/private_context_cow.git
- Installed client, llm-49: /home/dflanag3/spatial-artifacts/branchwrite-dev29-client-setup-20261020/installed-check/venv/bin/branchwrite
- Wheel backup: box-git:/srv/data/git/private_context_cow.evidence/branchwrite-dev29-client-setup-20261020/branchwrite-0.1.0.dev29-py3-none-any.whl
- Wheel SHA256: c6e0c9d3260316a788d9d92c4f22323e374060807f033e89ce612c595dac36ad

The Windows checkout is an older archive. Windows performed SSH/transport only; no source artifacts were placed there.

## Executed evidence

The previous launch stopped at a missing connection directory. That observation determined the next action.

New setup: authenticated GET /cow/info, private key storage bound to the exact connection, automatic first-run setup, stored-key code/resume/reconciliation/base support. Existing explicit environment credentials remain supported. Guided incomplete/malformed results now return nonzero. HTTP redirects cannot forward credentials or transform an uncertain mutation into a retry.

159 selected tests passed, 0 failures/errors/skips. The real COW CPU integration connected through a subprocess, admitted a context and grammar, then resumed with the same saved setup. This test uses the actual coordinator/store/HTTP path and a deterministic CPU backend. It is not language-model or GPU evidence.
20 installed-package startup/setup tests passed on llm-49/Python 3.14.4 without source imports. Existing fresh-wheel controls created an actual file and ran a bubblewrap-isolated shell with confirmed worker retirement. Full test IDs and source digests are in validation/client-setup-20261020/with-redirect-fix/result.json; installed results are adjacent.

Failures retained: test-first missing implementations, false-success exit codes, normal HTTP redirect behavior, an initial build environment missing setuptools, and a CPU integration attempt using an interpreter without regex. System Python built the wheel successfully; the pinned server test environment ran the CPU integration. These are engineering issues, not model-training examples.

The earlier unrestricted full-suite attempt remains incomplete evidence: 1308 methods, 225 errors and 1 failure with missing fixture/dependency setup. This turn ran the bounded relevant suite with explicit dependencies; it does not relabel the old broad run as passed.

## Historical dev29 deployment check

No native/GPU process or ordinary chat server was started. The original pinned Q8 profile correctly REJECTS the changed server source with Runtime source fingerprint mismatch: serve/cow_http.py. The exact read-only check is in the COW validation/client-setup-20261020/runtime-source-check.json.
Before a live trial, prepare a separate profile that binds the changed source with its new execution identity, preserve old profiles/checkpoints, and run that candidate's startup verification. Do not update old hashes in place or bypass the guard. A live admission/autonomous task remains untested for dev29.

## User experience still unfinished

The current wizard asks for read/edit/create paths and a real verification command. It is not yet the requested simple conversational coding experience. Next work is project inspection and a concise host-owned proposed plan, safe new-file admission, ongoing conversation/queued steering, and guarded application in the user's chosen working directory. Preserve immutable launch/ledger state and operation reconciliation throughout. The existing low-level launcher remains the runtime; do not build a second workflow representation.

Continue with test-first admission/UI work. Use the installed client on llm-49 for client-side checks, with COW on llm-60 when live work is authorized. Keep all backup/publication private.


## Interactive launch update

The owner requested opening BW, then requested direct LAN access and opt-in key saving.
The dedicated Q4 service is now on llm-60 at http://10.0.7.68:8099, authenticated,
with a fresh store and separately derived profile under
/home/dflanag3/spatial-artifacts/branchwrite-dev29-live-q4-20261020.
The original Q4 profile and old checkpoints were not modified. Source closure,
model hash receipts, native hashes and hardware passed preflight; the native
service reported ready. This is startup evidence, not a completed coding run.

Dev31 changes first-run key handling: save only with --save-api. An in-memory
callback carries the first hidden prompt into the same guided run. Optional
saved keys retain exact-connection binding. This is on the beginner-flow branch;
it does not claim integration of the separate dev30 project-context work.

Dev31 validation completed: 163 selected tests passed, zero failures/errors/skips,
40.14 seconds, source unchanged throughout. This includes real PTY, HTTP and
CPU COW integration; it is not a new model-coding or G-gate qualification.
Evidence: validation/client-setup-20261020/save-api-opt-in/full/result.json.
The failing default-key-persistence test is retained in save-api-opt-in/red.txt.

Installed dev31 on llm-49:
/home/dflanag3/spatial-artifacts/branchwrite-dev31-api-opt-in-20261020/venv/bin/branchwrite.
Its wheel SHA256 is e1d19faec4a59f9034daa8de38bdf83ccfba3591bf3fbf7cdf9ad8b4a250550a.
The interactive launch connected over the LAN using a single-use private FIFO
to carry the key in memory; the FIFO was removed and no credentials.json was
created. The client runs in /home/dflanag3/projects/branchwrite-first-project.
No coding task had been submitted at the connection check.
Server key material remains in its private runtime directory and is excluded
from Git/evidence backups. A later manual client run will ask for the key unless
it is supplied in the environment or explicitly saved with --save-api.
