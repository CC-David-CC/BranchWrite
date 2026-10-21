# Lower-quantization BranchWrite domain trials

Question: can the installed client complete the existing coding, PDF, fixed-CAD
and Blender examples with IQ2_XS/IQ3_XXS without extra model-specific handling?

PASS means the actual output passes unchanged domain checks and required image
feedback is present in settled native requests. CLI self-reported success alone
is provisional. Different models need not produce identical text or logits.
A passing single trial is not a success-rate estimate or general equivalence.

Use the exact public prompts from examples/prompts with greedy selection first.
Each domain starts with an empty owned project. No operator candidate edits.
Keep failures. If a model-specific intervention is needed, record it as a
separate trial (Min-P, then targeted worked examples/constraints where useful),
never overwrite the baseline. Do not repeat an unresolved operation with a new
ID. Infrastructure failures are not mislabeled as quantization/semantic failures.

Hardware: llm-49 RTX4090; one active inference process. Both models use the same
native executable, FP16 KV, 32,768 context capacity, 8,192 prefill chunks, 4GiB
expert budget, 6GiB context pool, 16GiB disk pool and 8GiB host guard. These are
GSQ-RCO models, not a controlled bit-width-only ablation of the Unsloth Q4/Q8.
Historical Q4 examples used different hardware and sometimes prior history;
latencies are reported individually, not claimed as controlled Q4 speedups.

Checks:
- CAD: reopen the actual STEP, fixed dimensions/holes/notch/material/one solid,
  unchanged baseline tolerances, and actual views sent to the model.
- PDF: actual two-page ReportLab output, required sections, readable rendered
  pages, both actual page images sent to the model, current named checks.
- Blender: actual blend and controlled views, independently reopened animation
  with one arm rotating 45 degrees and other meshes stationary, actual 24-frame
  12fps video, image feedback. One useful-motion receipt alone is insufficient.
- Code: actual HTML in isolated Chromium at desktop and phone sizes, blue
  heading, three dog names, visible greeting after click, no overflow or
  unexpected external resources, screenshot inspection.

Record prompt/source/build/model hashes, immutable operation receipts, elapsed
whole-task time, actual output/work and tool attempts. Preserve failed source
and mitigation outcomes for later failure-class collection; do not train.
All working data stays on Linux. Back up reviewed code/evidence to LAN box-git.
No Strata upstream publication. No full G1-G5 qualification from this campaign.
