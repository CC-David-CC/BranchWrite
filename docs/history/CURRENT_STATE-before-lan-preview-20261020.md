# Current release correction

See [PUBLIC_PREVIEW.md](PUBLIC_PREVIEW.md) for the latest verified state. Dev65 is installed separately; the candidate server trial finished and restored8099. The older notes below preserve development history and contain superseded live/pending labels.

# BranchWrite current state

Updated2026-10-20. Private LAN development; Windows coordinates SSH only.
Historical checkpoints are archived in docs/history/CURRENT_STATE-through-20261020.md.
This page is the current starting point; older dev paths in historical notes are
retained evidence, not the recommended installation.

## What the pieces do

- BranchWrite CLI: the directory-based human interface, queue/steering/modes,
  saved file versions, workflow ledger, tools and recovery of original effects.
- Context COW: the authenticated HTTP inference service, canonical immutable model
  history/controllers, movable branch references and optional RAM/disk checkpoints.
- Strata: native model execution. Model state is not a .bw workflow file.
- Acceptance harness: independent OS/browser/geometry/page checks and retained
  measurements. It launches actual CLI commands; it does not supply model answers.

One BW interpreter and ledger remain workflow authority. Git file versions pair
with COW references. Runtime artifacts are immutable derived outputs. No second
conversation history or hidden stateless replay path was introduced.

## Current locations

- Source/client development: llm-49:/home/dflanag3/src/branchwrite-documents-20261020
- New-launch installed dev63: llm-49:/home/dflanag3/spatial-artifacts/bw-cli-workflows-dev63-20261020/venv/bin/branchwrite
- Prompts: examples/prompts/ (one ordinary .txt request per workflow).
- Exact prompt outcomes: examples/prompts/results.json. Pending is not a pass.
- Private repository: box-git:/srv/data/git/BranchWrite.git
- Feature branch: feat/builtin-pdf-workflow-20261020
- Temporary controlled Q4 trial: llm-60, http://10.0.7.68:18099, source780e824a.
  The original8099 API is stopped pending explicit client settlement and restoration.
  Lifecycle: /home/dflanag3/spatial-artifacts/bw-server-integration-20261020-v1/.
  Ordinary chat remains off; this is not a permanent profile migration.
- Original serving source: llm-60:/home/dflanag3/src/context-cow-client-setup-20261020,
  revision4b1f8fda22c493a6772896e7e008730f3c767868.

Keep admitted older client installations for their exact saved workflows.
Cross-version migration is not silently assumed. Ordinary chat stays OFF. Q8 is
still deferred for this development campaign. Nothing here authorizes GitHub or
Strata publication.

## Demonstrated and implemented

- Interactive Work/Plan/Chat/Aside; coalesced queued followups, active steering,
  history search, edit/explore/switch, client reopen/continue and guarded files.
- Live Q4 edit/explore/steering and stop/reopen demonstrations on earlier named
  installs. Fast consumed-token pause passed a candidate-server trial; the restored
  current server has the older whole-step fallback.
- Authorized SSH administration, actual nginx installation, exact uploads and
  bounded autonomous code/deploy/repair demonstrations.
- Installed dev59 PDF authoring: exact pdf.txt, actual two-page images in settled
  native requests, current checks, visual audit, zero operator source edits.
  493.635seconds. Source and resulting pages/PDF are in validation/pdf-live-q4-20261020/.
- Installed dev61 writing: exact writing.txt,165 words, requested title/example,
  actual read/check, unchanged prior PDF and unchanged source project.274.522seconds.
- Q4 CAD plate and Blender scene/animation authorship are prior-version bounded
  passes.53 current CAD and7 Blender regressions passed after shared runtime fixes.
- Built-in ReportLab/pypdf/PDFium dependencies; isolated build_pdf/render_pdf,
  current-page canonical evidence, exact publication and immutable exports.
- New dev62 interactive CAD/Blender host configurations and saved output display:
  same session worker/ledger, read-only exclusion, original-launch recovery.
- New dev63 /preview supports a selected saved PDF or literal .txt in addition
  to websites. Other documents are not exposed in website resource bundles.

## Executed regression scope

- Dev62 codeb4b039c5:506 combined CPU/PTY/HTTP/PDF/session methods PASS,
  zero failures/errors/skips,127.423seconds, unchanged source fingerprints.
- Dev63 document-preview changes:47 focused checks PASS, including real
  loopback/Git transport, literal Unicode, explicit PDF/text selection and
  existing session/terminal cases. Full dev63 aggregate:510PASS,0failures/errors/
  skips,126.819seconds with unchanged source fingerprints.
- Actual native inference, domain model authorship and fixture-driven plumbing
  are distinct evidence scopes. A green count is not semantic task certification.
- Original COW G0 has51/51 evidence. Cumulative G1-G5 remains unqualified.
  Cross-arrangement equivalence remains outside the accepted prototype contract.

## Active work and next requirements

The exact code.txt dev62 CLI job completed in631.823seconds and passed independent
desktop/phone browser checks plus screenshot review. Prior PDF/text bytes were
preserved. See validation/cli-code-q4-20261020/. This latency is an open usability
problem; the measured5196 consumed output tokens include thinking and proposals.
Preserve IDs across lost replies. An observation timeout is not proof of exit
and is not permission to resend.

Next acceptance work:
1. Controlled caching/pause candidate is running with its own profile/store.
   Installed dev63 interactive CAD passed; Blender next-turn validation is live.
   Still measure comparable whole-CLI work and settle/restore the owned service.
2. A later-request PDF revision and restart using the actual saved computation.
3. Installed interactive CAD passed: actual geometry/views and saved export paths,
   model self-repaired Location misuse,241.368s. Blender/reopen validation ongoing.
4. Existing authorized admin-deploy prompt qualification on the current CLI.
5. A cohesive initial-install/manual path and broader unfamiliar code/admin jobs.

Important remaining product gaps:
- General mixed-domain acceptance and model-directed browser observation are not
  finished. The bounded Blender MCP adapter is not generic arbitrary MCP support.
- Automatic thinking-stall diagnosis/fallback is unfinished; older runs repeated
  irrelevant thoughts for many minutes. Passing chosen checks can miss requirements.
- Newest CPU metadata optimization is not deployed/GPU-qualified and has a retained
  128K CPU regression. No whole-agent speedup is inferred from microbenchmarks.
- Broader controller/image combinations, cross-client remote coordination, upgrade
  handling, crash/pressure/matrix/sanitizer/soak campaigns remain separate work.
- Experiment notebooks, numerical-controller experiments and measurement-versus-
  repair policy are future extensions, not existing agent capabilities.

The goal remains a standalone coding/admin agent using shared computational
histories with independent continuations. These specimen tasks do not redefine
completion around a small successful demo.

## Manual starting points

- docs/manual/09_INTERACTIVE_SESSION.md: responsive terminal and branch controls.
- docs/manual/10_REMOTE_ADMIN.md: host-granted remote execution and exact uploads.
- docs/manual/11_PDF_DOCUMENTS.md: installed PDF creation and actual page review.
- SPATIAL-CREATION-GUIDE.md: CAD/bd_warehouse/Blender setup and measured boundaries.
- examples/prompts/README.md: simple requests, exact status and one-shot CLI usage.

## Latest integration observation

The511-case aggregate passed with no failures/errors/skips in128.794s. A live
Blender turn then correctly refused runtime mutation caused by our concurrent
--help probe writing Python caches. Its original request is retained and
/continue is reconciling it after exact cache-layout recovery. New dev64 source
disables late bytecode writes at package bootstrap;11 focused tests pass.
Fresh installed checks and live Blender completion remain pending.

Latest completed observations: the original Blender operation resumed with
/continue and passed actual scene/image/45-degree/24-frame checks. Actual
/switch1 then /switch2 restored files/context/exports without model calls. New
dev64 is installed separately; its actual doctor/default-PDF/help-integrity
checks passed on Python3.12.15 and a dependency-complete offline install passed
on distro Python3.14.4.12 focused bootstrap/domain/runtime tests pass. The
current dev64 admin01 CLI trial remains live; original8099 restoration waits
for its owned client settlement.
