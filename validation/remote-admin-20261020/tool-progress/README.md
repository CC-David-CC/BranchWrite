# Specific tool progress

2026-10-20,dev55. Interactive progress now describes the admitted tool category:
reading/editing a file, running tests/checks, browser interaction, remote commands
or uploads. Labels are a closed table, derived from frozen plan identity and
world; no model text, arguments, paths, shell commands or credentials are printed.
The generic callback events remain for compatibility. Interactive output suppresses
the redundant generic tool-start line; noninteractive stderr retains it.
Progress is cosmetic, never evidence that a check passed or authority to retry.
Display failures cannot abort/repeat effects. New helper source is bound into
interpreter identity; old source-pinned sessions retain their old installed build.

5new focused tests plus prior progress tests passed. Combined471CPU/PTY/HTTP
regressions passed,0failures/errors/skips,107.941seconds, source unchanged.
These fixtures do not imply real-GPU qualification. Separate actual dev54 GPU
repair evidence is in../autonomous-repair/. Installed dev55 CLI/local-shell
and quiet idempotent reopen also passed on llm-49; see installed evidence.
The first nonisolated wheel build lacked setuptools; ordinary isolated wheel
build succeeded. No product workaround or test weakening was used.
Wheel SHA256:76150e91d62328c6549ad63304d261b229e38feed2ef080a8eb3930863d0dcd0
