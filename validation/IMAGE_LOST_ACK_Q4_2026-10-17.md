# Q4 image completion-loss recovery: bounded mechanics PASS

Both retained questions completed through the actual CLI/HTTP/COW/GPU path.
The proxy withheld the real completion after durable publication. A new Python
client process reopened the original pending intent, reconciled its receipt,
and returned it without another model evaluation. Each request was dispatched
once. Native traces were byte-identical across reconciliation/retry/rejection
controls; saved-prefix checkpoint bytes were unchanged.

| Question | Image answer | Quality | Saved prefix cells | New output forward tokens | Recovery forward tokens |
|---|---|---|---:|---:|---:|
| Expanded H02 | LEFT | PASS | 355 | 2 including EOS | 0 |
| Short | NOT_VISIBLE | **FAIL: accepted model edge** | 320 | 4 including EOS | 0 |

Both prefixes include 300 actual image rows. Same original PNG SHA256
`414bcbf649fc99734f5c7481cc33c84ce3031fc35443f4bdae470397efa532b8`, same actual
encoder embedding identity; the question differs. Neither case used thinking.
The host's correct label stays LEFT; all three grammar choices stay legal.
The owner requested both questions be retained and the short-question miss
documented while proceeding with Q4. The protected H02 oracle, numerical
equations/tolerances and registered gate assertions are unchanged. A recovery
PASS does not convert a wrong model answer to a quality PASS.

Prompts are retained in `fixtures/image_questions/{expanded,short}.md`. The
expanded text hash matches the original executed H02 question. Q8 must test
this exact pair in a later end-to-end campaign; the owner deferred Q8. Only
read-only model/profile metadata inspection occurred; no Q8 inference ran.

## Fixes and executed checks

The original CLI used exit 2 for both rejection and uncertain completion, while
BranchWrite inferred rejection from 2. New opt-in machine error envelopes
distinguish rejected from indeterminate outcomes. Existing exit codes/stderr and
success envelopes are preserved. Unknown legacy errors and malformed/other-ID
error frames remain indeterminate. Original intent is kept, never auto-resent.

Final CPU results: complete BranchWrite **338/338**, COW CLI **51/51**, launcher/
grammar **7/7**, G0 **51/51**; zero failures/errors/skips. BranchWrite full suite
28.147 seconds. CPU image fixtures use actual sockets/CLI/store with synthetic
inference; they are not substituted for the GPU cases above.

Failed attempts remain archived:

- COW machine-error RED: two errors; BW lost-reply RED: one error, incorrectly
  classifying the actual post-commit EOF as rejected.
- Malformed error-frame RED: four methods, two failing subtests; missing/extra
  identity fields could falsely imply rejection. Strict frame validation fixed it.
- Quality-verdict helper RED: one missing-helper error. Its regression requires
  legal-but-wrong answers to remain quality FAIL; incomplete/illegal answers reject.
- First GPU short question committed NOT_VISIBLE and stopped before recovery on
  its quality assertion. Read-only reconstruction from canonical state proved
  the image provenance matched H02 and the consumed IDs were
  45,1730,55275,248046. `MODEL-QUALITY-DIAGNOSTIC.json` preserves the failure.
- First paired run passed the expanded case, then its short-case server failed
  before inference: a random API key began with `-` and argparse saw an option.
  A new real-argparse regression first failed, then passed after the shared
  launcher used `--api-key=VALUE`. Final GPU cases deliberately use leading-dash
  random credentials, with no loss of entropy and no key retained in evidence.

Final paired wrapper/command exits 0/0. Expanded service64401/native64407 and
short service64582/native64590 exited0 and were observed absent. Recovery client
PIDs64569/64936 exited0/absent. Earlier failed-run processes are also retired.
No GPU job remains. Chat stays off. Native/CUDA engine is unchanged.

Saved-prefix checkpoints audited: expanded128355220 bytes; short127421192 bytes.
Actual image upload1984 bytes; embedding3072020 bytes. Full RAM/VRAM peaks and
end-to-end performance were not measured; these tiny outputs are not a TPS
benchmark. No independent fresh full-logit oracle ran; numerical max error is
**unmeasured**, not zero.

## Reproduction and fingerprints

llm-60 GPU=[0], RTX PRO6000 Blackwell96GB, driver595.91.07,
Qwen3.8-Flash-Next UD-Q4_K_XL, FP16 KV, capacity98304, prefill chunk512.
Native SHA256 `ae62045f75a8e11ba9d01b4da301d3bb87fe4ff342bab0ea7edc57276377824e`.
Model contract `387bbc46f184b148ff455b50a9037132da32d6fed83abba7eb63e57b33f12b53`.
Execution profile `f2ff15027423ea953861147a2b2284a2a48149cdf9cb5e41510251b98f177175`.

Under `/home/dflanag3/spatial-artifacts/cow-vision-20261016-v1/`:

- COW frozen source `cow-image-ack-green-source-v2`; BW source
  `branchwrite-image-ack-green-source-v5`.
- Profile `cow-image-ack-profile-v2/profile.json`; 50 runtime/launcher files pinned.
- Actual results `branchwrite-image-ack-{expanded,short}-gpu-v2/result.json`.
- Exact driver/launcher `run-image-ack-pair-v2.py`, `launch-image-ack-pair-v2.sh`.
- Manifest `branchwrite-image-ack-collected-v1/summary.json` includes all failures,
  source hashes, work/bytes, controllers, proxy records and process outcomes.

Runtime/test/question hashes match local source. Private receiver-verified
archive `/srv/data/git/private_context_cow.evidence/20261017-branchwrite-image-ack-v1/evidence.tar.gz`,
15387229 bytes,567 members, SHA256
`238ad21598a8b786da8777e1a17d153c660f1b285ab9bc4c21b3478113969479`.
1023523488 derived native-state bytes excluded/hashed/retained on llm-60.
Canonical records and raw receipts are archived. No raw archive went to Windows.

This closes a bounded VC06 lost-ACK subcase, not full VC06/VC09 or original
G1-G5. Server/native restart after lost acknowledgment is not tested: operation
lookup remains coordinator-process scoped. Broader faults/formats/controllers
and full qualification remain. Next owner priority is actual bounded,
state-dependent thinking; its controller/CLI are not yet implemented. See
[state thinking](../docs/STATE_THINKING.md) and [the implementation plan](../docs/THINKING_AND_GOLDEN_PATH.md).
