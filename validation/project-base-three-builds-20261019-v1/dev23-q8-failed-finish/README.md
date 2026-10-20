# Real Q8 failed-finish recovery drill

The installed dev23 CLI on llm-49 used authenticated HTTP to the normal Context COW server on llm-60. Server source: 6647ae4637cf43ea356cfb1bc799722238212434. Execution profile: 2e0a61f08d0dca09751c7eee3dd0947b2431b5f73010e268b7608eefdae4ae47. Q8, FP16 KV, prefill512, capacity262144.

A test-only grammar forced the initial 4K state to request finish. The ordinary host verifier correctly rejected it because current test-command evidence was missing. Seven other grammar states were unchanged. BranchWrite automatically forked the prior root, retained the failed continuation, advanced to the 8K thinking rung with unchanged greedy settings, inspected both files, repaired subtraction to addition, ran the real tests and finished. Runtime:108.59015114209615s; zero parent interventions after launch;52 closed frames; one canonical COW fork.

Independent read-only sandbox checks passed 1,000 seeded integer pairs and four edge pairs. Only calculator.py changed; original source and protected tests remained unchanged. This is a forced control-flow test, not evidence of a natural model failure, broad coding competence or numerical equivalence. No LoRA training example is warranted.

All work and artifacts remain on private Linux hosts. Server/native shutdown and temporary-access cleanup are recorded separately. Full G1-G5 qualification remains outstanding.
