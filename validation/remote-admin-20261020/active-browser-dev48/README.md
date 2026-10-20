# Fresh installed-client active steering browser check

Executed 2026-10-20. PASS for this bounded Q4 journey, not G1-G5 certification.

The installed dev48 client on llm-49 used the original COW service on llm-60:8099.
The initial task requested a phone-friendly dog page, the sentences "Milo plays.
Luna runs.", and a Say hello button. It did not request special name/verb styling.
While its first native ask was pending, the PTY sent a new user instruction:
make Milo/Luna bold and plays/runs italic and underlined, retaining the original task.
No operator edited the generated source or supplied a replacement answer.

The closed canonical session audit records the second input as kind=steer,
the original turn as interrupted, and the steered turn as finished. COW fork
and request receipts remain in the private raw client archive.

Independent isolated Chromium passed at 1280x800 and 375x812. Computed name
weights were 700; both verbs had italic font style and underline. The button
showed Hello, David!. No horizontal overflow, external dependencies or JavaScript
runtime errors were observed. Both browser inputs match the saved HTML SHA-256.
Screenshots were visually inspected as well as checked programmatically.

Whole journey: 358.834 seconds. Steering submitted at 15.068 seconds; safe
boundary observed at 80.525 seconds (65.458-second wait). The original server
has whole-model-step pause fallback. This is successful active steering, not
immediate cancellation or qualification of the newer consumed-boundary service.

The installed wheel SHA-256 is in provenance.json. The source worktree contains
pending dev48 integration changes beyond its committed baseline; this evidence
commit alone does not claim those implementation changes have been committed.
The private artifact archive includes their source diff and source hashes.
No Windows artifacts or GitHub publication were used.
