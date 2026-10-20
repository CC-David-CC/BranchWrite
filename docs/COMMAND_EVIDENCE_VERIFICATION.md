# Host-enforced command evidence before finish

## Problem observed during L06 integration
The file-readback-and-finish policy can establish current bytes and a real read
receipt, but not that the requested command actually ran. The external campaign
audit catches a missing timeout; a standalone agent needs that obligation inside
its workflow. This is a product gap, not a reason to loosen the L06 oracle.

## Proposed implementation
Add an explicit command-evidence policy alongside existing verification policies.
Host admission specifies required named-command or shell-command identities and
accepted dispositions/statuses. Verify only settled, resumed predecessor outcomes
bound to this registry, world, admitted plan and relevant file dependencies.
Require proved namespace retirement. Never trust the model's final sentence or
an unrelated receipt. Preserve nonzero, signal, timeout, output-limit and
spawn-error distinctions. A host may require timeout for a cleanup diagnostic;
that does not make the timed-out program successful.

Combine command evidence with current file checks where requested. Expected
output hashes remain an optional host policy, not a prerequisite for ordinary
coding tasks. Existing file-only policy identities and saved runs stay unchanged.
Do not build a second ledger, rerun effects on missing acknowledgment, or use
external campaign receipts as production authority.

## Test-first implementation sequence
1. A finish proposal plus readback without the required command must fail.
2. Real command execution with correct status and retired namespace may satisfy.
3. Wrong command, wrong world, stale dependencies, unresumed result, unsettled
   intent, incorrect disposition/status, and missing retirement must fail.
4. Bind policy identity and verification receipts to the canonical runtime.
5. Expose closed admission through CLI configuration and test real CLI flow.
6. Exercise an unfamiliar small coding repository without target artifact hashes,
   with actual tests as acceptance and no operator-supplied tool decisions.

Status: DESIGN_ONLY. No policy implementation or live qualification yet.
L06 baseline remains immutable and currently active on the previous worktree.

## Implemented interface (bounded qualification)
Select VERIFY contract=command-evidence-and-finish. Its host verification object
has schema:1 and commands:[{command:<exact shell string>,disposition:<actual kind>,
exit_code:<exact integer or null for spawn_error>}]. The shell grant remains
mandatory. The model does not set this policy or its acceptance values.
Each real shell outcome now binds the post-publication workspace inventory.
Current inventory, admitted command plan, canonical result bytes, actual stream
artifacts and namespace retirement must match. This supports declared program
outputs without needing oracle output hashes. Later workspace changes require
fresh command evidence. Normal command success does not prove semantic correctness;
choose a real protected test command when that is the desired acceptance.
Byte-only/readback policies remain separate and unchanged. Combining file and
command obligations in a single policy remains outstanding.
CPU workflow, CLI subprocess and replay checks exist. Live-model use of this
new policy, foreign/unresumed receipt regressions and broad qualification remain.
