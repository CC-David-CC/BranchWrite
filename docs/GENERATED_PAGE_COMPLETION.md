# Checking a page the model creates

## Simple explanation

A screenshot proves that the browser drew something. It does not prove that the
page is right. This host-selected check reads the current file, requires the
worker's actual readback and screenshot, and checks the page in a sandboxed
browser. The checked picture must match the picture returned by the worker.
A model saying finished is not enough.

## Host configuration

Use the existing CLI verification object with these exact fields:

    {
      "schema": 1,
      "inspected_captures": [{"path": "index.html", "width": 640, "height": 480}],
      "inspection": {
        "path": "/absolute/protected/checks.py",
        "sha256": "<exact checker SHA256>",
        "target": "H03"
      }
    }

The existing protected PageInspection adapter supports H03 through H07. This
does not create a general executable plugin interface. The inspector must be a
regular existing host file outside both the candidate source and owned world.
Its digest is checked before root admission and again by the browser boundary.
All capture paths need explicit read and capture grants and the registered
viewport. The source may initially be absent and created through a granted tool;
its future source bytes are not supplied as a reference solution.

Select VERIFY contract=page-inspection-and-finish. The model's browser tool
still cannot choose an inspector, executable, options or protected target.
ToolRegistry's rejection of protected inspections in model browser configuration
is unchanged. The host verifier uses the existing Bubblewrap and Chromium
sandboxes; it does not run candidate HTML or checker code directly on the host.

## What acceptance proves

An explicit finish request is required. Only resumed predecessor read/capture
receipts from the canonical workflow qualify. The verifier hashes current source
bytes and requires matching actual readback, served source, PNG and viewport.
Missing witnesses or changed source fail before protected browser execution.

The protected checker then runs on those exact current bytes in its own browser
execution. Its DOM and pixel assertions must pass. The resulting PNG must be
byte-identical to the returned capture, and current source must still match.
Both browser sandbox and fully retired worker/namespace witnesses are required.
Scope close rechecks the selected policy; completed workflow reopen reuses the
saved receipt without new browser dispatch.

This exact-image contract currently targets deterministic, self-contained pages.
A timestamp, animation, font race or other nondeterministic rendering can cause
a clear mismatch even when two renderings look similar. Do not relax checks or
claim dynamic-page support from the static fixtures. A separate evidence design
is needed for later interactive state.

A failed page check is a task failure and retains its real screenshot. A changed
checker or browser/setup failure remains an integrity/harness error. Neither is
reported as a pass, and no protected assertion or reference page was changed.

## Current end-to-end scope

Source-bound capture-image feedback and the protected host policy passed the
real autonomous H03 workflow through llm-49 CLI and Q4 on llm-60. The model chose
its own create/read/capture/finish actions. Actual image delivery and native
image rows were independently checked. One premature capture was rejected and
self-corrected. See validation/AUTONOMOUS-H03-Q4-2026-10-18.json.

The ladder is H00-H06, 7/13. Next is H07 input/greeting work. Static exact-image agreement does not qualify dynamic/interactive pages,
general coding quality, numerical equivalence, GPU process restart or full G/VC
qualification. Those campaigns remain outstanding.

## Autonomous edit follow-up

H04 passed a fresh default-sampler run on COW source 9fae1e2e/profile 092f after
its full-validator optimization. The model made one localized style change,
captured the edited page, read it back and finished. Protected checks and actual
image delivery pass; previous failed attempts remain. See
validation/AUTONOMOUS-H04-Q4-2026-10-18.json. That checkpoint established 5/13; the later H05 run below reaches 6/13.

## Image-first layout follow-up

H05 passed with a real before image delivered before its single model-selected
repair, then a real after image delivered before finish. Both canonical image
identities and 600 native rows were audited. Original source remained intact;
protected current-source geometry/colors/heading checks passed. Whole CLI
105.77s, offline completed reopen 0.401s. See
validation/AUTONOMOUS-H05-Q4-2026-10-18.json. This is static image-first editing;
model-selected click/fill and persisted interactive browser state remain work.

## Interaction-state follow-up

H06 passed with the separate interactive-page-inspection-and-finish policy.
The actual model-selected click image is checked against a replay of its own
source/recipe; independent protected checker clicks and their PNG are retained
separately. The existing static contract was not relaxed. See BROWSER_ACTIONS.md
and validation/AUTONOMOUS-H06-Q4-2026-10-18.json. Model-selected fill exists in
bounded tools but H07 has not yet run autonomously.
