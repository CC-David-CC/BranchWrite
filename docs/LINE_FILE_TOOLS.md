# Line-based file tools

Use create_text_file for a new text file. Use replace_text_file for an existing
file that needs a complete replacement. Read the existing file first. For a small
edit, the older scoped replace tool is still available.

Both new tools take path, lines, line_ending and final_newline. For example:
{"tool":"create_text_file","arguments":{"path":"notes/example.txt","lines":["first line","second line"],"line_ending":"LF","final_newline":true}}

Each array item is one line without a CR or LF. The host joins the items with
LF or CRLF and adds exactly one final terminator when requested. It preserves
spaces, quotes, dollar signs and Unicode without normalization. [] with false
creates an empty file; [""] with true creates one blank terminated line.
A trailing empty item in a multi-line array with final_newline=false is rejected:
it would contradict the explicit absence of a final terminator.

The maximum is4096 line items and32768 encoded UTF-8 bytes. Invalid types,
embedded line breaks and unpaired surrogates are rejected. Grammar constrains
the shape; host validation remains authoritative, including escaped Unicode
line breaks. The schema compiler has a canonical key order; arbitrary JSON
wire ordering is not a newly qualified property.

Creation uses the exact existing create grant and cannot overwrite. Replacement
uses the exact edit grant and a fresh observed-source witness, with atomic
replacement, mode preservation and existing effect receipts. Final verification
still requires actual read_file after the last write. These tools create bytes,
not a new history, checkpoint or permission representation.

## Prefill examples

New coding roots whose schema includes the line tools receive three generic
worked examples from examples/line-file-worked-examples.txt. They demonstrate
literal Unicode/dollars/quotes, LF/CRLF, absent final newline, and whole-file
repair after an actual read. They contain no protected L02 answer or path.
Old raw-string-only roots keep their existing examples and identity.

Regenerate on Linux with the verified interpreter:
PYTHONPATH=. python scripts/build_line_file_examples.py --output examples/line-file-worked-examples.txt

The builder executes the actual file tools and independently checks bytes.
Observation IDs belong to its temporary world; regeneration creates a new
prefill identity. Existing saved roots/controllers are never edited in place.

## Executed evidence at source freeze

120 distinct CPU methods pass (23 new:18 file-tool and5 example methods),
zero failures/errors/skips. This includes8 actual COW CPU fixtures on llm-60;
the other client tests ran on llm-49.45 mask checks pass using the actual Q4
tokenizer and llguidance1.9.1. Initial red tests, the old closed-tool-menu
failure, the schema regex incompatibility and their corrected runs are retained.

The only changed existing test assertion is the exact closed menu, expanded
from4 to6 authorized tools. Protected workload bytes/checkers, numerical
equations and tolerances are unchanged. GPU/model behavior is UNRUN at this
commit. These are CPU/component results, not VC/G certification.

Artifacts:
llm-49:/home/dflanag3/spatial-artifacts/branchwrite-ubuntu-baseline-20261018-v1/line-file-tools-cpu-v1
llm-60:/home/dflanag3/spatial-artifacts/cow-vision-20261016-v1/bw-line-file-tools-cpu-v3
llm-60:/home/dflanag3/spatial-artifacts/cow-vision-20261016-v1/line-file-q4-grammar-legality-v4

Next: original protected L02 through real remote CLI, requiring actual use of
the new creation tool; then an independent existing-file replacement exercise.
Global DRY+Min-P defaults remain unchanged. Private LAN backup only.

## Completed real-Q4 trials

The original protected L02 acceptance passes unchanged using
create_text_file, read_file, finish.37 exact bytes including final LF;
36.459 seconds whole CLI,3 calls,503 consumed output tokens.
An independent owned repair fixture passes read_file, replace_text_file,
read_file, finish.39 exact bytes,CRLF/no final newline,0640 mode and unchanged
neighbors;45.079 seconds,4 calls,428 output tokens. Both use global-default
DRY.8+Min-P and4096 thinking,with actual CLI49 -> HTTP60 -> GPU Q4.

No model actions were supplied between calls. One success per task does not
establish statistical robustness,causal improvement or a speed benchmark.
The earlier raw-string failures remain recorded. Both services and native
processes exit0;client/tunnel absent,scoped keys revoked and credentials retired.
No model/GPU files were exposed to the client. Unauthorized401 caused zero work.

Private evidence details are in CURRENT_STATE.md and
provenance/LINE-FILE-TOOLS-Q4-2026-10-18.json. No GitHub push or model training.
The existing source-workspace copier does not preserve0700 directory modes;
setupv8 detected this and stopped before inference. This delivery tests file
mode preservation,not arbitrary directory-mode cloning.
