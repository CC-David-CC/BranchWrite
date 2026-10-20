# Giving the worker its screenshot

## Simple explanation

The browser can take a picture, but the model does not see a picture just because
it knows the filename. This connection takes the actual saved PNG, uploads it to
the same COW conversation, and gives its image ID plus tool feedback to the next
model step. Ordinary text feedback stays text.

## Use through the existing CLI

Select examples/generated-page-task.bw. Its agent loop chooses its own tools;
the file contains no task-specific actions or expected answer. Host profiles
include the normal decoder profile and this separate routing profile:

    "profiles": {
      "control": {"<existing explicit generation settings>": "..."},
      "image_feedback": {"kind": "image-feedback", "source": "current"}
    }

Use the actual generation_profile() mapping for control, or an explicit supported
decoder profile. The image-feedback profile is not a sampler profile and cannot
be passed to EXPAND. It names the lexical COWSource binding to observe. Settings,
grammar state, seed and token budgets remain owned by the decoder profile/COW.
No profile is silently injected into an explicitly supplied mapping.

The existing language spelling is:

    TRANSFORM feedback contract=tool-feedback input=outcome profile=image_feedback -> task

The existing optional profile field is used; the reference language and its tests
remain unchanged. Without this profile, legacy tool-feedback remains Text
metadata. With it, feedback is ModelInput: bounded text when no image exists,
or the ordered actual image ID and feedback text after a successful upload.
The selected source must be an admitted COWSource, not a path or model-authored
continuation address. Missing or wrong profile kinds fail preflight.

## Saved intent and recovery

The existing /cow/head reply supplies head and namespace together. Both must
match the frozen source. The immutable PNG artifact, namespace, source head,
endpoint and feedback text are recorded in a FrameKernel child before upload.
COW acknowledges actual bytes/digest/dimensions; the receipt and typed result
are retained in the same RuntimeLog. No second transcript or client image cache
is introduced. The actual pixels remain the existing artifact.

Upload is a repeatable content-addressed cache fill. If upload acknowledgment or
local publication is lost, resume may send the same bytes to the same namespace.
This does not evaluate model tokens or change the branch. Changed source heads,
namespaces, artifacts or acknowledgments are rejected. A completed upload or
completed CLI workflow reopens without network calls.

Model generation remains a separate operation with its existing original-intent
journal. An uncertain generation is never silently resent by this feature.
Server expiry, quotas and authorization remain authoritative. Expired or rejected
images produce an explicit failure; this layer does not silently replay a prefix
or reset controller state.

## Current evidence and limits

Fifteen focused upload/profile/CLI tests are included in 123 affected regressions,
all passing on llm-49. Actual Chromium supplies CLI screenshots; a synthetic HTTP
peer supplies test generation receipts. This is not real-GPU numerical evidence.
A separate real H03 run now passes writer/capture/image-feedback/model/host-
verifier integration: llm-49 CLI to Q4 on llm-60. It created a 506-byte page,
returned its 3915-byte PNG, and the protected DOM/pixel check passed on an exact
matching capture. Native image state confirms 300 actual embedding rows. One
early capture proposal lacked a read and mangled the digest; the host rejected
it and the model recovered on its own. Five model outputs consumed 1509 tokens
including thought/final/EOS. Whole audited latency 286.3s; offline reopen 0.40s.
Those are not native throughput figures. Full numerical and restart qualification
remain separate. See validation/AUTONOMOUS-H03-Q4-2026-10-18.json.

Initial tests retained a missing-feature RED. First implementation also exposed
two fixture setup errors: deliberate corruption needed writable permission on
its own test artifact, and its upload CLI lacked the fixture API key. Both setup
fixes preserved assertions and production checks. An attempted language extension
failed the unchanged contract check; it was removed instead of changing the
reference. See validation/IMAGE-FEEDBACK-2026-10-18.json.

Automatic local-file attachment admission, general click/fill tools, dynamic page
verification, broader recovery/controller combinations and full G/VC/Q8 campaigns
remain separate work. New tasks keep thinking 1024 and DRY+Min-P defaults; previous
saved controllers and successful runs are not rewritten.
