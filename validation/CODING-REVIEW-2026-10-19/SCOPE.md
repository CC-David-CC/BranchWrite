Read-only RuntimeLog opening is a prerequisite for CLI status/review/export.
It uses the existing canonical format/replay and shared existing writer.lock.
It creates no files, rejects an active writer, never initializes an empty log,
and refuses artifact/event publication. Six distinguishing tests failed before
implementation and pass afterward. All21existing record regressions pass.
The reader also successfully opened the settled SC08 program as Closed/verified.
No review/export CLI command or guarded publication is implemented yet.
This separate dev5 branch must not silently replace a running dev4 interpreter.

Read-only status is now implemented. Seven test-first CLI cases passed, alongside
47 existing record/reader/kernel cases (54 total). A new process inspected the
settled real SC10 run: 239 events, 74 Closed frames, no pending operations, recorded
verification true. Every canonical ledger file remained byte-identical.
This does not revalidate current workspace bytes or export/apply changes.
