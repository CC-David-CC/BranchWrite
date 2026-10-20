# Autonomous Q4 local coding, exact upload and VM deployment

Executed2026-10-20 with installed dev51 on llm-49, original Q4 COW on llm-60,
and the owned admin01 VM. One natural-language task requested a dog website,
a local copy, deployment over the welcome page, and checks. No operator changed
the generated code, supplied a replacement tool call or steered the attempt.

The model created4609-byte index.html, read and checked it, inspected the target,
used upload_file for exact transfer, published via remote_command, and issued a
final composite check_remote. It redundantly updated three candidate index paths;
that broader-than-needed choice is visible in the actual command receipts.
Every recorded remote command returned exit0. The independent HTTP body exactly
matches the saved local project SHA256:
2aa55f1f3565506ac3ddc8759f51ecaec365a65c9b1a6a5532174e4b6ad91174.

Independent isolated Chromium passed1280x800 and375x812: required sentences,
button click -> Hello, David!, no external dependencies, no horizontal overflow,
no runtime errors. Desktop screenshot was visually inspected. This is one small
site, not broad autonomous programming or release qualification.

IMPORTANT: the first client observation reached its20min deadline before final
completion. It is retained as FAIL/TIMEOUT, not changed to PASS. Graceful stop
saved an interrupted continuation and the local file; no native request remained
unacknowledged. A separate /continue after client restart finished in2.333s,
with no new native inference requests or remote receipts. Original remote receipt
bytes remained identical. Both final workflow verification and independent site
acceptance passed after that resume. The native server remained running; this
is client/workflow restart, not a new native-process restore qualification.

Greedy thinking repeatedly enumerated an irrelevant checklist. Across the reported
native chunks,19969 tokens used932.680s generation and88.341s capture. These are
reported COW wall timings, not isolated GPU-kernel throughput. The resulting delay
is an open usability failure. A compact, unapproved LoRA candidate with original
request/output bytes and a generator brief is retained on llm-60.

The final answer suggested the guest NAT IP10.0.2.15; client reachability at that
address was not demonstrated. Testing used the owned host's loopback HTTP forward.
The application needs clearer client/remote URL scope and host-provided preview
facts. An internally correct page does not make that advice beginner-friendly.

Source integration commit efca748f, wheel
8299bf8569420897ee1cb30e62ba14026cf9eb5ab53892ee6ffd7ce41d5e7dce.
Q4 execution profile62a8bc71db2436477fc6e5c010d4357287034c04ea41123a887418694a5d42b6.
Raw private archive retains the complete session and resume. Keys were excluded
and checked absent. New Min-P follow-up is separate, with its own task/settings;
it is not a controlled sampler-only speed comparison.
