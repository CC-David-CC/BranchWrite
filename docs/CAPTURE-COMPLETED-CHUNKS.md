# Capture completed model turns that used several response chunks

A valid BW workflow could finish and pass its checks, yet its lesson/assessment
capture was refused because an intermediate native response had `stopped: false`.
That flag describes one response chunk. It does not say that the logical model
turn remained unfinished after later chunks arrived.

Capture now accepts a settled intermediate chunk only when its exact native
frame and completed logical `ModelOutput` owner are present. It still checks
the original request, endpoint, model/profile, receipt, journal and ledger bytes.
An open logical model output, unresolved dispatch, mismatched return, or partial
chunk without a ledger owner remains refused. No unfinished output becomes a
correction or training example.

The [qualification receipt](../validation/completed-chunk-capture-20261026/qualification.json)
records 22 passing CPU controls across the original capture suite, a real
multi-chunk correction capture, missing-owner counterexamples and budget
observations. A completed native MiniCPM workflow was then archived and graded
read-only with the corrected reader: BW verification and the independent code
checker both passed. No model generation was repeated to repair that archive.

## Observe a budget failure without calling it a lesson

```python
from branchwrite.coding_observation import observe_model_budget
evidence = observe_model_budget("/path/to/existing/bw-state")
```

This reads the actual frozen model plan, frame slots, grammar registration and
complete native journal. It verifies that all dispatched operations have settled,
the logical model output remains incomplete, and the request or output-token
limit has actually been reached. It performs no model or tool calls and does
not advance the ledger. An ordinary partial output with remaining budget is
refused rather than relabelled as exhausted.

The result is explicitly `training_eligible: false`. The completed-turn capture
gate still refuses that partial turn. S³ now uses this evidence in its standard
workflow panel: a proven budget failure scores unfinished/failed and the next
case can proceed. Uncertain dispatches and unproven bounds still refuse scoring.

`archive_model_budget(state, output)` freezes the original launch, ledger and
request receipts under BW's read lease. `read_budget_archive(output)` checks
their hashes, source implementation and actual budget evidence without the
original server or mutable world. These private archives contain no world
artifact verdict and have `training_eligible: false`; they are not lesson captures.
The original failed boundary remains readable if its live workflow is later
continued. An archive must use a new output directory.

Two additional S³ CPU integration checks exercise the complete two-case panel,
settlement, read-only archived regrading, tampered journal/launch refusal and
refusal of a false budget label while allowance remains. Together with capture,
assessment and recovery regressions, 33 checks passed. The same archive/reader
also verified the saved native MiniCPM budget failure with zero model/tool calls
and unchanged original ledger/journal bytes. This is a read-only native-evidence
qualification, not a new inference run of the updated generic S³ panel.

These observations do not invalidate previously admitted lessons: the discovered
bug refused a valid capture. The broader historical data still has its original
qualification limits; this fix is not a blanket requalification of old evidence.
