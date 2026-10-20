# Image input in the autonomous interpreter

## Simple explanation

An image has to reach the model as an image. Writing its filename into a question
does not do that. Upload the real picture to Context COW first. Then give
BranchWrite its image ID and your question. COW keeps the picture with the correct
conversation. BranchWrite saves the exact request so that restarting does not
accidentally ask the question twice.

## Development status

Typed ModelInput now reaches the existing Interpreter/ModelAdapter and COW HTTP
ask or append-user boundary. Eight new tests and72 affected client regressions
pass on llm-49; their HTTP peer returns synthetic outputs. A separate live
autonomous H02 run now passes all three image questions through llm-49 CLI and Q4
on llm-60. Actual uploaded images match canonical server image spans and branch
receipts. The unchanged protected host checker confirms all three visual answers.
See validation/AUTONOMOUS-H02-Q4-2026-10-18.json for exact scope and measurements.

Upload actual PNG/JPEG bytes using CowClient.upload_image(namespace, bytes).
Keep the acknowledged image_id. The target branch must use that same namespace;
COW checks authorization, expiry, supported controllers and native preparation.
No local COW implementation or model weights are needed on the client.

A host configuration binding can contain:

    "task": {"type": "ModelInput", "value": [
      {"type": "image", "image_id": "<64 lowercase hexadecimal characters>"},
      {"type": "text", "text": "Describe the attached image."}
    ]}

Use EXPAND with task=task as with text. ModelInput permits1..8 images, at least
one explicit text part, at most17 parts and262144 UTF-8 JSON bytes. Parts preserve
their order; repeated IDs are not silently deduplicated. Paths, URLs, roles,
embeddings and extra metadata fields are rejected. Text-only input remains Text.
Host declarations are trusted input, not upload receipts: the server is the
authority for resolving and granting each image ID.

The frozen model call and original-intent journal retain exact ordered parts.
Later native CONTINUE requests do not append those parts again. Changing an input
on restart fails admission rather than rebasing the old workflow. Reopening a
completed workflow reads its retained result without another HTTP request.

An EXPAND-only workflow has no selected acceptance oracle. It completes with
verified=false and CLI exit1, and its output is in the canonical result artifact.
A protected host checker may judge that output; the model cannot declare itself
verified. Existing tool-based verification contracts are unchanged.

## Remaining integration and qualification

Automatic local-file admission/upload and broader vision/controller combinations
remain to be exercised or built. No fallback treats paths/base64 as text or
silently resets sampler/parser state. COW remains the only model-history and
native-state authority; this adds no second transcript or image cache.

Capture feedback can now supply actual image input through an explicitly selected
host routing profile; see IMAGE_FEEDBACK.md. ModelInput may also hold plain text
so non-image tool results do not require an upload or a different execution loop.
