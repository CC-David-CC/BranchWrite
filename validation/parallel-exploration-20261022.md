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
