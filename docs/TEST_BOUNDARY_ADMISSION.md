# Admit the execution boundary before model work

The CLI now runs a trusted readiness command inside the actual registered
unit-test sandbox before making any COW HTTP call for an unfinished workflow
with a test grant. It does not import candidate code or run project tests.
Completed local replay does not probe or start another process.

C01's first autonomous Q4 run reached its900-second harness deadline. Its outer
client filesystem namespace prevented the nested test sandbox from starting:
five run_tests calls returned a bubblewrap namespace permission error.
The model accurately reported the blocker; the workflow then attempted more
planning. Thirteen settled model calls consumed10791 output tokens before timeout.
The candidate later passed9 public tests and3 independent held-out methods
(including64 generated CSV datasets). This is code evidence, not an autonomous pass.

The distinguishing new regression uses a real outer namespace with further
user namespaces disabled and asserts rejection before the HTTP constructor.
The positive probe executes the real bubblewrap boundary with an import tripwire
in the project tests. Admission never imports that file.

35 focused boundary/execution/CLI/observed-preimage/task-verdict methods passed.
The initial broader CLI discovery ran48 methods with22 environment errors
(missing COW imports and BW_BASIC_LOOP_PACK); it is retained, not called a pass.
A complete current integration suite and corrected live C01 rerun remain pending.

The cross-host audit must run the trusted CLI on the host for test/browser/shell
work, retaining each untrusted tool's own sandbox. Its Python access audit is
evidence about this trusted client, not adversarial containment of the CLI.
Do not grant additional tool capabilities to select an audit layout.
No global namespace protection was disabled.
