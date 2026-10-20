# Capture a generated page

The capture tool now opens the browser in a separate Linux filesystem, process
and network space. It receives only the captured page bytes. Your home folder,
API keys, service sockets and GPU devices are not mounted there. Chromium also
keeps its own renderer sandbox on. A timeout stops the owned worker and children.

This is one tool used by BranchWrite, not another agent loop. The host grants an
exact capture path and SHA-256. The executor reads stable bytes, sends them
through a memory-backed file descriptor, and receives a PNG plus source and
isolation receipts. It never serves the caller's working directory. The byte
server, Playwright and Chromium all run inside the same isolated network.

Use the client Python environment with Playwright/Pillow, Linux bubblewrap and
prlimit installed. Supply the actual Chromium executable and its adjacent
runtime directory, rather than a launcher that depends on an external service.
The tested executable on llm-60 is:

```text
/snap/chromium/3554/usr/lib/chromium-browser/chrome
```

Existing CLI shape:

```text
CLIENT_PYTHON -B tools/capture_page.py --source OWNED_SOURCE --entry index.html --expected-sha256 SHA256 --browser NATIVE_CHROMIUM --output NEW_OUTPUT
```

The receipt now includes distinct PID/network/mount namespace identities,
launcher PID, worker exit and an empty-namespace check. Permission to read or
edit does not grant permission to capture. A missing namespace/browser dependency
fails explicitly; there is no host-process or --no-sandbox fallback.

System runtime files, the client Python environment, the selected browser's
directory and fonts are mounted read-only. The BranchWrite package is read-only.
Temporary state is in a bounded128MiB tmpfs. User/mount/PID/network/IPC/UTS
namespaces, capability removal and an empty inherited environment form the
outer boundary. Nested user namespaces remain available for Chromium's sandbox.
CPU/file limits apply per process; they are not aggregate memory/CPU accounting.
The supervisor separately bounds wall time and captured output and settles its
owned process group. No GPU is used by this capture configuration.

The initial tests exercise a host-only secret file, an active host-loopback
listener, an inherited secret canary, actual distinct namespaces, real Chromium
capture and timeout cleanup with a spawned child. They do not establish immunity
to every browser/kernel escape or exhaustion attack. One self-contained document
is supported; assets/interactions, broader isolation hardening and aggregate
resource controls remain outstanding.

Executed2026-10-17: focused12/12 and full BranchWrite341/341 pass, no skips.
The unchanged H01 source renders to the same1984-byte PNG SHA256
414bcbf649fc99734f5c7481cc33c84ce3031fc35443f4bdae470397efa532b8;
protected pixel checking passes. H01 capture was0.806s in this single sample,
not a benchmark. These counts belong to that browser-boundary increment. H03
subsequently ran: create/read and protected capture PASS, first observer semantic
FAIL, explicit independent-example observer retry PASS on unchanged PNG. Current
focused38/full349 pass; see validation/H03_Q4_2026-10-17.json/.md. Exact earlier results
and private archive fingerprints are in validation/BROWSER_ISOLATION_2026-10-17.json.

For a host-selected protected page inspection, supply --check-module,
--check-sha256 and --check-target together. The checker is verified and bound
read-only into the existing browser worker; its assertions run on the same live
page and captured PNG. A task assertion failure retains the PNG/receipt and
exits1. This facility does not permit a model to choose or supply executable
checker code. H03/H04/H05 are the currently admitted inspection targets.


## Host-owned checks for an ordinary task

A host can select `PageInspection(path, sha256, "custom")` for checks that are
not a catalog fixture. The checker has the same pinned-source and OS-isolation
boundary as protected catalog checks; a model cannot select or modify it. It
provides `structure(page, target, expect)` and `pixels(path, page, target, phase)`.
An optional `interact(page, target, expect, actions)` drives actual browser events.
After interaction, structure is checked again and the resulting screenshot is
captured. Action receipts retain the existing bounded pairs-of-strings wire format.

This permits independent computed-style checks, such as names being bold and
action words being italic and underlined, plus a real click that must display
the requested greeting. Source bytes are not rewritten to suit a checker.

Four real-browser controls passed: valid styles and click, missing underline,
italic without bold, and an invalid action receipt rejected by the host. The
29-method browser regression campaign passed without skips. One old assertion
expected a raw OSError after canonical publication failure; unchanged baseline
4d7b0414 failed the same assertion. It now requires EffectIndeterminate with the
original OSError cause, operation/plan IDs and no-resend behavior. The dispatcher
and protected catalog assertions were not changed. Original failing evidence is
retained under validation/interactive-loop-20261020/.
