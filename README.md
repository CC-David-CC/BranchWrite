# BranchWrite (BW)

[Drive one learning round from a person or agent](docs/BOUNDED-LEARNING-DRIVER.md):
the bounded client follows PCC's advertised actions, waits for original jobs,
and stops for verified lesson selection or operator review. S³'s real tiny-model
CPU integration qualifies the driver separately from model capability scores.

[Terminal workflow failures](docs/TERMINAL-WORKFLOW-FAILURES.md) can now be archived locally for assessment without inventing an artifact grade or approving a lesson.

[Owner completion recovery](docs/OWNER-COMPLETION-RECOVERY.md) lets a person or owner agent inspect original evidence, explicitly adopt completed metadata, and return to the same learning round without starting another training job. [PCC's recovery contract](https://github.com/CC-David-CC/Private_Context_COW/blob/4a536ab6e26a7d97f200452479a201b414ce55fb/docs/NATIVE-COMPLETION-RECOVERY.md) explains the engine checks. A tiny synthetic model has passed one native CPU update/reload and deliberate stop/restart recovery through BW. This qualifies the mechanics only; MiniCPM/Wen model quality remains untested. See PCC's [sanitized qualification receipt](https://github.com/CC-David-CC/Private_Context_COW/blob/feat/native-completion-recovery-20261026-bo/validation/native-completion-recovery-20261026/README.md).

[The durable learning loop: ELI5, master's, PhD, and applied guide](https://github.com/CC-David-CC/sss/blob/main/docs/LEARNING-MACHINERY.md) explains ownership, recovery, paired learning/forgetting, expanding assessments, commands, and qualification limits. The [current learning-loop status](https://github.com/CC-David-CC/sss/blob/main/docs/LEARNING-LOOP-STATUS.md) records recent work and remaining gaps. The new machinery checks are separate from the fixed 68-update comparison.


[Shell compatibility and check-quality findings](docs/POSIX-SHELL-NAMESPACE.md):
ordinary `/bin/sh` paths now work inside the restricted namespace. This fixes
an environment defect; MiniCPM’s remaining workflow failure is still open.

S3 can now evaluate through the [same COW request code BW uses](docs/SHARED-EVALUATION.md).
PCC reports the [4.8x small forward-work probe result](https://github.com/CC-David-CC/Private_Context_COW/tree/feat/native-learning-curves-20261024#48x-faster-on-small-forward-work-probes),
with shared-A100 timing limits. S3 records the detailed test method and outcomes.

[What we are discovering](https://github.com/CC-David-CC/sss/blob/feat/foundations-20261023/docs/FINDINGS.md): readable findings about context
cost, tool differences, training, forgetting and practical next steps.

[Compare BW, OpenCode, Codex and pi](https://github.com/CC-David-CC/sss/blob/feat/foundations-20261023/docs/HARNESS-COMPARISON.md)
with S³'s four-condition study contract. The offline comparison machinery is
tested; live adapters and cross-harness results remain to be qualified. BW
retains its own workflow and tool authority. The
[real-client CPU guide](https://github.com/CC-David-CC/sss/blob/feat/foundations-20261023/docs/REAL-HARNESS-SETUP.md)
now verifies file/tool loops in pinned Codex/OpenCode/pi clients with mock replies.
Actual Wen comparisons remain pending.
[Joint learning and harness hill-climbing](https://github.com/CC-David-CC/sss/blob/feat/foundations-20261023/docs/JOINT-LEARNING-LOOP.md)
keeps separate per-harness improvements and mixed-review training measurable;
the full live coupled cycle remains to be established.
Development checkpoint: [foundations and workflow validation](validation/foundations-20261023/README.md). Live-model qualification remains pending.


[Explore the skill graph and existing Blender/CAD/PDF/web/admin workflows](docs/SSS-EXPLORATION.md). The operator guide separates working reference machinery from model qualifications.

**Describe what you want to make or change. BW works on the files, runs checks,
and keeps saved versions so you can continue or try another direction.**

> Make a one-page website for my landscaping business. Include our services,
> phone number and a contact section. Make it easy to read on a phone.

Then:

> Make the lettering bigger and change the green to blue. Keep the phone number
> at the top.

BW is the app you talk to. Its current documented interface is a text window on
Linux. It connects to an AI server you choose. A single suitable computer can run
both BW and that server; a separate laptop is optional.

## How BW, PCC and Strata fit together

| Part | What it does | Why it matters |
| --- | --- | --- |
| **BranchWrite (BW), this repository** | Takes your request, reads and changes permitted project files, runs tools and checks, and keeps task progress and file versions. | Turns model answers into project work you can inspect and continue. |
| **Private Context COW (PCC), the server** | Contains both a modified Strata core and the COW context-management layer. | Runs the AI and keeps reusable starting points for related work. |
| **Modified Strata core, inside PCC** | Runs the supported model on the graphics card and system memory. | Does the computation that produces the model's answers. |
| **COW layer, inside PCC** | Keeps model context, independent continuations and reusable saved computation. | Lets related work share a beginning without mixing up the different paths. |

**[Private Context COW (PCC)](https://github.com/CC-David-CC/Private_Context_COW)
is one combined server project: modified Strata core + COW layer.**
Use PCC for the whole project and COW for its context layer. The AI model is the
downloaded set of learned weights; it is separate from these programs.

PCC builds on [Niko's Strata](https://github.com/Niko1221/Strata).
**Niko and the upstream Strata contributors are welcome to review the PCC changes
and take useful improvements back into Strata.**

## Start with the computer you have

**[Start here: one computer or a remote server](docs/START-HERE.md).**
This guide covers the R730 with two P4s, RX 7900 XTX, RTX 4090,
RTX PRO 6000 Blackwell and shared/rented A100 setups. It distinguishes working
routes, separate previews and hardware paths that still need integration.

On one suitable Linux computer, PCC runs in the background while BW works on
your local project. With a remote server, BW keeps your project on the client
and sends the content needed for the task to PCC. Use a server you trust.

For the existing large-model installation steps, see the
[desktop/server walkthrough](docs/TWO-COMPUTER-SETUP.md) or
[client-only guide](docs/LINUX-QUICKSTART.md). Their default model is about 111 GB.
A smaller dense-model path has a separate setup; do not assume you must download
the largest model to try every hardware route.

### Which model can do the work?

[PCC's model guide](https://github.com/CC-David-CC/Private_Context_COW/blob/main/docs/MODELS-AND-RESULTS.md)
offers the 111.33 GB Flash Q4 download beside Wen 1.1 (16.24 GB) and original
Wen 1 (15.94 GB), with their separate installation routes. Download size and
tokens per second do not tell you whether a model can repair your project.

**[Skills³ (S³): Skills, Scoring, Stability](https://github.com/CC-David-CC/sss)**
is the independent skill tree and testing project BW imports. Its reasoning
curriculum is **strengthened by ideas incorporated from
[LearnHarness](https://github.com/amosblomqvist/learnharness)**;
[S³ owns the new exercises and proof checks](https://github.com/CC-David-CC/sss/blob/feat/foundations-20261023/docs/REASONING-CURRICULUM.md).
BW uses them through its existing optional S³ import. Its foundations
are read, write, edit and verified completion, leading toward tool use, coding
and Linux administration. [The full guide](https://github.com/CC-David-CC/sss/blob/main/docs/USER-GUIDE.md)
explains what is implemented and what remains unmeasured.

The [canonical model report](https://github.com/CC-David-CC/sss/blob/main/docs/MODEL-COMPARISON.md)
keeps historical Flash Q4/Q8 serving measurements separate from the paired
Wen 1 / 1.1 trial on the same current tool tests. Those first model tests use
isolated mock files, not actual Linux administration or the BW task runtime.
BW keeps its own real tool execution and acceptance checks.

The first paired A100 trial finished at **Wen 1: 5/9; Wen 1.1: 4/9**, with no
backend errors. The extra 1.1 failure was correct read content without the
required completion action; other shared failures need parser/model attribution.
This small stack test does not establish broad model superiority or real BW
administration competence. The linked S³ report gives each case and its limits.

Checked corrections can become single lessons or explicit training batches
through an owner-enabled PCC service. Optional S³ mixed replay checks the other
active skills while a LoRA hat is made. The completed small mixed-practice pilot
preserved earlier correct answers but did not improve its held-out score; no
hat qualified or automatically replaced the running model. Useful learning and
broad admin competence still need evidence.

### Install the current main client

On 64-bit Intel/AMD Linux, install the required tools:

```sh
sudo apt update
sudo apt install -y curl git ca-certificates bubblewrap util-linux
```

As your normal user, download the installer and explicitly select current source:

```sh
curl -fsSL https://raw.githubusercontent.com/CC-David-CC/BranchWrite/main/install.sh -o "$HOME/branchwrite-install.sh"
BW_REF=main sh "$HOME/branchwrite-install.sh"
```

Without `BW_REF=main`, the installer selects its older pinned preview release.
Keep old runtime versions for saved work that needs them. Installation of this
exact new source has not been rerun as part of this documentation update.

After PCC is running, start BW in your project folder:

```sh
mkdir -p ~/my-first-website
cd ~/my-first-website
~/.local/bin/bw
```

Enter the server address and API key when prompted. The key is the service's
password and stays in memory unless you explicitly choose to save it.
On the same computer, use the configured local address, usually
`http://127.0.0.1:8099`. With a remote server, use its configured LAN or forwarded
address. [The guide explains both](docs/START-HERE.md).

Ask for a simple one-file website. When BW finishes, type `/preview` and open
the printed link. Ask for a change and keep working in the same session.

## Try another direction and come back

Suppose your first saved Work request made a website:

- **Follow up normally:** ask for a change and continue along the selected path.
- **Try an alternative:** `/explore 1 Make the site more playful.` uses context
  after saved turn 1 and your current files in a separate folder. The selected
  project folder stays unchanged during that trial.
- **Replace an earlier request:** `/edit 1 Make a formal landscaping website.`
  starts from the context and file version before Work request 1.
- **Return to a saved version:** `/switch 1` selects saved turn 1 and restores
  its matching files. Conflicting manual edits stop restoration.
- **Find a request:** `/history website` searches saved requests and shows turn numbers.

Here, `1` is an example saved turn number. Edit and Explore currently target saved
Work requests. The [interactive guide](docs/manual/09_INTERACTIVE_SESSION.md)
explains the exact controls.

A **branch** is another direction from a recorded starting point. BW saves the
project files; COW saves the corresponding model context. When compatible saved
computation is available, the server can reuse the shared beginning. If that
optional checkpoint has expired, it may need to rebuild the computation from
retained history.

A separately selected coding workflow can also try **two checked approaches**
in isolated project copies and select a passing candidate by an explicit rule.
[See the two-approach controls](docs/PARALLEL-EXPLORATION.md).
Review the result yourself: passing selected checks does not prove every part
of your request has been satisfied.

## Keep talking while it works

| Control | What happens |
| --- | --- |
| **Enter** | Send a request or steer active work at its next safe boundary. |
| **Tab** | Queue a follow-up note for the next turn. |
| **Esc** | Ask it to stop at a safe boundary. |
| **Ctrl+R** | Search what you typed before. |
| **/plan** | Inspect and discuss without editing files. |
| **/work** | Return to making changes. |
| **/aside your question** | Ask a side question without moving the main model path. |
| **/preview** | Open the selected saved website. |
| **/continue** | Continue the saved paused or unsettled workflow. |
| **/exit** | Settle work and leave. Reopen BW in the same folder to return. |

Wait for the stop/settlement message. Closing BW does not stop PCC.
Reopening unfinished work uses its saved operation identity; it should not
be submitted again as an unrelated new task after an uncertain reply.

## Teach a checked correction

The skill tree, evaluation suites and regression-aware curriculum belong to
**[Skills³ (S³): Skills, Scoring, Stability](https://github.com/CC-David-CC/sss)**.
BW imports that optional package; its task ledger, tools and grants stay here.
`branchwrite skills` or `/skills` displays the broad map with unmeasured abilities
labelled explicitly. `branchwrite lesson skills` inspects a server's active
training tree. Linux administration is a major branch of the map; the current
native learning starter covers five arithmetic skills, not a qualified admin agent.

With a PCC server that has opted in to native training, BW can write a short
lesson after a failed check and verified correction. Train one example now or
queue lessons for a later batch. Failures and repairs can be in the same task.

```text
/lesson create --prompt "def double(n): return" --completion " 2*n" --operation-id double-lesson --train-now
```

Use `--queue` for later, `/lessons` to inspect the queue, `/train --pending
--operation-id batch-1 --batch-size 8` for a batch, and `/training batch-1` for
status. The standard `branchwrite lesson` commands also work outside a session.
BW binds the lesson to existing check records; PCC performs native LoRA or direct
full-weight training without PyTorch. The original model and live contexts keep
their pinned identities; each update produces a separate candidate.

With an owner-configured S³ guard, tag a lesson with `--skill SKILL_ID` and add
`--skill-guard --batch-size 8 --steps 16` to request bounded mixed practice and
whole-tree regression checks. This is explicit: ordinary single-example jobs do
not silently acquire a repair-loop budget. S³'s independent tests and curriculum
are documented in [its integration guide](https://github.com/CC-David-CC/sss/blob/main/docs/INTEGRATION.md).

The CPU test proves this wiring with real updates on a tiny generated model.
Useful learning, preservation and large-model/hardware qualification need their
own measurements. Training is disabled on ordinary servers, and a candidate is
not automatically promoted. [Read the workflow, settings and limits](docs/LEARNING-LOOP.md).

The optional native learning path now lets BW select registered AdamW/Muon
policies and preserve private named standalone GGUF checkpoints through PCC.
Real tiny CPU jobs pass through BW's CLI. The separate MiniCPM development
campaign has improved from 59 to 482 to 507 correct answers out of 864 while
tracking regressions; that does not establish a fix to BW's shell tasks.
[Commands and qualification limits](docs/LEARNING-LOOP.md#registered-native-optimizer-jobs-and-private-model-checkpoints).


The first 1,000-variation Wen study learned its selection pattern (2/48 to
48/48), but lost five of sixteen unrelated checks and reached only 3/16 on
differently worded blind cases. No candidate qualified. This preview demonstrates
the learning controls, without establishing a reliably improving everyday model.

## Does BW benefit from the DeepInfra-inspired work?

**Yes. The new inventory, placement and checkpoint-transfer features live in
PCC's COW layer. BW benefits through its normal server requests.**

An operator can enable PCC to find reusable computation, consider restore and
compute costs when choosing a local worker, recover compatible checkpoints from
configured peers, or assign input preparation and continuation to different GPUs.
The optional fastokens adapter handles measured long text pieces more quickly.

BW does not need a second cache manager or a new workflow for each server setting.
The current integrated client checks the server's advertised capabilities and
model/execution identities when connecting and admitting unfinished work.
Completed results can be reopened offline from BW's saved records.

These features are optional and off by default. A single-GPU setup can use
ordinary context reuse; cache peers need another configured location, and
separate GPU roles need suitable independent workers. They do not make all
hardware interchangeable or establish a general speedup.

[Read the PCC feature overview](https://github.com/CC-David-CC/Private_Context_COW#what-the-newer-cache-features-add),
[configuration and contributor credits](https://github.com/CC-David-CC/Private_Context_COW/blob/main/docs/CACHE-FABRIC.md),
and [BW's integration details](docs/STACK-INTEGRATION.md).

## Research model, real mechanics, unfinished validation

The Wen/Wen 1.1 research model was used to exercise the system's mechanics:
forking shared context, preserving native state, moving checked checkpoints,
pausing and continuing requests, and completing small read/edit/test/finish tasks.
Original Qwen models provided additional checks through the same system.

These were real model executions with bounded tasks and explicit controls.
They were not a full working day of varied inference, many users, long queues,
repeated failures or sustained memory and disk pressure.
A mechanics test can pass even when a model is poor at an unfamiliar task.

The recorded stack work includes 158 focused BW integration tests, native
Wen/Qwen feature-off/on workflows and six saved native workflows reopened with
their servers stopped. Earlier installed-client checks cover follow-up edits,
steering, alternatives and restart continuation.
[Read the evidence](docs/STACK-INTEGRATION.md),
[project-loop checks](validation/real-project-loop-20261020/README.md) and
[fresh-client installation checks](validation/linux-lan-install-20261020/README.md).

**Feature unification has working, tested increments; the full integration and
validation programme is still unfinished.** Broader project quality, a day-long
realistic load, all listed hardware paths and the complete G1-G5 correctness/stress
programme remain open. The detailed [PCC guide explains what each test established](https://github.com/CC-David-CC/Private_Context_COW/blob/main/docs/START-HERE.md#why-we-used-a-research-model).

CAD, Blender, images and remote administration need separately configured tools.
The standard installer does not enable model-driven browser inspection;
`/preview` lets you review saved websites yourself.

## Learn more

- [One-computer and remote-server guide](docs/START-HERE.md)
- [Example requests](examples/prompts/README.md)
- [Repair an existing contact-directory project](examples/repair-contact-directory/README.md)
- [Interactive session and saved versions](docs/manual/09_INTERACTIVE_SESSION.md)
- [Two checked approaches](docs/PARALLEL-EXPLORATION.md)
- [Preview and provenance](PUBLIC_PREVIEW.md)
- [Workflow language](spec/BW_FIRST_PRINCIPLES_v0.6.md)
- [Run and step a workflow](docs/AUTONOMOUS_RUN.md)
- [Registered tools](docs/TOOL_REGISTRY.md)
- [Model integration](docs/MODEL_FLOW.md)
- [API integration plan](docs/COW_INTEGRATION_PLAN.md)

MiniCPM native integration and optional direct tools: [guide](docs/MINICPM-DIRECT-TOOLS.md), [measured evidence](docs/MINICPM-INTEGRATION-EVIDENCE.json).

## MiniCPM native development results

[The five-objective BW screen](docs/MINICPM-DIRECT-TOOLS.md#five-objective-follow-up)
passed three Python tasks and failed two shell tasks. Same-weight peer successes
make the shell workflows the next harness investigation. Evidence includes saved
artifact checks and explicit budget differences; this is not a general ranking
or a MiniCPM training result.

[Why the shell tasks failed](docs/MINICPM-SHELL-INVESTIGATION.md): clearer tool
contracts/feedback improved the five-objective screen to five correct saved
artifacts and four completed tasks. One regressing prompt variant was rejected;
verification/termination on the remaining task is unresolved. No weights changed.

[Pin the training parent](docs/PINNED-TRAINING-PARENTS.md) when continuing a
registered model or hat. PCC refuses a job/hash mismatch before queuing; S³
keeps its learning and release decisions separate.

[Registered LoRA AdamW through BW and COW](https://github.com/CC-David-CC/Private_Context_COW/blob/feat/native-learning-curves-20261024/docs/REGISTERED-LORA-ADAMW.md) now has real CPU checks and a short MiniCPM A100 qualification through both actual clients. Resumed and uninterrupted GPU updates produced identical adapter and optimizer-state file hashes. It is explicit and optional; existing default training recipes are unchanged.

Owner-side evidence export: [read captured coding actions without replay](docs/CAPTURED-ACTION-TURNS.md). This optional reader does not approve correctness or training.


[Replacement permission fix](docs/REPLACEMENT-MODE-PRESERVATION.md): file edits now retain their original mode under restrictive owner umasks, preventing a demonstrated harness-caused workflow failure.
