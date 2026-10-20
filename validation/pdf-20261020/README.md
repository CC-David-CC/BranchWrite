# Built-in PDF foundation and completion evidence

34 focused tests pass, no failures/errors/skips: actual ReportLab/PDFium workers,
canonical ledger completion checks and the existing project-check suite. The
initial red cases demonstrated missing current-page completion, forged receipt
acceptance, stale source acceptance, absent PDF exports and out-of-range page
misclassification. Preserve the failures. One launcher JSON-escaping failure and
one bytecode-cache mutation failure are infrastructure evidence, not model failure.

The existing runtime guard is unchanged. PDF admission prevents later Python
bytecode writes into the pinned installed runtime. Exact source/receipt identity,
independent inspection and retired namespaces remain required.

Every current PDF page must have an actual rooted PNG receipt, and all current
selected named checks must pass. A build failure supersedes prior success without
deleting the previous PDF. Source edits invalidate an earlier build. The public
feedback reports missing page counts. This verifies evidence availability, not
that the model correctly interpreted every image or fulfilled every requirement.
Real Q4 author/review/revise and latest combined regressions remain pending.

53 CAD and 7 Blender regressions passed after the shared builder change, before
the latest registry/completion edits. Do not combine older scope into a current
whole-project certification. Prior installed-proof.json belongs to an earlier
wheel snapshot; new installation fingerprints will supersede it explicitly.

## Distro Python portability correction

A real standard /usr-based venv initially rejected because the generic runtime
tried to pin unrelated files under all of /usr. New admission pins the venv,
stdlib, real interpreter and explicit OS stdlib-link targets. Arbitrary venv
links to private files still reject, and admitted module mutations still reject.
A second actual worker failure exposed a venv under /tmp being hidden by the
private scratch mount. Runtime mounts now follow scratch mounts. Both failures
are retained. 37 combined PDF/project/runtime checks pass with no skips.

The native inference processes and old admitted dev59 installations were not
changed. This correction is a new-launch dev60 build. Full combined and existing
CAD/Blender requalification follow; do not infer those from 37 focused cases.

## Combined and domain regressions

Combined dev60 source7dd54f56 passed500 CPU/PTY/HTTP/PDF methods onllm-60,
no failures/errors/skips,126.82s, source fingerprints unchanged. Its first run
retains12 missing test-support-dependency errors; exact regex/Jinja2 pins were
then installed and the full suite rerun. No reference assertions were edited.

The shared runtime change initially broke Blender's structural runtime protocol
(missing support_paths); the explicit empty support-path field is now supplied
by BlenderRuntime. Seven actual Blender/MCP regressions pass after that fix.
53 CAD regressions also pass with the established OSMesa runtime. A launcher
without OSMesa crashed and produced no final result; preserve that log as a
failed environment invocation. Neither failure is a model-inference defect.

The combined500 methods cover7dd54f56; the subsequent Blender-only field fix
is covered by the seven actual domain cases. Do not silently attach the500
count to a later untested aggregate source. Real Q4 PDF evidence lives separately
in validation/pdf-live-q4-20261020 and describes the installed dev59 wheel.
