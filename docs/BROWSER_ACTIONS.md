Current model proposal contract: see OBSERVED_SOURCE.md. capture_page now takes
only path; interact_page takes path and actions. The host binds the latest actual
file observation and retains its exact hash in bw.tool-plan.v2. Earlier sections
below describe the original implementation/result history; they do not authorize
old v1 argument fields in a new workflow.

# Bounded browser action recipes

A browser action recipe starts from exact HTML bytes, opens a fresh sandboxed
browser, performs ordered clicks/fills and returns the actual resulting picture
and bounded visible text. It does not keep a hidden browser session. Repeating
a two-click recipe starts from a new page and performs two clicks; it does not
inherit the previous capture's counter, cookies or input.

## Implemented core

The client-side render API accepts BrowserConfig.actions, an immutable tuple of
PageAction(kind, target, value). kind is click or fill. target is one unique DOM
ID: an ASCII letter followed by at most63 letters, digits, hyphens or underscores.
It is not a CSS selector or script. A click's value must be empty. A fill accepts
at most4096 UTF-8 bytes. A recipe has at most16 actions.

The worker receives the recipe and exact source through its memory input stream,
not command-line action values or a host directory. Bubblewrap filesystem,
network and PID boundaries and Chromium's renderer sandbox remain mandatory.
Every capture gets a new browser context. Missing/duplicate targets, errors,
unexpected navigation/resources or namespace retirement failures return errors.

The result binds served source SHA256, actual PNG, viewport, browser, namespace
retirement, exact acknowledged action order and up to8192 visible-text characters.
Visible text is an observation, not a protected semantic pass. Large Unicode
values require a bounded512KiB worker header; the screenshot and total output
limits remain unchanged. The Unicode regression preserves its original failure.

Protected checker actions are separate from model actions. BrowserConfig rejects
combining a protected inspector and a model action recipe. A future workflow
verifier must replay the same recipe/source for screenshot comparison and retain
its separate protected interaction check; comparing different interaction states
is incorrect.

## Model-tool and CLI connection

A host manifest may now grant interact_paths in addition to read_paths and
capture_paths. Every interaction path must appear in both of those grants.
Capture permission alone does not expose interact_page. For example, inside the
existing grant object, add "interact_paths": ["index.html"]. All other required
host fields and browser setup remain as documented for static captures.

interact_page accepts path, source_sha256 and actions. Each action object has
exactly kind, target and value. A click has an empty value; fill has its text.
The tool is generated in the live JSON Schema and tool-first GBNF only when
granted. Rebuild the startup grammar from the actual registry for a new context;
do not reinterpret an old parser checkpoint under new definitions.

The exact source read witness and recipe are frozen in PLAN and rechecked at
ACT. Browser runtime sources also contribute to registry identity. The actual
PNG, action list and text are returned through ToolOutcome and the existing
image-feedback transform. No second transcript or browser daemon is added.
Completed CLI reopen is offline; an unknown publication outcome retains its
original operation and cannot automatically resend browser work.

## Interactive completion

Select examples/interactive-page-task.bw and host verification with schema1,
interactive_captures (the same path/width/height list used for static captures),
and the existing protected inspection descriptor. The exact contract is
interactive-page-inspection-and-finish. The inspector remains host-owned;
the model cannot choose, edit or invoke it as a tool.

This policy requires current actual readback and a visible successful interaction
whose frozen plan, source hash, actions, PNG and text agree. It replays that exact
recipe on the current source in a fresh sandbox and requires byte-identical PNG
and text. It then independently runs the unchanged protected checker, which may
perform different actions. The checker's own PNG is retained as a separate
artifact, never substituted for the model recipe's image. All three browser
executions must have retired. A checker-only click cannot qualify.

The existing static page-inspection-and-finish policy remains unchanged and
does not accept interaction images in place of its static capture.

## What remains

One autonomous H06 on Q4 now passes through the remote CLI/HTTP path. General assets,
navigation, persistent browser sessions and H08+ protected adapters remain work.
No CPU routing test is a model, numerical, restart or full G/VC certificate.

## Executed evidence

Eleven focused real-Chromium/validation methods pass. Across the affected suite,
116 methods pass on llm-49 and eight server-dependent grammar/CPU HTTP fixture
methods pass on llm-60:124 unique methods, zero unresolved failures/skips.
Earlier launch attempts had missing server imports and remain recorded.
CPU FlowModel tests are synthetic model peers; no inference GPU ran here.
See validation/BROWSER-ACTION-CORE-2026-10-18.json for names and attempts.
Full VC/G qualification, H06 and Q8 remain outstanding.

The subsequent connected tool ticket passed180 selected methods:164 client
checks and16 server-dependent CPU checks, including13 new tool/CLI methods and
three new grammar methods. Initial RED, a host-inspector compatibility defect
and a GBNF quote defect remain retained. Both defects were fixed without changing
protected assertions. See validation/INTERACT-TOOL-CLI-2026-10-18.json.

The interaction completion ticket passed192 selected methods:176 client checks
and16 server-dependent CPU checks, including12 new policy methods. Actual
Chromium, CLI subprocesses, negative receipt/replay/retirement checks and the
unchanged protected counter checker were exercised. See
validation/INTERACTIVE-PAGE-POLICY-2026-10-18.json.

## Autonomous counter result

H06 completed with no intervention: read, edit, interact_page(click increment),
read, finish. The actual image was delivered before finish. Its source/action
replay matched exactly, and the protected checker passed two independent real
clicks. Native COW ancestry and300 image rows agree with the exact PNG. Whole
CLI82.53s, completed offline reopen0.401s. Source/code/profile and all scope limits
are in validation/AUTONOMOUS-H06-Q4-2026-10-18.json. This is not a general intent
judge or fresh numerical qualification. H07 and broader interaction/resource
coverage remain. Do not infer that every allowed recipe fulfills any user task.

## Greeting adapter checkpoint

The host-only PageInspection target H07 now executes the original protected
counter and greeting assertions. It checks ordinary names and markup-like names
as literal text. Six new actual browser/CLI methods pass, including rejection of
an innerHTML handler and a broken existing counter.198 selected regressions pass
(182client,16serverCPU), no skips. UnknownH08 remains refused; the checker bytes
are unchanged. Autonomous H07 is still unrun at this source checkpoint. See
validation/H07-INSPECTION-CLI-2026-10-18.json.

## Failed page observations

A JavaScript exception is a failed observation,not verification success.
The isolated worker returns up to16 messages of1024 characters each,actual
pixels and visible text,the exact source/resource/action receipt,and proven
process/namespace retirement. A direct Executor call raises BrowserExecutionError
without creating artifact files;its capture is held in memory. The workflow
registry may publish that same capture once as browser_error with exit code1.
Existing tool-feedback/image-feedback delivers the actual error and image.

Only that completed receipt can settle the failed interaction. Worker failure,
timeouts,unproven cleanup and artifact/canonical publication exceptions retain
the original unresolved intent. A new process must not automatically repeat it.
Completed error receipts reopen from the existing RuntimeLog without dispatch.
Protected verification still rejects JavaScript errors and error-bearing capture
metadata. This introduces no second workflow or computational-state history.

H11's scripted CLI repair and300 selected CPU/browser checks pass. Autonomous
Q4 H11 is unrun at this source checkpoint. No full VC/G qualification follows.
