# Execution integration update,2026-10-18

The read-only reader checkpoint below is historical. `run` and `step` now call
the same FrameKernel-backed Interpreter. Only the explicitly supported handlers
in [AUTONOMOUS_RUN.md](AUTONOMOUS_RUN.md) are executable; syntax recognizes more.
No syntax check or scripted CPU model proves autonomous task ability.

---

# Read a BranchWrite program

A .bw file is a list of instructions. The new check command checks how those
instructions are written. It does not run them. It does not ask a model a question,
edit a file, run tests or grant permission. This is the program reader for the
existing durable controller; the general execution command is still being built.

From this repository on Linux, use the configured Python interpreter:

```sh
python -m branchwrite check examples/bounded-revision.bw
python -m branchwrite canonicalize examples/bounded-revision.bw
```

check prints a statement count, the canonical source SHA256 and Execution: NOT_RUN.
canonicalize prints a consistently formatted copy; it does not change the source
file. It keeps literal data unchanged. Both commands need valid UTF-8 and LF line
endings, including the final newline. They reject CRLF rather than silently changing
source identity. A source file over1000000 bytes is refused before parser entry.
The reader verifies the opened file descriptor is an ordinary file. On Linux a
nonblocking open lets it reject a FIFO without waiting for a writer. There is no
run/step command yet; an unsupported command exits with an error.
The existing COW CLI remains a separate, already-tested client to the inference server.

## One production definition table

branchwrite/language.py defines14 operations, six structural blocks and two data
constructs. Required/optional fields and block classification come from one immutable
production table. Parsing and canonical rendering use that table. The independent
reference parser remains unchanged and is imported only by tests.

The production parser uses an explicit stack and frozen Statement records. Structural
blocks require END; it never repairs a truncated program or mines instructions from
prose. Names and atom fields follow the documented ASCII syntax. Duplicate or unknown
fields, old verb aliases, invalid result arrows, shell metacharacters, noncanonical
control whitespace and invalid repeat bounds are rejected. REPEAT bounds are canonical
positive decimal integers at most1000000. The default limits are1000000 UTF-8 bytes,
32 structural levels and10000 statements. Resource limits are exact integers, not bools.

TEXT payload lines lose exactly one leading literal prefix and retain their LF. END
inside a prefixed payload, JSON, code, Unicode and instruction-looking text remain data.
The parser splits only on LF; Unicode U+2028 stays inside literal text. Rendering sorts
fields, emits one ASCII space and preserves literal bytes under the documented LF rule.
Arbitrary source/binary bytes still belong in byte artifacts, not lossy text conversions.

Syntax does not resolve a name to a typed result, decide sibling visibility, acquire a
world grant, prove plan freshness or implement a handler. A parsed COMMIT line has no
publication authority. Those checks belong to admission and the single FrameKernel.
Parsed Statement trees are transient views of source, not a second workflow ledger.
The eventual interpreter must retain source bytes as its program definition and derive
its program position/locals/waits from the existing canonical runtime records.

## Derived finite control contracts

branchwrite/control_contract.py turns a bounded host-eligible choice set into a frozen
ControlContract. Every choice must parse as exactly one operation; blocks/data/prose and
multiple commands cannot masquerade as a control return. The contract binds the host
frontier digest, production implementation identities and canonical choices. Equivalent
field order has one semantic identity. Choices are sorted/deduplicated, so arrival order
does not change the grammar. An eligible singleton is explicitly host-derivable and does
not require an invented model inference.

The GBNF emitter permits canonical serialized choices. The host parser can accept an
equivalent field order, while the emitted grammar intentionally selects one canonical
order. The actual COW CPU grammar matcher accepts the canonical choices and refuses a
foreign plan and partial completion. This is CPU matcher coverage with TinyByteTokenizer,
not full real-model vocabulary, GPU generation or grammar/controller restart qualification.
Contract.accept checks frozen membership; execution still rechecks actual permissions,
inputs and relevant state. A frontier hash is not a capability.

This is a finite control grammar, not a universal recursive program grammar or an automatic
COW inline-schema endpoint. COW currently selects named startup registry states. Dynamic
admission and integration with model-invocation/tool routing remain separate work.
Explicit JSON/JSON Schema model output is supported beside GBNF, per owner policy; the
canonical .bw program is still typed text. JSON data does not become a second workflow.

## Evidence and next implementation

The focused suite compares production results to the independent oracle for published
examples, all22 definition rows and120 seeded programs. It tests literal Unicode/LF
fidelity, field-order identity, malformed/truncated programs, exact bounds, immutable views,
hand-constructed invalid trees, finite-choice identity/admission and actual CPU GBNF
compilation. Actual CLI subprocesses verify UTF-8 byte output, source immutability,
invalid UTF-8/CRLF, oversize rejection before parsing and syntax-only operation with
network/process dispatch disabled. A real FIFO test first timed out at10 seconds;
the corrected reader returns its regular-file error without waiting. See the
companion validation JSON for IDs and totals.

Initial new-test source had quoting errors; raw failures were retained. PowerShell transport
also replaced literal Greek/emoji test data with question marks; fixtures now use ASCII
Unicode escapes evaluated on Linux. One multibyte bound was corrected to one byte below
the actual17-byte fixture. The GBNF positive fixture now uses canonical field order;
noncanonical emission rejection is explicitly retained. No existing test, reference
parser, acceptance record, tolerance or mathematical specification was edited.
These are engineering fixture issues, not model failures or LoRA training examples.

Next: resolve typed inputs and compile/admit workflow instructions to the existing kernel,
connect ModelOutput to frozen tool plans and typed tool returns, implement protected
completion verification and expose step/run through that SAME interpreter. Then run
unfamiliar coding workloads on Q4 and qualify the supported image/controller path. Do not
replace this with one hard-coded strategy per H fixture. Current model/tool components
are not a complete autonomous task loop or the full .bw operation implementation.

New thinking admissions remain1024; saved512 successes are unchanged. No new GPU run,
numerical oracle, performance result or VC/G gate promotion is claimed. Linux execution,
private box-git only, chat server OFF and Q8 deferred. No generated data is written to
Windows. The archive is component evidence/source, not a standalone installer.
