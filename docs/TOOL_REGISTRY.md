# Registered tools and durable controller dispatch

The model proposes a tool. The host decides whether it is allowed and records
an exact plan before doing anything. A file read gives an observation containing
its world, path and SHA256. Editing or capturing that file must name the same
visible observation. A plan becomes stale if its relevant input changes; changing
an unrelated file does not invalidate a single-file plan. Completion is a request,
not proof that the task passed.

This component connects the existing FrameKernel to the existing Executor. It is
not a second workflow loop, ledger, transcript, CLI or autonomous agent. One host
interpreter owns transitions. Workers only return observations. COW continues to
own native model histories/controllers and numerical checkpoints.

## One tool definition table

ToolRegistry emits JSON Schema, strictly parses complete JSON and freezes plans
from the same definitions: read_file, create_file, replace, run_tests,
capture_page and finish. The host Grant selects exact paths and capabilities;
the model cannot grant paths, shell commands, browser binaries or test commands.
Schema constraints assist generation; host validation always runs again.

File observations bind to an owned workspace. Replace also binds the full source
hash and exact replacement preimage. Create refuses overwrite. Test plans depend
on the bounded complete workspace inventory, including modes/directories. The
inventory is hashed incrementally, so4100 files work without exceeding the typed
codec's per-container4096-item bound. Browser capture runs JavaScript and is an
ACT, not a harmless observation. It returns actual PNG bytes and isolation/source
witnesses, never the protected inspector/verifier verdict. Browser runtimes and
configuration are host-pinned. This remains the existing single-document browser
scope, not general interactive browser sessions or asset navigation.

Frozen plans are canonical typed artifacts, not a new history representation.
Registered definitions bind source, permissions, browser and workspace identity.
Output bytes and actual images become artifacts in the same RuntimeLog and are
returned to the original parent's typed slot by the same FrameKernel.

## Intent, effects and recovery

admit_tool freezes the proposal and atomically admits its child with parent wait.
dispatch_tool writes the original operation intent BEFORE entering the Executor.
Known preflight rejection becomes a durable rejected_before_execution result.
After external entry, errors are EffectIndeterminate, including receipt failure
after a file was actually created. The frame remains unresolved. Reopening and
trying that pending call raises ReconciliationRequired with the ORIGINAL operation
and plan identity; it never repeats a mutation under a new ID. A completed frame
returns its saved result without calling Executor again, even if the world changed.
Explicit reconciliation of unresolved tool effects remains future interpreter work.

A tool finish result does not close its parent or certify acceptance. The host
workflow must process it and independently verify the task. Parent resume is an
explicit kernel transition. Grants, budgets, native controllers and tool results
must not be silently inferred from prose or streamed thinking.

## Current test execution behavior (2026-10-19)

The registered `run_tests` tool accepts ordinary `tests/test_*.py` directories
without `tests/__init__.py`, as well as package-based tests using relative
imports. The project root is importable inside the same read-only OS sandbox.
The runner does not create package markers or alter protected tests. Empty
suites return exit 1 with a no-test-cases diagnostic; discovering zero tests is
not successful verification. Standard-library unittest discovery rules still
apply; this does not claim support for arbitrary test frameworks or layouts.

The normal `branchwrite code` command instead admits the explicit verification
commands supplied by the user with `--test-command`, executed through the
separately granted shell tool. Its tests are not automatically routed through
registered `run_tests`. For a flat Python test directory a suitable explicit
command is `python3 -m unittest discover -s tests -v` on Linux. Select commands
appropriate to the actual project. A successful command receipt is required
against the current workspace; model prose cannot substitute for it.

The interpreter and CLI now exist. The section below records an earlier
component milestone, not the present implementation inventory. Current installed
candidate evidence is in `validation/TEST-DISCOVERY-2026-10-19/`; its broader
regression result retains one historical diagnostic assertion failure, so it is
not a fully green qualification or a general autonomous-agent certification.

## Historical component evidence and integration boundary

Current source passed21 registry +5 dispatch methods and432 total CPU tests.
Actual filesystem reads/writes, sandboxed unittest execution and Chromium capture
ran. The model schema also compiled in existing COW GrammarRegistry with the
TinyByteTokenizer CPU fixture. This is NOT real-model vocabulary or GPU testing.

The pinned constrained JSON emitter uses canonical property order: arguments
before tool. An unsorted forced positive test failed at byte2; its canonical
positive fixture was corrected and unsorted rejection retained explicitly. The
host JSON parser accepts either order. The forbidden-tool negative uses otherwise
valid arguments. No backend grammar change or arbitrary JSON-order acceptance is
claimed. A separate new positive test initially omitted tests/__init__.py, so
actual isolated unittest discovery exited1. The positive fixture now supplies its
package; a negative test preserves and asserts the real nonzero missing-package
result. Existing protected checks and Executor commands were not weakened.

Inspection of COW's current HTTP routes found named grammar_state selection and
startup --grammar-registry, not inline schema admission. The next real interpreter
must use that inspected contract or implement a versioned, controller-safe grammar
admission primitive. Never guess an inline endpoint or silently use unrestricted
generation. Static schema export alone does not establish model-driven operation.

The production step/run interpreter, COW decision adapter and general CLI are
still missing. H00-H06 are bounded scripted/component evidence; H07-H12 and Ubuntu
Agent Baseline are unrun. These components must work on changed tasks, rather than
turning each supplied fixture into another specialized product strategy.

New thinking contracts default to1024. Frozen512 successes/controllers are intact.
Q8/model campaigns, broad cancellation/settlement, crash/disk-full/power-loss and
fleet qualification are separate. No VC or original G1-G5 promotion follows from
these CPU checks. Raw failures and machine-readable IDs/hashes are in the private
backup named by validation/TOOL-REGISTRY-2026-10-18.json.
