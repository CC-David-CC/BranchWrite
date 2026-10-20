# File tasks without a unit-test grant

Use examples/file-task.bw with the same Interpreter and FrameKernel as coding.bw.
The difference is the explicitly named file-readback-and-finish VERIFY contract.
It does not execute tests, judge arbitrary meaning or trust a model verdict.

The host config may supply a closed verification object:

    "verification": {
      "schema": 1,
      "files": [{"path": "result.txt", "sha256": "<expected lowercase SHA256>"}]
    }

One to64 distinct expected paths are allowed. Each must have a read grant.
The host determines these expectations before admission; the model cannot set
or change them. The policy identity and host-config digest bind the workflow.
Changing expectations cannot resume an existing run. Caller mutations cannot
alter a frozen policy. Old workflows must retain their pinned code/config;
this increment does not introduce automatic interpreter identity migration.

A pass requires an explicit actual finish request, matching current file hashes,
and completed read_file receipts from resumed predecessors in this lexical run.
The read stdout artifact must hash to the expected bytes and match the observed
world/path/digest. A creation or edit observation is not readback. A closed read
child before parent resume is not visible. Reads in other runs cannot count.
Actual files are rechecked under the existing world lock/no-follow reader when
VERIFY runs and again when the scope closes. After a run closes, reopening it
returns its original receipt; it does not certify later external file changes.

Canonical history, model controllers and native state remain COW-owned. This
policy adds no transcript/cache database or model/tool decision loop. The CLI
uses the existing copied workspace and real granted tools. Read bytes remain in
the existing artifact ledger. Native execution and sampling are unchanged.

When no run_tests capability is granted, the initial instructions require file
readback and actual-content reporting instead of demanding unavailable tests.
The three existing coding examples remain illustrative, not permission grants.
Tool grammar still permits only the live registered tools and paths.

A protected workload checker remains separate and unchanged. A file policy pass
does not prove browser rendering, correct image interpretation, valid edits,
general coding ability or G/VC certification. For H00, independently inspect the
original pack byte check plus actual model-selected create/read/finish receipts
and the final report; do not insert protected fixtures into model context.

The smoke harness accepts --workload-config for a host-owned source/task/grant/
workflow/verification/checker description. Only task text and live tool schema
are admitted to the model. Independent checker argv is a trusted host setting,
never model text. Checker source hashes are checked before service start and
again before execution. File-only checkers may read bytes on the host. Any
checker executing candidate code or HTML must retain the existing authorized OS
sandbox; a working directory is not containment. The original H00 checker only
reads files. Browser/interaction/image feedback integration is a later increment.

## Page capture tasks

Use examples/page-task.bw and page-capture-and-finish for supplied source whose
expected bytes the host knows. Add captures to the same verification object:

    "captures": [{"path":"index.html", "width":640, "height":480}]

Each captured path must also appear in files and have read/capture grants. The
host browser must select the same viewport. The compound policy requires the
file readback policy plus a completed capture of those exact source bytes. It
checks the served digest, actual PNG artifact/size/viewport, Chromium sandbox
witness and fully exited browser namespace. A model finish alone, a missing
capture, stale source or a file-only policy cannot satisfy capture completion.

Host browser config is closed: executable, width, height and timeout. No model
may select executable/options or a protected inspector. The grant has an optional
capture_paths list; read permission alone does not authorize rendering. Default
coding/test behavior is unchanged when no capture capability is registered.

Tool feedback now includes the actual PNG hash/byte count and capture metadata.
CLI stdout adds artifacts entries with media_type, SHA256, byte count, actual
ledger path, source path/revision and tool frame. These reference the existing
immutable artifact ledger; no extra history/database or fake image is created.
Reopening completed work returns the same artifact receipt without re-rendering.

This is not a generic page correctness judge. H01 additionally passes the original
protected pixel assertion on the actual returned PNG. Pages that the model creates
or edits need a separately selected protected acceptance policy; an expected hash
for a supplied file is not sufficient for those later tasks. Image delivery and
model visual interpretation remain separate H02+ work.

The existing canonical artifact ledger has a4MiB per-artifact bound, while the
browser worker's capture bound is8MiB. H01's1984-byte PNG is within both. Larger
high-entropy screenshots can exceed the ledger bound and cannot qualify this
workflow without a separately tested bound/publication change. That coverage is
outstanding; no larger screenshot or viewport certification is claimed here.

For newly generated pages whose future bytes are unknown, the separate
page-inspection-and-finish contract now checks current read/capture receipts,
protected sandboxed DOM/pixel assertions and exact checked/captured PNG identity.
See GENERATED_PAGE_COMPLETION.md. Fixed-source expectations above stay strict.
This component has browser/CLI fixture coverage; autonomous H03 remains UNRUN.
