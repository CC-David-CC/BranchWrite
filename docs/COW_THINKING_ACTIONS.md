# Thinking before a file action

COW keeps the thought and final answer in one canonical continuation. BranchWrite
uses the server-derived final view after durable publication. It does not split
the raw text at a printed `</think>` tag, and it does not execute streamed text.

`branchwrite.cow_actions.completed_thinking_text` requires a complete final view,
the same snapshot as the durable receipt, schema version1 and a consumed EOS.
Missing or partial views fail; raw thought is never a fallback action. The
existing COW client returns this view unchanged through CLI and HTTP.

For an edit, the host chooses the file and grammar. JSON Schema constrains tool
name, path and argument types; `parse_replacement` independently rejects duplicate
fields, unexpected keys, other paths, empty preimages and excessive UTF-8 bytes.
The existing Executor then checks its Grant, the actual source hash and one exact
preimage before an atomic, flushed replacement. Syntax does not authorize work or
establish that the answer is correct.

The H04/H05 runner is `validation/run_basic_loop_edit.py`. It copies one supplied
fixture to an owned workspace, reads actual bytes, records proposals and receipts,
applies the authorized edit, captures the new revision in the Linux browser
namespace and gives only its PNG to an independent observer. Protected DOM/pixel
checks stay out of model inputs. H05 also requires a correct initial image report
before the edit. A model/tool/check failure remains a failure; no silent repair.

New tasks use1024 thinking tokens (owner update2026-10-18). Increase only when the budget is exhausted and
the task fails. Stop at success or natural closure. COW registry entries currently
select immutable budgets and final schemas; this is not a general thinking_length
CLI control. Each stage uses a separate prepared state. General thinking appends,
restart/fault coverage and the complete workflow interpreter remain outstanding.

Run source edits, tests and evidence collection on Linux. Windows drives SSH only.
The chat server stays off; Q8 is deferred. Private box-git is the backup destination.
The live results are in validation reports, not implied by the existence of this
runner. Numerical equivalence, performance and full VC/G certification are separate.


H06 now continues the verified H05 page with predecessor-receipt and source-hash
checks. The same runner admits H06 and the isolated browser invokes the unchanged
host-selected interaction checker: two actual counter clicks, with the returned
PNG captured afterward. The CLI returns the checked action witness as a JSON
string in its TOML receipt. This is not a general browser-command API. The bounded
current-profile run and limits are in validation/H06_Q4_2026-10-18.md. A larger-cap
natural-thinking cutoff study is deferred; the successful H06 edit exhausted512.

The shared DEFAULT_THINKING_TOKENS is now1024 for newly created contracts only.
The H04-H06 recorded512 budgets remain historical facts; saved active grammar
state must continue under its original budget. No new GPU run is required just
to rewrite those successes. End-to-end data collection is deferred by owner.
