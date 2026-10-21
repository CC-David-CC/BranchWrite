# Tool errors and model repair

BranchWrite includes observed tool failures in the next model input. The record retains the tool, original operation ID, plan hash, actual exit status, separate stdout/stderr, raw artifact hashes, truncation/decoding indicators and any host verification. Successful output text does not override a failing exit or verification.

For recognized failures, `problem.stage` names the observed stage and `problem.next_action` explains a bounded repair. This is guidance, not a permission grant or acceptance verdict. Arbitrary internal details are not copied into the prompt. CAD and Blender design quality still requires their actual measurements and views.

For example, a PDF program that exits zero but writes `dogs.pdf` rather than the worker's required `document.pdf` now explains the missing file. The model should change its source to write `document.pdf`; the host publishes the requested destination name. CAD uses `part.step`. Empty, linked, nonregular or oversized exports are rejected. Timeout and output-limit failures are distinct from missing exports. The isolated worker's original exit status remains available.

New coding prefixes teach the model to diagnose from the recorded evidence, avoid repeating unchanged failed actions, reread before stale edits, and respect grants. Already prepared roots/controllers remain immutable; these instructions apply to new admissions.

An uncertain operation is different from a known failure. Its exception identifies the original operation and plan and requests reconciliation instead of resending. A nonzero command may already have changed something. Neither failure nor cancellation implies rollback.

## Executed validation

The 2026-10-21 diagnostic revision passed 85 focused CPU regression tests: 31 PDF, 8 problem-feedback/prefix, 8 output/HTTP, 8 edit admission, 14 terminal components, 10 actual CAD execution and 6 coding-default tests. No skips. The PDF integration test executes an isolated program with the wrong filename and inspects the actual workflow feedback. CAD/Blender stage-projection fixtures script outcomes; those are not new GPU/CAD/Blender design successes. Existing execution tests independently cover real PDF/CAD workers and namespace retirement.

Initial regression commands used incomplete test environments (missing COW imports and CAD packages). Retained logs record those failures; final reruns used both COW import roots and the installed CAD interpreter. No assertions or reference equations were relaxed.

A separate-VM Qwen3.5-9B Q8 PDF trial using the corrected installed client was started after these checks. Its model recovery and final-page inspection are pending; passing diagnostics tests do not establish autonomous PDF success.

## PDF layout observations

PDF build/render feedback includes the saved page's visible box, number of scanned text characters, out-of-page character count and up to eight examples with coordinates. At most 8,192 characters are scanned; remaining text is explicitly unassessed. Cropped and rotated page tests use the actual PDF canvas coordinates. Warnings supplement the current page image. Zero measured overflow does not prove absence of overlap, missing content, bad design or problems in embedded images. The executable teaching example derives table width from doc.width and wraps long cells with Paragraph instances.

39 PDF regression tests pass for this additive observation, including real worker-to-model feedback and the two rendered teaching pages. The live model repair remains separately evaluated.
