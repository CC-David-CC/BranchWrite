# Next autonomous real-project feature

Add --task TEXT as an alternative to --task-file PATH, with exact literal text,
mutual exclusion, nonempty validation and file compatibility. These are new
protected regression tests, not a supplied patch. Baseline:6methods,4failures,
2passes. Fixtures include Unicode, actual newlines, quotes, $HOME and shell-like
literal text; nothing executes it. No model run has started.

The task source is actual BranchWrite source exported from dc9ef4f and committed
as an owned Git checkout. The upcoming installed dev3 client must exclude .git
and preserve the original source/admin. Model edit scope is only __main__.py and
coding_cli.py. Context COW still owns all inference state. Prefer the completed
SC08 initial system-prefix snapshot when available, with exact original source
branch/snapshot IDs recorded before admission; do not reuse unrelated task history
merely to claim reuse. Fresh-oracle numerical certification is separate.
