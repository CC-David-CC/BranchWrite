# Parallel exploration controls, 2026-10-22

The tests execute the repository's interpreter and ledger, real COW HTTP forks,
real isolated Executor filesystems and verification subprocesses. Scripted
proposals exercise orchestration; they are not evidence of model competence.

Linux validation used Python 3.14.4 and an isolated environment with
llguidance 1.9.1, regex and Jinja2. Relevant commands, with the sibling COW
source and implementation tests on PYTHONPATH:

* `python -m unittest tests.test_parallel_dispatch tests.test_parallel_exploration
  tests.test_interpreter tests.test_model_dispatch tests.test_coding_launcher
  tests.test_coding_review tests.test_project_export tests.test_coding_status
  tests.test_run_cli`: earlier 84-test run passed.
* `python -m unittest tests.test_coding_launcher_http tests.test_full_project_review
  tests.test_coding_reconciliation tests.test_planning_retry_flow`: 26 passed.
* After budget/slot immutability and drain changes,
  `python -m unittest tests.test_parallel_dispatch tests.test_parallel_exploration
  tests.test_model_dispatch tests.test_coding_launcher_http
  tests.test_project_export tests.test_coding_review`: 35 passed.
* Final added drain/slot controls: parallel dispatch and exploration, 10 passed.
* Final selected-workspace review/export addition: exploration, 6 passed.

These runs overlap; do not sum them as distinct tests. No skips counted.

The first exploration test exposed cross-candidate verification contamination:
visible settled sibling outcomes could certify the wrong workspace. Verification
now checks the original frozen tool plan's registry/world binding. The original
passing and failing candidate assertions were preserved.

Final cases cover concurrent effects, stable declaration-order selection,
retaining a failed candidate, rejecting changed files, overlapping world aliases,
pre-admission budget overcommit, owner-only collection and collection of another
known receipt after one collector fails. Selected-candidate review/export reads
the second candidate's exact payload and excludes the first candidate's payload.
The original source is checked unchanged.

Initial validation setup errors included missing import paths/dependencies and
test-fixture directory permissions and cleanup. They were repaired in validation
setup; they are not Wen training failures. Full release certification, real Wen
two-approach execution, crash/restart fault campaigns and federated endpoint
scheduling are not established by this evidence.

## Reconciliation after interrupted integration

The new nested-repeat regression fails against the parent `step_branch` with
`TransitionError: wait is not completely settled`. The repaired implementation
waits for its direct scope's canonical Closed state before resuming the branch.
All seven exploration tests pass on Linux after that change.

The asynchronous progress regression holds a completed worker behind at least
five owner polls. It fails against the previous unconditional notices and passes
when notices correspond to dispatch and completion rather than waiting polls.
An initial broader run exposed an existing test race: waiting for any worker was
mistaken for waiting for both. The test now waits, with a bounded deadline, for
both actual futures before checking their original results and overlap claims.

Final Linux/Python 3.12 run at `5b3a0a2b`:

`python -m unittest test_progress_http test_progress test_parallel_exploration
test_parallel_dispatch test_interpreter`

36 passed, no skips. The parent-function failures are recorded separately from
the final green run. Windows validation could not import POSIX `fcntl`; it is
not counted as a passing run. These CPU suites allocate no GPU.

Two separate real Wen/COW/BW CLI coding tasks also completed with
`verified=true`: small double/triple function repairs, actual file observations,
edits, unit-test execution and finish. Times were 72.62 and 66.07 seconds.
Those runs used the earlier `49294fbc` BW source and the unadapted Wen model;
they are bounded model-workflow evidence, not verification of trained adapters
or two-approach execution. The corrected host grant includes the test files;
an earlier omitted test-directory projection is retained as setup failure and
excluded from model training. Temporary serving used 100 GiB RAM and disk limits,
exited zero and left zero ephemeral sessions.

## Full native two-approach follow-up, 2026-10-23

BW `8b821b0` with COW runtime `10964d0` and Wen 1.1 on llm-60 completed both
isolated approaches, ran each candidate's actual checks and selected the first
under `verified-first`. Both candidates reported verified with different
workspace inventories. The result passed with optional inventory/scheduling/
fastokens disabled and enabled. Completed replay left COW heads unchanged;
operation journals had no pending entries. Source files and frozen launch
configuration remained unchanged. Each owned server exited zero, removed its
ephemeral sessions and released GPU allocations.

An initial setup retained enabled flags in its disabled control and failed
before BW work. A second driver used only 128 interpreter steps and correctly
paused as `step_budget_exhausted`. The successful fresh pair used 512 steps,
below the CLI default of 1,024, without changing the frozen candidate, request
or token budgets. These are operational fixture failures, not model-training
examples or changes to the verification oracle. Full resume execution took
53.69 and 56.22 seconds; these single observations are not a speed comparison.

Answer-free native receipts are in COW's
`experimental/branching_context/evidence/STACK-UNIFICATION-FINAL-20261023.json`.
Cross-host inference federation, adversarial crash/restart campaigns and broad
autonomous task quality remain separate work.
