# BranchWrite admin integration handoff

> Historical operational checkpoint. Read [current S3 exploration](docs/SSS-EXPLORATION.md) and CURRENT_STATE.md. Old paths, PIDs and permissions below are not current authorization.

Goal stays a usable standalone coding/admin agent, not completion of a catalogue.
Stable current product: dev44, private branch work/interactive-loop-20261020 at
10f1f2cb; installed llm-49:/home/dflanag3/spatial-artifacts/branchwrite-dev44-preview-20261020/venv/bin/branchwrite.
This worktree: llm-60:/home/dflanag3/src/branchwrite-remote-admin-20261020,
branch feat/bounded-remote-admin-20261020. Private LAN box-git only.

## Roles

BranchWrite owns typed workflows, user messages, file versions and permissions.
Context COW owns immutable model histories, controllers and optional checkpoints.
Strata performs inference. The independent harness measures actual outcomes.
RemoteTransport is a host effect boundary, not a second agent or workflow engine.
It is not yet in the model registry or ordinary CLI. Do not claim autonomous admin.

## What exists and was exercised

RM01 transport: RemoteTarget and RemoteTransport in branchwrite/remote_execution.py;
standalone bounded remote helper in remote_guest.py. 7 CPU methods and 8 real
SSH/VM checks pass. Installed candidate dev45 lives on llm-49 under
/home/dflanag3/spatial-artifacts/branchwrite-dev45-remote-boundary-20261020/venv.
Source/helper/wheel fingerprints and exact commands are in validation/remote-admin-20261020.
No server source, sampler, tolerance, registered G test or inference configuration changed.

Owned persistent VM on llm-49: /home/dflanag3/.local/share/bw-vm/admin01.
Read actual qemu.pid AND /proc cmdline before touching any process; launch.json
now describes the ISO-detached disk boot. Last observed PID2428494 is not an
ownership proof for future actions. QMP/VNC use owned Unix sockets. SSH forwards
127.0.0.1:22220; HTTP forwards127.0.0.1:18080. Both are client-host loopback only.
SSH as maint with guest-key and strict known_hosts-a432129ef6d1 from that directory.
No password is retained in the project. The supplied live ISO regenerates host
keys across boots; its separate fresh-live key file is not the installed VM pin.
Do not replace pins merely because a connection fails.

The initial disk EFI boot failed and was repaired; both are recorded. Root is
/dev/vda2 ext4, 31GiB with about26GiB free. ISO is detached. A second clean reboot
preserved the file and pinned key. No nginx or deployment has been performed yet.
Raw VM/setup/SSH evidence: llm-49:/home/dflanag3/spatial-artifacts/bw-admin-integration-20261020.
Keep private keys, VM disk and ISO out of Git and ordinary evidence archives.

## Next implementation, test-first

1. Add shared per-target leases across client runs, with durable unknown-effect
   blocking after client/SSH loss. Per-operation duplicate prevention alone does
   not make simultaneous admin mutations safe. Explicit reconciliation reads
   existing evidence; it must not rerun a pending command under a new ID.
2. Add remote_command as a typed ACT in ToolRegistry's one definition table.
   Target alias is an enum from host configuration; model never selects an IP,
   key, grant or helper. Bind target/helper/binary identities into registry and
   FrozenToolPlan. Reject missing/stale capabilities before effects. Local shell
   remains bubblewrap-isolated with no home/network. Plan/Chat get no admin grant.
3. Add bounded upload_file from an observed project file. Bind exact source bytes
   and destination scope, remote expected-old hash/absence and durable receipt.
   Protect destination from traversal/symlinks; no hidden arbitrary SCP shell.
4. Plumb explicit host target configuration through saved launches and SessionService
   into the installed CLI. Keep secrets/authority out of prompts and frozen project
   copies. Expose concise human progress and actual command status. Preserve source
   bound old clients/workflows rather than silently accepting a changed registry.
5. Reconcile a known remote host receipt into the original Kernel frame after a
   lost local return, then /continue once. Missing evidence remains unknown. Admin
   services deliberately persist under the VM's owned scope; don't claim that an
   exited SSH process means the web service stopped.
6. Run novice end to end on Q4: make a simple site, install nginx on admin01,
   upload/publish, independent HTTP/browser checks, alter site by steering, redeploy,
   switch coding branches, and recover a stopped session. Commands must actually
   come from the model via CLI/HTTP/COW, not operator replacement. Preserve failures
   and add generalizable model failures to the private LoRA candidate collection.

Cumulative G1-G5 stays unqualified. This milestone is no reason to restart chat,
push publicly, or claim arbitrary fleet administration. The ordinary COW service
on llm-60:8099 was not changed by this work. Windows remains SSH orchestration only.


## RM02 ownership checkpoint (supersedes step1 above for one client host)

RemoteTransport now uses TargetOwnership from remote_ownership.py.16CPU checks,
8repeatedrealSSHchecks and2actual multi-process/VM checks pass. A credential/name/
user/timeout change cannot bypass a shared endpoint resource key. OS flock avoids
concurrent commands; durable reservations survive process death. Original known
receipts recover after a crash between receipt publication and lease completion.
Unknown work remains blocked. No force-clear or automatic unknown-command resend.
Installed dev46 onllm-49 is a boundary candidate, not the ordinary CLI admin UI.
Source/wheel/raw fingerprints are in validation/remote-admin-20261020/ownership/.

Operator state preparation: the existing llm-49 app container had0775permissions.
It was tightened to0755; the private remote-targets leaf is0700. On a new host,
prepare the owned app container without group/other write access, then create
its remote-targets directory at0700. Do not loosen checks to fit an unsafe parent.
No inference server source or unrelated directory permissions were changed.

Remaining coordination scope: different client HOSTS or multiple forwarded
addresses to one physical machine are not qualified. First exposed admin
capability must stay bound to its configured client owner/unique VM endpoint.
Cross-host target coordination remains a separate obligation.

Next implementation is tool/CLI integration. Existing ProjectChecksPolicy counts
only local run_check receipts. Add actual named remote-check evidence with
relevant target freshness/invalidation; do not use a dummy local check merely to
make an administrative workflow finish. Preserve the separate meanings of
command exit, useful task acceptance and independent HTTP/browser verification.
Expose remote_command/run_remote_check from the one tool-definition table under
explicit host target grants; keep Plan/Chat read-only. File transfer needs exact
local bytes and guarded remote publication, not model recopying long source text.
A known retained remote receipt should settle the ORIGINAL waiting Kernel frame
without rerunning the command. These product integrations remain unimplemented.

## Fresh dev48 active browser steering (2026-10-20)

The installed dev48 client on llm-49 passed a fresh real-Q4 steering run against
llm-60:8099. A new formatting instruction was typed during the pending original
request. Canonical audit records kind=steer, interrupted original turn and finished
new turn. Desktop/mobile isolated Chromium checked computed bold names, italic
and underlined verbs, the greeting click, no overflow and no runtime errors.
Evidence: validation/remote-admin-20261020/active-browser-dev48/.
Whole run358.834s; safe boundary65.458s after steering, using the original service's
whole-step fallback. This does not qualify immediate/consumed-boundary cancellation.

The preceding autonomous admin pilot finished in495.561s. Independent HTTP and
systemd inspection confirmed the welcome service responds200 and is active/enabled.
It used Python's static HTTP server after discovering our remote helper's global
RLIMIT_FSIZE breaks apt. That helper bug remains open; package installation is not
claimed to work. No reboot was performed. Raw admin evidence remains on llm-49:
/home/dflanag3/spatial-artifacts/bw-autonomous-admin-q4-20261020/.

Dev48 implementation changes remain uncommitted beyond bb533994; the current
evidence-only checkpoint does not mislabel their status. The private browser
archive preserves the installed wheel, source snapshot/diff and fingerprints.
Next: fix bounded output capture without limiting legitimate command file writes;
rerun focused real SSH cases, then rerun package installation.

## Integrated dev49 remote administration checkpoint

This checkpoint includes the previously pending typed remote tools, explicit
operator capabilities, CLI launch plumbing, original-receipt reconciliation and
remote-aware final verification. The global file-size limiter is replaced with
bounded pipe capture. Current439-test suite and11 installed VM workflow cases
passed; actual apt/nginx installation,2MiB writes and independent HTTP passed.
See validation/remote-admin-20261020/output-capture/README.md for exact scope.

The original Q4 server on llm-60:8099 remains running, ordinary chat remains off.
The owned admin01 VM on llm-49 now serves nginx, not the preceding temporary Python
welcome service. No VM reboot or privileged process cancellation was qualified.
Next largest product gap: hash-bound local-file upload and guarded remote
publication, then an autonomous coding-to-deployment-to-edit journey with steering.
Also expose actual failed verification reasons in model feedback, improve live
tool/target progress, and qualify repeat steering on the newer pause service.

## Exact upload integration, dev51

Added upload_file(target,path) through the existing typed plan/Kernel/SSH receipt
path.450 combined regressions and3 installed exact-upload/recovery cases passed,
plus11 remote workflow regressions. Initial dev50 failure on the VM's0775 shared
parent is retained; dev51 has a dedicated target-home staging directory.
See docs/manual/10_REMOTE_ADMIN.md and validation/remote-admin-20261020/upload/.
Autonomous Q4 deployment trial is live on llm-49, campaign2434505/client2434508,
at /home/dflanag3/spatial-artifacts/bw-code-deploy-q4-dev51-20261020/. Revalidate
process identities before acting. Do not restart solely because observation times
out. Independent deployment/browser acceptance remains pending.

## Interactive sampler selection, dev53

New session --sampler min-p/dry-min-p options are implemented, preserving greedy
default and exact saved launches on recovery.454 combined regressions and an
installed no-inference PTY check passed. No GPU Min-P result is claimed yet.
The dev51 autonomous greedy code/deploy pilot is still running on llm-49; last
verified controller2434505 and client2434508. It created and uploaded index.html
but spent substantial time repeating an irrelevant thought checklist. Its20min
observer deadline is recorded in campaign.py; a timeout is not a numerical fail.
Revalidate handles and original receipts; never restart an unknown operation.
The compact repetition candidate and generator brief are on llm-60 under the
LoRA collection and privately backed up. Next: observe terminal outcome, perform
independent HTTP/hash/browser acceptance if it finishes, then test a supported
sampler alternative if required. Avoid source edits to the installed in-flight
candidate. The repetition/latency and unexposed verification reasons are useful
self-monitoring work; neither is solved by the new manual option alone.

## Autonomous coding/deployment outcome and current follow-up

Dev51 greedy run created, checked, uploaded and deployed the dog website, with
HTTP exact-byte and desktop/mobile browser PASS. Initial20min observation timed
out before final workflow completion. Graceful stop retained all work; a separate
client /continue finished in2.333s with no new native requests or remote receipts.
Keep the initial timeout, successful resume and site acceptance separate. Evidence
is validation/remote-admin-20261020/autonomous-code-deploy/.

The run generated19969 tokens and repeated an irrelevant thinking checklist;
latency remains an actual usability problem. Final answer also suggested a guest
NAT address not established reachable from the user client. Record this scope
problem; add host-provided preview/routing facts instead of guessing a usable URL.

A new Min-P edit/deploy follow-up is running on the SAME saved session, using the
installed dev53 client. Controller2437388 (revalidate) on llm-49; artifact
/home/dflanag3/spatial-artifacts/bw-followup-minp-dev53-20261020/. It asks for bold
Milo/Luna, italic+underlined plays/runs, preserving button and updating admin01.
No DRY yet. It has its own20min observation limit and drains the PTY during stop.
Independent browser formatting checks are required before PASS. It is not a
sampler-only comparison because task and starting state differ. The original
Q4 inference service stays running; ordinary chat remains off. Next: audit that
follow-up, self-monitor repetitive thinking/verification failures, and improve
actual tool/target progress in the interactive display.

## Recorded-verdict feedback, dev54

Default new coding programs now VERIFY before tool-feedback. The optional typed
evidence binding must refer to the actual visible VERIFY return for the exact
tool operation. Protected detail fields are excluded.460 regressions and2 actual
installed CLI/shell cases passed; no GPU auto-repair test for this new version yet.
Source/evidence: validation/remote-admin-20261020/verification-feedback/.
The Min-P pilot used installed dev53 and is separate evidence.

## Min-P follow-up completed; next speed target

The dev53 follow-up finished unassisted in746.551s. Exact two-sentence diff,
HTTP equality and desktop/mobile computed styles/button/nooverflow/noJS passed.
It reused50684 starting cells:9 native requests evaluated16780 new cells exactly
(12710prefill+4070generation), with no observed old-prefix replay. All canonical
object IDs were hash-checked and witnesses backed up. See minp-followup evidence.
Both old pilot processes are terminal; ordinary chat remains off; Q4 COW8099 stays
running. No GPU job is currently scheduled by this controller. Recheck before use.

Latency remains unacceptable. Read-only CPU microprobe took0.017s/0.128s/0.529s
for20 synthetic metadata append/validation steps at1K/8K/32K respectively. cProfile
identifies input_binding, canonical_inputs/token validation, InputHistory creation,
JSON parsing and prefix construction. These are actual server functions; this is
not a whole-request GPU profile and does not prove exclusive causation. Native
per-token counters also show substantially less compute time than generation wall.

Next high-value server work: isolate a COW worktree; keep canonical serialized
InputHistory bytes and reference binding equations unchanged; test derived immutable
projection/append caches that avoid parsing and revalidating the whole prefix on
every token. Preserve complete validation on import/publication, exact native
receipt checks, tamper/subclass rejection and bounded memory. Do not disable hash
checks or alter tolerances. Compare derived bindings with the unchanged reference
for text, images and boundary cases; measure CPU first, then same-profile Q4 exact
GPU continuation in a separate one-job campaign. Only promote a measured winner.
Current serving COW source is4b1f8fda at context-cow-client-setup-20261020. Latest
consumed-pause source780e824a includes128-byte names/pause; real.py and backend
input-path code otherwise closely match. The live text snapshots are schema2
InputHistory, so do not assume the tuple-only path is the bottleneck.

Other open product work: actual dev54 model self-repair validation, useful tool
and target progress, correct client/guest preview URL facts, and automatic handling
of thinking stalls. Do not claim the new manual sampler option solves those.

## 2026-10-20: autonomous repair and progress notices

Dev54 installed CLI completed one real-Q4 Python repair in77.362s with no
intervention. Existing3tests unchanged;100independent seeded inputs passed.
Actual failed run_shell and successful run_check receipts/feedback were audited.
See validation/remote-admin-20261020/autonomous-repair/.
Dev55 adds fixed tool-specific progress labels;471CPU/PTY/HTTP regressions
passed without failures/skips. Installed client on llm-49 under
/home/dflanag3/spatial-artifacts/branchwrite-dev55-tool-progress-20261020/.
New-launch candidate only: old admitted workflows keep their original build.
Remaining priorities: end-to-end steer latency, robust broader coding/admin
workflows and independent acceptance; current metadata optimizations are not
yet GPU-qualified or deployed. No broad G1-G5 qualification claimed.

## 2026-10-20 CAD task family: foundation checkpoint

Authoritative source moved to llm-49:/home/dflanag3/src/branchwrite-cad-20261020
on feat/build123d-task-family-20261020, based on5ac8a7fb. Read the full user CAD
requirements and acceptance/cad/task-family-plan.json. This is an additional
domain inside BW, not a new orchestration service or another history store.
18real OpenCascade/VTK tests pass, no skips. CAD00 only: no model authored a
part yet and no CAD tool is exposed in the normal CLI. Do not call it complete.

Runtime: /home/dflanag3/spatial-artifacts/bw-build123d-20261020/cadvenv/bin/python
Python3.12.15, build123d0.13.0, OCP8.0.1.1.0, VTK9.5.2, prompt_toolkit3.0.52.
OSMesa libraries were extracted locally, not installed globally. Required worker
environment LD_LIBRARY_PATH points to .../osmesa-runtime/root/usr/lib/x86_64-linux-gnu;
LIBGL_ALWAYS_SOFTWARE=1. VTK EGL probe crashed; OSMesa initially lacked its
library. Private libosmesa6+libllvm20 resolved this; actual llvmpipe CPU rendering
works. The first Matplotlib renderer was visually rejected, then replaced.
Frozen tolerances:1e-6mm length,1e-5mm^3 volume, based on independent STEP
round trips at97/100/110mm (max analytic volume error8.74e-11mm^3). Never widen
for bad model output. Same-bbox/same-volume corruption is rejected via direct
OCCT reference CSG. A new adversarial case exposed loose faces/edges passing
volume checks; single-solid acceptance now requires all faces/edges/vertices to
belong to the solid. No model/training failure was claimed for these tool bugs.

Next implement bounded workers first. Candidate Python must execute in a fresh
bwrap filesystem/PID/network namespace with only captured project inputs and
pinned CAD runtime. Do not run model Python on host or give it the protected
checker package. Separate independently controlled parse/check/render from the
candidate process. Bound CPU/wall/RAM/tmpfs/output bytes, retire descendants,
validate STEP from captured bytes and preserve original operation identities.
Use existing Executor._capture and namespace retirement where applicable; verify
bwrap info-fd semantics locally rather than assuming candidate-supplied witness
JSON is trusted. Then add typed CAD tools/config to existing registry/Interpreter,
feedback with actual PNG via existing image-feedback, finish policy requiring
current source/requirements/export checks, and ordinary directory CLI admission.
Keep one existing ledger and COW branch authority. Bump new-launch package version
when integrating; old dev55 sessions retain their installed source.

Model milestone: Q4 ordinary Python construction, measured/rendered revision,
then110mm change with fixed76x36 hole pattern;90mm must explain97mm minimum.
Notch dimensions chosen explicitly for pilot:6mm depth x10mm width, centeredY,
positiveX through-thickness. Closed pilot spec permits no extra features. Document
these demonstration choices. Finalize export/reopen, branch/filesystem isolation,
old-evidence rejection and budget comparisons before claiming the complete loop.
Future assemblies/dynamics are deferred. Metadata/pause candidate is prepared on
llm-60 but unstarted; original Q4 service8099 remains unchanged and chat OFF.


## 2026-10-20 CAD and Blender addition

See SPATIAL-CREATION-GUIDE.md for actual boundaries, setup and commands. Real Q4 authored/repaired a plate and closed its original workflow verified after three CAD builds. Forty-nine CAD/domain tests plus five Blender/MCP tests passed in their declared environments. The 471 existing CPU/PTY/HTTP tests passed the first CAD integration revision; rerun is required for the latest carrier/Blender changes. Carrier model and autonomous Blender model runs are next; fixtures are not their substitutes. Runtime-cache hard links, missing client Pillow, a disabled image preparer and an incorrect completion-policy tool card were found and addressed; all original failure evidence is retained. Native engine and execution/model profiles remain unchanged. Ordinary chat is off. No public push.


## dev58: faithful Blender framing; documents now take priority

Seven real Blender/MCP tests and seven CLI/context tests passed for v2 controlled framing across every rendered frame and valid world-less scenes. Source/profile changed explicitly; old installed dev57 stays unchanged. See validation/blender-framing-20261020. Broader combined regressions remain pending. Carrier admission is held at owner request; prioritize built-in ReportLab PDF creation, actual page rendering, image feedback and revision, with dependencies included at initial installation. Original dev57 Blender client2455370 continues; revalidate PID and receipts, never resend unknown operations. Its observer timeout is not a numerical failure.
