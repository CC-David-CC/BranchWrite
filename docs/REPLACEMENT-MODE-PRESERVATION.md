# File replacement preserves permissions under restrictive umasks

A real S³/BW baseline found a harness failure: the model repaired `task.py`
correctly, read the file, edited it, ran a passing check and explicitly finished.
The independent artifact oracle passed. The workflow still failed because the
saved repair's mode changed from `0644` to `0600`.

The owner process used `umask 0077`. BW created its atomic replacement file with
the original mode, but POSIX applies the process umask to `os.open(..., mode)`.
Renaming that temporary file into place consequently replaced the original
permissions with the narrowed permissions. The same issue affected byte
replacement and whole-file replacement.

## ELI5

BW fixed the contents and accidentally changed the file's permission label.
The test caught that change. BW now puts the original permission label on the
new file before swapping it into place.

## Technical explanation

`Executor._replace_bytes` now calls `os.fchmod` on the owned temporary file
descriptor after flushing the new contents and before `fsync` and the atomic
rename. It restores the already observed original basic mode, independently of
the process umask. Both `replace` and `replace_file` use this boundary.

If restoring the mode fails, the temporary file is removed and the original
file remains unchanged. The patch retains the existing grants, preimage checks,
private-workspace boundary and original input immutability. It changes no model
weights, prompts, samplers or inference limits.

## Evidence and practical effect

The distinguishing Linux tests exercise both replacement methods with modes
`0644`, `0755` and `0444`, and umasks `0022`, `0077` and `0777`: 18 combinations,
plus a deliberately failed mode-restoration check. Before the patch, 12 mode
combinations failed and the injected-failure test exposed the missing operation.
Afterward, all controls pass.

The broader BW checks ran 54 tests: 53 passed and one optional real-browser test
was skipped because this host has no configured browser executable. All 44 S³
action/export/registry and artifact-integration controls also passed with the
patched BW under `umask 0077`. Those checks use actual BW/COW/OS boundaries and
real GGUF tokenizer/template metadata, with scripted proposals and no model
inference or training.

A pre-existing test expected one Python version's missing-package error wording.
On this host, the interpreter instead discovers an empty suite and BW rejects
it explicitly with exit code 1. The test now accepts either exact non-success
case, while continuing to reject empty-suite success. The original source was
tested to confirm this expectation mismatch existed before the permission fix.

The affected new learning round was stopped through PCC's public learning-step
API at the settled `choosing_lessons` boundary, before any training job was
created. Its original scores and observations remain unchanged. The next round
must install the corrected BW source, register its new evaluator identity and
establish a matched baseline before comparing a trained candidate.

This finding is a harness correction, not evidence of learning. Historical
results should be checked for the triggering permission change and owner umask;
this does not invalidate arithmetic-only training curves or prove that every
earlier workflow failure had the same cause. The fixed 68-update comparison and
its quant sweeps remain unchanged.

See the [machine-readable qualification](../validation/replacement-mode-20261026.json)
and [regression tests](../tests/test_replacement_modes.py).
