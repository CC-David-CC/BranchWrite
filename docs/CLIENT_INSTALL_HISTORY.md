# Install the private Linux client

This is a development package, version0.1.0.dev16. It is not a public release.
The model and Context COW server stay on the inference machine. The client
needs Python3.11 or newer and the existing Linux bubblewrap/prlimit tools.
Installation and tool checks below were executed on Python3.14.4; other Python
versions and platforms need their own checks. Native Windows tools are not supported.

1. Get the client wheel, connection.json and server access from the operator.
   Do not copy the model or server repository.
2. Make a private Python environment:

       python3 -m venv ~/branchwrite-client
       source ~/branchwrite-client/bin/activate

   An environment is a folder that keeps this app's Python tools separate from
   the rest of your computer. Activate it in each new terminal.
3. Install the wheel from the file you received:

       python -m pip install --no-index --no-deps /absolute/path/branchwrite-0.1.0.dev16-py3-none-any.whl
       branchwrite --help

4. Use the operator's SSH/HTTPS connection. Enter the API key without putting
   its literal value into the command history:

       read -rs BW_COW_API_KEY
       export BW_COW_API_KEY

   Paste the key and press Enter when read waits. connection.json contains
   endpoint/profile identities and EOS IDs, not the key.
5. Put your task in a text file. Start with the command in CODING_LAUNCHER.md.
   Grant read/edit/create paths explicitly and supply a real test command.
   Choose a new branch and state directory for each new task.
6. Read the result. Work is in STATE/world/workspace; the original project is
   unchanged. Inspect it before copying changes into your checkout.
7. Continue an unfinished run with:

       branchwrite resume /absolute/STATE

The normal CLI uses the one existing interpreter and Context COW HTTP path.
It does not require a source checkout on PYTHONPATH. Images/browser use cases
retain their additional runtime prerequisites and have not been qualified by
these text-client installation checks.

## Current tested package and output handoff

The current private wheel is branchwrite-0.1.0.dev16-py3-none-any.whl.
Its SHA256 is 367a93ee855d6a9b5d6e38c327f96609ac32c12d37765bb80aef13ad319e3773.
Check the file you received with sha256sum before installing it. Keep the wheel
for an unfinished run; do not silently upgrade its pinned code.

The installed package passed90 controls outside the source checkout. In SC15,
two installed clients on llm-49 shared the llm-60 Q8 server with one active GPU
request at a time. Both coding tasks passed independent checks and complete
review/export/apply/retry/offline-resume handoffs. This is bounded evidence, not
universal coding reliability,a fresh numerical oracle or full G1-G5 qualification.
See validation/SC15-2026-10-19/STATUS.md. Keep dev15 for unfinished dev15 workflows;
the new interpreter identity is not an automatic ledger migration.

After a successful task, inspect its saved result and export a reviewed archive:

    branchwrite status /absolute/STATE
    branchwrite review /absolute/STATE
    branchwrite export /absolute/STATE /absolute/NEW-result.zip

The export command reports an archive hash. Use that actual hash below:

    branchwrite apply /absolute/NEW-result.zip --source /absolute/ORIGINAL --destination /absolute/NEW-copy --sha256 ACTUAL_ARCHIVE_HASH

Apply creates a new project copy. It checks the original source still matches
the captured input. It does not edit your original checkout or publish Git
changes. Linux user extended attributes and atomic no-replace directory rename
must work on the destination filesystem; unsupported storage fails explicitly.
An identical apply retry reconciles the existing copy instead of making a
second edit. A modified output or changed intent is rejected.

For another question using a prepared generic context, pass --from-prefix
BRANCH and optionally --from-snapshot ID. A new dev15 coding bootstrap separates
reusable controller examples from the current task's tool permissions and test
commands. Older task-bound prefixes remain unchanged. See CODING_LAUNCHER.md.
Whether a checkpoint is resident, restored or explicitly recomputed is reported
by COW; choosing a branch is not a GPU-residency promise.

## Build and check the wheel privately

In a source checkout with setuptools and wheel already available:

    python -m pip wheel --no-index --no-deps --no-build-isolation --wheel-dir /absolute/new-wheel-dir .
    python tools/verify_client_wheel.py --wheel /absolute/new-wheel-dir/branchwrite-0.1.0.dev16-py3-none-any.whl --work-dir /absolute/new-check-dir

The check makes a new environment, installs only that wheel, checks its package
boundary/examples, and executes real file creation and a read-only isolated
shell. It writes machine-readable result.json and logs under new-check-dir.
It runs no inference and does not certify GPU behavior, broad coding quality,
power-loss recovery or adversarial isolation.

The five packaged example assets are build-time copies of the existing
canonical examples. Source and installed workflow/prefix hashes were compared
and matched. A failed initial wheel omitted those assets; its failure evidence
is retained. No model prompt/example text changed to repair packaging.


## Historical shell readiness and version pins

Development build0.1.0.dev1 probes the actual shell namespace before model work for unfinished CLI runs. It runs no project code and contributes no task-completion evidence. Unsupported host namespace policy returns an explicit error; there is no unsandboxed fallback. Kernel logs on r730 show AppArmor denying setpcap/net_admin to unprivileged_userns; its0.1.0.dev0 wheel installed and opened normally,but the real isolated-tool check failed. No global protections were changed.

A read grant for an explicitly creatable file may refer to a file that does not exist yet. Shell projection now leaves it absent so baseline tests can genuinely fail before creation and pass afterward. Missing protected read inputs and links remain errors.

Keep old wheels/code for unfinished runs: tool-definition source hashes change with this host-boundary fix. Do not migrate a pending workflow silently. The live installedQ8SC05 pass used the pinned0.1.0.dev0 wheel;0.1.0.dev1 passed SC06 with two overlapping installed clients, independent task checks and offline completed resumes. See STANDALONE_CODING_STATUS.md for scope and limitations.

## Private dev22 candidate (2026-10-19)

Installed on llm-49 at
/home/dflanag3/spatial-artifacts/branchwrite-dev22-package-20261019-v1/venv/bin/branchwrite.
The existing dev21 environment remains unchanged. Dev22 includes reference-pack
refresh, pack-backed Project Base API admission, coding CLI pack pins, and local
recovery of acknowledged bootstrap after interruption before workflow admission.
Its64 installed client-side checks pass with the source package excluded from
the import path; all44 installed module bytes match the wheel. Source-level
HTTP/process-exit regressions pass separately. A real-Q8 run of dev22 remains
outstanding. See validation/project-base-three-builds-20261019-v1/dev22-installed.

## Current private dev23 candidate

Installed CLI on llm-49:
 /home/dflanag3/spatial-artifacts/branchwrite-dev23-package-20261019-v1/venv/bin/branchwrite

Exact source:c5fdb874436fb712d7ba443a156df08a325a1671.
Wheel SHA256:9e0dd41651edb73f2a919322a1cb7212f27ae3b830d67d9f10da85c1da448a66.
Private wheel backup:
 box-git:/srv/data/git/private_context_cow.evidence/branchwrite-dev23-20261019-v1

All44 installed module bytes match the wheel;64 installed client checks pass.
A small real-Q8 run on llm-60 passes root acknowledgment loss, actual server/native
restart, explicit original-ID reconcile and autonomous coding. The code repair
completed in53.090s; independent sandbox checks passed1000seeded pairs plus4edges.
The source project and protected tests were unchanged. See the dev23-q8-restart-coding
validation directory for raw evidence, earlier failures and exact limits.

The research server and temporary SSH forwarding/key have been shut down.
These facts do not imply a stable inference endpoint is currently running.
The one-shot campaign scripts are evidence, not an installer. A reusable service
launch/deployment path, automatic Project Base selection/refresh, and broader
workload qualification remain unfinished. Chat staysOFF.
