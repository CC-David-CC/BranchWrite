# Read a captured coding action sequence

`branchwrite.lesson_actions.captured_action_turns(directory,
expected_capture_id=...)` is an optional, read-only export of BW's actual captured
model inputs, tool proposals and settled tool outcomes. It is not a workflow
cursor, replay mechanism, correctness verdict or training approval.

The reader first validates the original capture. It uses BW's existing model
adapter and native receipt readers to reconstruct completed logical outputs,
including outputs spanning multiple native chunks. Each output must match its
original result artifact and the tool admitted by the same program frame. For
edits, the host-added source hash must match the original read observation.
The next input is read from the recorded request; tool feedback is not invented
from a later file state.

Initial support requires one context-only system bootstrap and a single chain of
completed, grammar-constrained JSON tool actions. Thinking, images, branches,
retries, unknown prefixes and partial logical outputs are refused. These need
separate qualification before they can be exported faithfully.

The reader constructs no network transport, executes no tools and never mutates
the original workflow. It continues to work from the capture when the original
workspace is unavailable. Consumed token IDs remain evidence of the original
run; they are not automatically valid training tokens for a different renderer.

S³'s optional action-practice adapter independently verifies owned practice
artifacts and renders these logical turns through PCC's actual append API. S³
owns curricula, split protection, scoring and lesson approval. PCC owns native
tokenization, model identity, memory, backprop and checkpoints. BW owns this
workflow evidence and its tool contracts.

CPU capture tests exercise the actual BW/COW/file/check boundaries with scripted
proposals. They establish archival/export behavior, not a model improvement.
