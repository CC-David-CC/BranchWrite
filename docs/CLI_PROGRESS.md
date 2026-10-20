# CLI progress

New coding/run/resume execution displays bounded status lines on stderr:
Working on model output; Model step recorded; Running a tool; Tool result recorded.
Stdout remains the existing machine-readable receipt. No raw thoughts, tool
arguments, file contents, credentials or mutable frame values are displayed.

These are provisional observations, not extra workflow records or success
acknowledgments. A started event does not prove an effect occurred. A model step
can end at a partial/budget boundary; a tool result can be a rejection or command
failure. Read the final receipt, review and actual command evidence.

The existing owning interpreter emits the events around its existing dispatch
path. There is no polling reader of a live ledger, second scheduler, shadow
history or extra model request. A broken observer is disabled; a closed stderr
pipe does not change operation identity, retry an effect or lose its receipt.
An already completed workflow reopens quietly and returns its original result.

Five new filesystem/subprocess tests and one real HTTP CPU fixture pass, within
272 selected controls. These are not GPU quality or numerical tests.
This change modifies the interpreter source identity. Keep dev15 for unfinished
dev15 runs; do not migrate their ledgers silently. A new package/run must be
qualified separately. General request heartbeats/streamed token display and
elapsed-time estimates are not implemented by these phase events.
