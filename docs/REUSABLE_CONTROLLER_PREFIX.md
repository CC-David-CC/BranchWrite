# Reuse examples without inheriting another project's commands

New inline coding bootstraps with a task use controller_prefix v1. It contains
tool-family instructions and worked examples, not project paths, exact argument
permissions or required completion commands. The native grammar and host grants
remain authoritative; examples grant no execution rights.

Each new task, including the first bootstrap, receives a current HOST TOOL
CONTEXT card with its exact schema and command requirements. That card is part
of the consumed task input and is frozen with the workflow. Resume reconstructs
the same card from saved configuration, not a newer project's policy.

Within one tool family, changing file names or required commands leaves the
controller prefix bytes identical. Different tool families or context-pack
identities can produce different prefixes and must not be presumed equivalent.
Context packs remain exact verified input; their bytes are not silently refreshed
inside a saved prefix.

To obtain a new reusable root, start a new coding run without --from-prefix.
Subsequent new runs can select its initial root through --from-prefix BRANCH.
Existing task-bound snapshots remain immutable. They are not retroactively
cleaned and may retain old commands, as SC12 demonstrated. Choose a new root
rather than pretending old prompt text disappeared.

The existing system_prefix helper remains task-bound for explicit raw workflows
without current-task-card bootstrap, preserving that API's actual contract.
It is not the generic cross-project controller-prefix interface.

Four focused tests and a real subprocess/HTTP CPU test establish structural
separation: two distinct projects have identical root text and distinct current
cards.266regressions and75fresh installed controls pass. No new GPU numerical or
autonomous cross-project reuse campaign ran for this change; that is next.
