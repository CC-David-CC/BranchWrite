# Independent terminal components

Run these before autonomous model tasks. They execute real ToolRegistry proposals
through the workflow interpreter and the existing read-only Bubblewrap terminal.
They do not call a model, inference server, GPU, reference worker or autonomous
coding runner. They change no sampler or default prompt.

On the Linux client, from this checkout:

    PYTHONDONTWRITEBYTECODE=1 /home/dflanag3/spatial-artifacts/branchwrite-cross-host-20261018-v1/client-env/bin/python -B -m branchwrite.terminal_components --domain quoting --domain newlines --split heldout --seed 731 --variants 3 --output-dir /home/dflanag3/spatial-artifacts/NEW-terminal-components

Choose a new output directory each time. Existing directories are rejected,
rather than rerunning uncertain operations under previous identities. Omit
--domain for all components. Repeat it to select domains. --variants accepts
1..100. Seeds are unsigned 63-bit integers. The host name is bound at admission.

| ID | Domain | Required distinction |
|---|---|---|
| TC001 | streams | Optimistic stdout cannot override a nonzero status; stderr is separate. |
| TC002 | warning-success | Warning stderr does not turn a real zero status into failure. |
| TC003 | pipeline | Default Bash pipeline versus explicit pipefail. |
| TC004 | binary | Invalid UTF-8 and NUL remain exact raw bytes; replacement display is lossy. |
| TC005 | literal-ufffd | An intentional valid UTF-8 replacement character is not lossy decoding. |
| TC006 | empty | Empty streams occur with both successful and unsuccessful commands. |
| TC007 | missing-file | An existing empty file differs from an absent file. |
| TC008 | quoting | Spaces, quotes, literal dollars, Unicode normalization forms and final LF. |
| TC009 | timeout | Timeout disposition and negative observed status; no invented success. |
| TC010 | recovery | Command-not-found is recorded separately from the following correction. |
| TC011 | newlines | LF, no LF, CRLF, literal backslash-n and double LF remain distinct. |

Demo and heldout use separately seeded content and different command forms.
For example, the demo pipeline ends in cat; the held-out pipeline ends in wc.
Held-out quoting adds composed and decomposed accents, emoji, shell-looking
literal text and a differently structured filename. This is a small, explicit
structural split, not proof of arbitrary out-of-distribution robustness.
Diagnostic catalogue scripts and expected answers are not imported.

Each result includes independently declared expectations, command, actual raw
stdout/stderr hex/byte counts/SHA-256, disposition, status, tool-feedback display
metadata, operation/plan identities, per-assertion checks and namespace-retirement
evidence. Missing-command stderr varies with the host Bash build; its oracle is
a declared diagnostic substring plus exact status127, not a copied observed
error message. Timeout permits the actual negative termination status and
requires the timeout disposition and exact pre-timeout marker. All ordinary
outputs have exact byte oracles. Source, ledger and tool artifacts are retained.

Report.json updates after every case. PASS means every declared assertion
passed, FAIL means a false assertion, ERROR means an execution/collection error.
No skipped tests become PASS. A failed/error case does not hide later cases.

Python API:

    from pathlib import Path
    from branchwrite.terminal_components import build_case, run_case
    case = build_case("quoting", seed=731, split="demo")
    result = run_case(case, Path("/home/dflanag3/spatial-artifacts/new-case"))
    assert result["status"] == "PASS"

Run_case rebuilds the deterministic definition and rejects altered expectations
before creating its directory. These fixtures support host-authored teaching
examples and direct model comprehension questions. A tool-component pass does
not establish that the model understands or accurately reports its observations.
Keep held-out observations out of teaching roots used to evaluate that split.

This runner grants read-only captured fixture files and bounded shell execution.
It does not grant source edits, network, home, credentials, GPU devices or an
administrative terminal. Existing sandbox requirements remain mandatory.
