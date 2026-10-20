SC13 cross-project generic controller qualification. Installeddev15 on llm-49,
pinned Q8/FP16 KV on llm-60. A bootstraps a fresh task-independent controller root;
after A terminates, B restores that exact root in a new server/native process.
A/B use different paths and required test commands. Independent seeded output
tests and stale-command audits are frozen before inference. Read only settled
producer ledgers; inspect copied logs after terminal status. No model actions
supplied by harness. Current status: A and B bounded functional PASS. See per-project outcomes and audits.
Original numerical gates remain unqualified; no fresh oracle claimed here.
