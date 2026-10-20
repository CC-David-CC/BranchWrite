# Separate BranchWrite client and COW server

The active client checkout is on llm-49:
/home/dflanag3/src/branchwrite-cross-host-client-20261018
Inference remains on llm-60, using the pinned Q4 profile. Windows steers SSH and
transports code/evidence in memory; it does not run workloads or store outputs.

The public command is unchanged: python -m branchwrite run job.bw --config host.json
--state /absolute/owned/run. The host manifest selects a real authenticated HTTP
endpoint, model/execution IDs and EOS IDs. BW_COW_API_KEY is an environment secret.
A private SSH local forward can expose the server loopback API to the client.
That tunnel only carries HTTP; it does not invoke model inference commands.
Do not bind an unauthenticated service publicly or copy model state into a client.

The integration audit is validation/run_remote_workload.py. It accepts host-owned
fixture, existing state, checkout, ephemeral credentials, known-host pin and
forward-only SSH key paths. The fixture selects source/task/workflow/grants/file
expectations; it supplies no model decisions. The client uses the normal CLI and
one canonical FrameKernel ledger. File tools run locally; native continuation
and COW history stay on the server.

For proof, the audit places the CLI in a Bubblewrap filesystem with no server
code, model paths, GPU devices or server checkpoint pool. Network is shared so
it can reach the local SSH forward. An import guard also rejects native/server
modules; the negative control actually attempts that forbidden import. The guard
is an audit aid, not a replacement for the filesystem boundary or a general
adversarial containment claim. Run/setup/tool results are retained independently.

A wrong key returns401 with server native work counters0. Then real Q4 H00
chooses create/read/finish and passes the unchanged protected checker. Reopening
a completed run after stopping transport returns the exact saved workflow receipt.
That is local receipt recovery, not a fresh completion or native restart test.
Server canonical branch identity is audited independently on the server. The
client never reads that store. There is no stateless inference fallback.

New client environment: Python3.14.4, Playwright1.64.0 and Pillow13.0.0. Chromium
was downloaded with the matching Playwright installer. libasound2t64 and its data
package were installed from the host package repository after a real missing
library error. No Python/venv/build outputs were written on Windows.

## Browser client on llm-49

The actual browser and generic capture CLI now work in the normal product layout:
trusted CLI on llm-49, registered browser/candidate execution inside its existing
Bubblewrap/Chromium sandboxes, inference on llm-60 via authenticated HTTP.
H01 passes model-selected read/capture/finish; the640x480 returned PNG passes the
original protected pixel check. Current selected client regressions57/57 and
browser regressions9/9 pass, no skips. See AUTONOMOUS-H01-Q4-2026-10-18.json.

Ubuntu26.04's bwrap-userns-restrict profile initially denied the capability needed
by Chromium's inner namespace. A root-owned local priority rule now selects a
restricted project worker profile only for the exact installed Python, Playwright
Node and Chromium/crash-handler paths. That profile allows sys_admin/sys_chroot
within the existing user namespace so Chromium can create its sandbox. The
original vendor policy remains; the global userns restriction is still1. A real
ordinary-system-Python control retains unpriv_bwrap and cannot write a nested UID
map. Policy paths/hashes, failed attempts and successful browser checks are backed
up privately. Reinstalling/upgrading runtime binaries requires reviewing the path
allowlist again. This is an explicit host deployment requirement, not a universal
platform or adversarial security qualification.

The extra outer CLI namespace used by the H00 audit still conflicts with nested
browser launchers on this host; its failing test is retained. H01 therefore uses
the normal CLI process with Python import/file/process audit hooks and the actual
isolated browser. Those hooks reject native-server imports, GPU file opens and
unregistered executables; all explicit negative controls pass, and the authorized
run has no audit violations. Hooks are test instrumentation, not an adversarial
OS boundary. Do not claim H00's outer-filesystem proof for H01. Server-side native
receipts and branch state are audited independently. A wrong key produces401 and
zero native forward work; closing transport before completed-run reopen proves
that reopening reads its original workflow receipt, not a new inference result.

Original browser failures are preserved. No original test or protected assertion
was edited. Neither sandbox was disabled. Original G1-G5/full VC09, native image
interpretation and Q8 remain separate and unqualified.
