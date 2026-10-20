# Autonomous repair through the installed client

2026-10-20: installed dev54 on llm-49, real Q4 COW HTTP inference on llm-60.
BW received only the initial natural-language task. It ran the existing unit
suite (run_shell, exit1), read source and tests, repaired calculator.py, reran
the same unit command (run_check, exit0), and finished in77.362seconds.
Independent audit matched unchanged test bytes and exact repaired function,
reran3 existing tests and checked100 seeded integer-list cases. All passed.
The canonical ledger binds actual failure/success feedback to the original
operations; sandbox terminal workers exited with no remaining namespace members.
No operator repair or injected model decision. This is one small repair, not
proof of broad autonomous coding ability or an adversarial self-repair campaign.
The initial observer incorrectly assumed both invocations used run_check;
actual commands/exits/identities were then audited without changing the run.

Private raw archive:
box-git:/srv/data/git/private_context_cow.evidence/branchwrite-admin-20261020/bw-autorepair-dev54-20261020.tar.gz
SHA256:15b7782a3ac38573e9db6a33f75a77aaa9f8c7206db5224bab9e77ab70a46162
The original dev54 installed client remains needed for this pinned session.
Dev55 is a separate new-launch build, not a silent migration of admitted work.
