# Why BW failed the MiniCPM shell tasks

BW had a correct repaired file on disk and still failed the workflow. That is
why we score the saved artifact, verification, termination and cost separately.
The same model can write the repair and then struggle to verify it through a
particular tool contract. These are development findings from five objectives,
not a general failure-rate estimate or a qualified harness release.

## What the original traces show

In the quoted-filename task, BW read the script, then generated a repetitive,
unfinished JSON shell-command string across continuation requests. The command
was never admitted or executed, and no edit occurred before the timeout. This
was not an observed shell quoting failure during execution.

In the failure-status task, BW made ten exploratory shell calls. The model tried
to edit protected source through shell writes and to run a non-executable script
directly. Four calls emitted read-only-filesystem diagnostics, five emitted
permission diagnostics, and four diagnostic calls nevertheless ended with status
zero because later commands masked earlier failures. Correct separate stdout,
stderr and final status reached the model; the trajectory did not recover.

BW's shell intentionally projects captured source read-only. Persistent source
edits use granted file tools. A readable shell script can be tested with `sh`
without changing execute permissions. Other harnesses have different tool
contracts; at least two passed each objective with the same MiniCPM weights.
The observed mismatch justified harness work before weight training. It does
not establish a single causal explanation for every failure.

## Changes and measured results

The tool card now explains the project-relative working directory, file-edit
boundary, script invocation and short-command workflow. Shell feedback includes
that context. If retained stderr mentions a read-only filesystem or permission
denial, feedback gives conditional repair guidance, including the possibility
that a later command masked an earlier failure. It preserves the exact final
status and original output artifacts; a hint is not a task verdict or new grant.

| Variant | Correct saved artifacts | Completed independent passes |
| --- | ---: | ---: |
| A: original compact-v2 controller | 3/5 | 3/5 |
| B: rewritten compact-v3 plus tool/feedback changes | 2/5 | 2/5 |
| C: original compact-v2 wording plus shell contract/feedback | 5/5 | 4/5 |
| D: C plus explicit exploration versus named-check descriptions | 5/5 | 4/5 |

B regressed and is rejected. C and D preserve all three Python passes and
complete the quoted-filename task. The failure-status script independently
passes after both changes, but the workflow still fails to finish. In C it kept
using exploratory shell calls, including treating an input value as a filename,
instead of registering a final named check. D's clearer completion contract did
not solve this: it timed out after nineteen requests. This is an unresolved
verification/recovery/termination problem, not an accepted full fix.

All runs kept weights unchanged, thinking off, 64K context and 512 output tokens
per request. BW's twelve-request limit was per model action, not global; the
interpreter had 256 steps and each task 120 seconds. Do not compare this as an
equal-budget causal ranking against external clients. These interventions also
change multiple prompt/feedback details together; their effects are not isolated.

[Verified summaries and source-patch hashes](../validation/minicpm-shell-investigation-20261024/results.json)
retain each failure and the saved-source/checker/ledger fingerprints. The
adjacent B/C/D `.patch.gz` files reconstruct each intervention from its recorded
source base: decompress with `gzip -dc candidate-c.patch.gz` before applying.
Their decompressed bytes match the recorded patch SHA-256 exactly. Private tasks, expected answers and raw traces remain outside public Git.

## Mechanics, recovery and remaining work

Forty-five focused CPU checks pass, including real namespace isolation,
read-only rejection followed by a granted edit and successful `sh` invocation,
zero final status with an earlier shell error, exact output artifacts, HTTP
feedback, completed reopen and grammar/continuation boundaries. The HTTP fixture
was updated to supply actual required connection-discovery identities; missing
module paths/dependencies during setup were retained privately and corrected.

D's timeout left an unacknowledged request whose original server status proved
durable. Its exact output was recovered into a separate journal only after that
proof, using the original immutable intent. The original failed-run record was
preserved and no new generation or workflow continuation was requested. The
owned inference service was then settled and the GPU released. A timeout alone
would not have proved cancellation or absence of committed work.

Next, qualify short complete tool actions, intelligible file feedback, meaningful
positive/negative checks, explicit final-check selection and bounded stopping on
unseen variants. Measure whole-run requests as well as per-action bounds. Keep
saved-artifact correctness separate from completion, and preserve the incumbent
when a change regresses another task. Do not repair this by silently rewriting
file escapes, weakening checks, granting shell writes or calling every failure a
model-training problem. MiniCPM learning and native Muon qualification are
separate next-stage work; these runs used no weight updates.


A later [four-probe check-readiness study](MINICPM-CHECK-PROGRESS-EXPERIMENT.md)
found no accepted behavioral improvement. The default remains unchanged; the
new accurate check-progress projection is explicit experimental configuration.
