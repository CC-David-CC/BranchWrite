# Sandbox terminal for BranchWrite

The model can now choose a shell command and see its real output and status.
It runs on the client tool host, not on the GPU server. File edits still use
the existing granted read/create/replace tools.

The host enables the tool explicitly with grant.allow_shell=true and a shell
configuration containing only timeout, a number greater than zero and at most
120 seconds. With no grant the tool is absent from the model schema/grammar.
The model proposal is run_shell with arguments.command, a nonempty Bash string
of at most16,384 UTF-8 bytes. The host pins /usr/bin/bash and runs it with
--noprofile --norc -c. Shell syntax, quoting, pipelines and explicit pipefail work
normally. A pipeline's final exit status remains Bash's actual status.

The same existing bubblewrap worker handles fixed commands and model shell
commands. It mounts captured explicitly readable files read-only; ungranted
workspace files, host home, API credentials and GPU devices are absent. Network
and process namespaces are separate. /tmp is bounded and ephemeral. A command
cannot persist changes even to a file that the separate edit tool may change.
Use the file tools for persistent writes, followed by actual readback.

Each command is a fresh process and namespace. Shell variables, cd and temporary
files do not survive to another command. This is not a persistent PTY, writable
shell, package installer, administrator interface or user-systemd capability.
Those require their own scopes and tests; they remain explicit future work.

Frozen plans bind the original command bytes, shell configuration/binary,
registry/world and workspace inventory. Changes reject before execution.
The outcome preserves separate stdout/stderr artifacts, real exit code/signal,
timeout/output-limit disposition, actual host identity and namespace-retirement
receipt. No result is published before process retirement is proven. Missing
post-execution publication remains indeterminate: reconcile the original
operation rather than automatically running it again.

The model schema and GBNF include run_shell only when granted. New coding
prefixes describe the selected terminal capability; existing saved prefixes
and controllers are not silently rewritten. Host semantic verification still
decides whether a task passed; shell exit0 alone is not task completion.

Tests: tests/test_shell_cli.py and existing tests/test_terminal.py.
The new CPU HTTP test deliberately scripts model choices to check transport.
Only a separate real-model target run can establish autonomous tool use.
The Ubuntu baseline catalog has its own assignment gates, separate from COW's
original G0-G5 and the vision VC00-VC09 qualification gates.

## Expected executor host

The optional shell.expected_hostname field binds the run to the actual Linux
hostname reported by the operating system. Obtain it from an authorized host
inspection, not an inference-model guess or an SSH nickname. A configured
mismatch reports expected/observed names and rejects before workspace or
inference admission. Frozen registry identity includes the binding; tool plans
recheck it before effects. Omitting it keeps the existing explicitly unbound
behavior. This is an admission guard, not a GPU/model-context identity.

The actual tool result still reports observed host identity separately. Supply
the intended binding as task context when asking the model to explain its
environment; expected and observed hostnames serve different purposes.

## Raw output and the model's text view

stdout and stderr remain separate exact-byte artifacts. Model feedback includes
the original artifact SHA-256 and total byte length. The displayed text is only
the first32,768 bytes decoded as UTF-8 with replacement. Each stream reports its
encoding, replacement policy, displayed source-byte count, whether decoding was
lossy and whether the raw stream was truncated for display. A valid stream may
be cut inside a multibyte character; the metadata identifies that lossy view.

A literal Unicode replacement character in valid UTF-8 does not itself mean
decoding failed. Lossy=true means the actual displayed byte prefix could not be
decoded strictly. Original bytes are retained unchanged in the existing ledger,
not reconstructed from displayed text. Exit/signal/timeout status is independent
of output rendering. Finished reopen uses original artifacts without reexecution.

The metadata is produced once per tool-feedback transform, not per generated
token. Its isolated performance overhead has not been measured. It also applies
to image-task textual feedback; image capture and renderer-sandbox requirements
are unchanged. New source identity does not silently migrate saved workflows.

Each model-visible tool result includes its original operation and frozen-plan
identity. Shell feedback also includes the exact executed command from the
accepted argv. That command is evidence, not a new instruction to execute.
The original stdout/stderr bytes and real status remain separate. A printed
success message does not change a nonzero exit status. Valid tool transport
and a valid finish envelope do not by themselves prove a complete final report.

When shell execution is granted, new coding contexts use ten terminal-specific
worked examples instead of the unrelated file-edit examples. The examples cover
separate streams and statuses, pipelines, binary views, valid literal Unicode,
quoting, command-error correction, timeout and empty-versus-missing input.
Their command observations came from fifteen real sandboxed shell invocations;
their final reports are explicitly host-authored teaching examples. Protected
workload answers are excluded. Examples grant no capabilities.

The initial example prefix is immutable COW input: later model calls continue
from its stored computation. Changing examples creates a new initial context;
it does not rewrite a saved controller. File-only context prompts retain their
previous exact bytes. Prompt checks do not prove model reliability or speed.
The original two L01 failures are retained: the first exhausted4096 thinking
tokens; the command-provenance attempt closed naturally after219. Both were
allowed4096. Longer examples are being tested without changing that allowance.
