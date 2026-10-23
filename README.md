# BranchWrite (BW)

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
