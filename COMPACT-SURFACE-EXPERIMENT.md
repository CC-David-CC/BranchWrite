# Compact examples experiment for the Surface 2B model

This opt-in source branch trims worked examples in the controller prefix. It does not change the runtime permission model or the authoritative current tool schema. The goal is to reduce first-use latency on a low-power client; the experiment was not promoted to main.

On a Surface Book 2 13-inch with 8 GB RAM and MiniCPM5-2B Q5, an unmodified BranchWrite coding prompt measured about 15,666 tokens. A 4K PCC context failed; a 32K context admitted it, but the first CPU attempt was still computing after several minutes. This trimmed variant reduced the measured prefix from about 55,473 to 24,733 characters, or about 6,701 tokens. Its CPU attempt and a separate eight-GPU-layer attempt were stopped before completing the file task. Do not interpret a shorter prompt as a working or faster complete agent workflow.

Before considering adoption, compare file creation, editing, check execution, tool errors, malicious inputs, recovery, permissions and unseen tasks against the full prompt. Measure total request and prefix-reuse times and preserve existing saved-session/profile identities. For comparison, Q4 on a separate RTX PRO 6000 completed the file-creation and follow-up tasks using the full prompt; that does not qualify this 2B experiment.
