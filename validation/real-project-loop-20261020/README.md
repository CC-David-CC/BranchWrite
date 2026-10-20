# Installed CLI: existing-project repair

The corrected Unicode fixture passed all eleven independent acceptance checks.
BW ran as an ordinary non-admin user in the Linux VM on llm-49, using the
authenticated COW service on llm-60. No COW implementation package was installed
on the client. All 86 installed BW Python files match this worktree.

The initial request asked for case-insensitive contact search. A follow-up sent
while the GPU request was active added CAFÉ/Café and STRASSE/Straße matching.
The session closed the initial turn as interrupted, then completed the revised
request. Both the client driver and its SSH child exited. The accepted project
files are in `accepted/`; the starting project and exact prompts are in
`examples/repair-contact-directory/`. The five original test methods are
structurally unchanged; BW added four. Its nine tests passed, and an independent
checker in an OS-isolated copy passed eleven behavior/preservation checks.

An earlier attempt used a fixture whose Unicode was damaged by Windows
PowerShell before SSH transport. Its raw evidence remains private and is
explicitly invalid for model/Unicode scoring. The corrected destination bytes
and direct WSL UTF-8 transport were verified. SIGINT settled the invalid client's
two turns as interrupted and released the active server request.

The independent checker and canonical session observations remain on llm-49 at
`/home/dflanag3/spatial-artifacts/bw-real-project-loop-20261020/`. Protected
observer files were outside the agent's project and were not sent as examples.
The JSON here is a derived evidence summary, not a dispatch record or alternate
workflow state. The installed client used the existing canonical RuntimeLog and
COW references. No new numerical-logit or zero-prefix-work qualification is
claimed; this instrumented run is not a throughput benchmark.

Queued follow-ups and alternative file/context branches are the next combined
checks. They are not claimed by the repair result. The standalone-agent goal
and broader recovery, browser, stress and release work remain active.
