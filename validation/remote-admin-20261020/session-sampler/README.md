# Interactive sampler choice for new admissions

Dev53,2026-10-20. branchwrite session --sampler min-p (or dry-min-p) now reaches
the interactive workflow. Ordinary no-argument startup still defaults to greedy.
An explicit option changes only newly admitted requests. Recovery reads the saved
launch and never overwrites an old controller or resends an unresolved effect.

Three new session tests check selected settings, recovery under a different
startup option, and early rejection of unknown profiles. A CLI test checks both
explicit session and --sampler shorthand. Current combined suite454/454 passed,
no failures/errors/skips and source unchanged. Installed real PTY on llm-49
printed Min-P, exited0, retained no key in output and submitted no model task.
This is not a real-GPU Min-P quality or performance result yet.

The initial dev52 suite had4 failures because no-option startup passed a new
unrequested keyword to the established launcher. The implementation now omits
that option unless explicitly provided. Existing tests were preserved. Both
failed output and the final suite remain here.

The need was observed in the independent dev51 Q4 autonomous coding/deployment
pilot: greedy thinking repeatedly enumerated an irrelevant checklist. The task
had created and uploaded a file but had not yet completed. Its run is unchanged
and retains its original greedy profile. One episode is not a model failure rate.
Candidate capture (not approved or trained):
/home/dflanag3/src/branchwrite-lora-examples/candidates/greedy-thought-checklist-repetition-20261020/.
