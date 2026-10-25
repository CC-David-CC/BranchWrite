# Ordinary POSIX shell paths inside BW's restricted world

BW's Linux namespace exposed `/usr/bin/sh` but omitted `/bin/sh`. Python's
`subprocess.run(..., shell=True)` uses `/bin/sh` by default, and executable
scripts commonly use a `#!/bin/sh` shebang. Both could fail even though calling
`sh` through PATH worked. The new read-only `/bin → usr/bin` alias fixes this
layout in both terminal execution and the registered unit-test worker.

The alias points to the same already mounted read-only system binaries. The
workspace, home, credentials, network and capability boundaries are unchanged.
The runtime identity binds the changed source; existing admitted workflows must
keep their original inspected implementation rather than being silently resumed
under this change.

## What verified the change

The four direct boundary checks establish that:

1. Python `shell=True`, explicit `/bin/sh` and an executable shebang work inside
   the actual namespace; the host home and shadow file remain unavailable.
2. Writing through `/bin` fails on the read-only filesystem and creates no host
   binary.
3. `/tmp` is private and fresh for **each invocation**. A file created there by
   one shell call is absent in the next. Use granted project files for state that
   must persist between tool calls.
4. The registered unit-test worker supports Python `shell=True` as well.

Before the runtime patch, three of these checks failed and the existing fresh
temporary-directory check passed. After it, all four passed. The broader 107
checks passed across execution, command verification, shell grants and output,
CLI/HTTP transport, selected project checks, restart and reconciliation.

The first broader run passed 99/100; its scripted COW HTTP fixture did not
advertise current discovery metadata. The fixture now advertises the same pinned
identities as its scripted model, without bypassing discovery. Intermediate
launches with incomplete optional fixture import paths are retained privately as
operator setup errors. They are not model failures or product regressions.

S³'s stronger host-controlled shell check subsequently passed the correct
reference using explicit `/bin/sh` and rejected both declared faulty programs.
The earlier model-proposed check still missed the quoting fault. This repairs
an environment defect; it does not prove MiniCPM now completes the previously
unresolved fifth shell workflow.

[Source and check receipts](../validation/minicpm-shell-investigation-20261024/posix-namespace-aw.json)
are public-safe aggregates. Raw commands, model histories and private task
artifacts remain outside Git. See the [preceding model probes](MINICPM-CHECK-PROGRESS-EXPERIMENT.md)
for the current behavioral limits and [S³'s reusable check probe](https://github.com/CC-David-CC/sss/blob/feat/minicpm-baseline-20261024/docs/CHECK-SENSITIVITY.md).

The [completed temporary-lifetime follow-up](MINICPM-CHECK-PROGRESS-EXPERIMENT.md#explicit-temporary-file-lifetime-a-completed-negative-result)
keeps this contract explicit in the model tool card. Both conditions still
completed four of five workflows; the remaining termination failure is open.
