# BranchWrite

Tell BranchWrite what you want to make or change. It works on the project folder
where you start it, keeps saved versions, and lets you steer while it works.

## New here? Start with two computers

**[Set up a desktop server and a laptop client](docs/TWO-COMPUTER-SETUP.md).**

This plain-language Linux guide covers both machines, automatic Q4 model
download, model preparation, the server address, the API key and your first
website. It does not need an AI agent to explain missing file paths.
Read the hardware and download size first: the current Q4 model is about 111 GB.
This is not a promise that every gaming PC has enough memory to run it.

**Already have a Context COW server?** Use the shorter
[client-only installation guide](docs/LINUX-QUICKSTART.md).
The laptop needs no GPU and does not download the model.

## What goes on each computer?

| Piece | Where it runs | What it does |
|---|---|---|
| Context COW server | Your NVIDIA/Linux desktop | Runs the model and keeps reusable model context in RAM/disk pools. |
| BranchWrite client | Your Linux laptop or desktop | Talks with you, manages saved work and calls the server over HTTP. |
| BranchWrite tools and workflow harness | The client | Reads and changes the project, runs bounded tools and records their results. |

Your project stays on the client. Content needed for a request goes to the model
server you choose. Your API key stays in memory unless you request `--save-api`.

## Start in a folder

After installation:

```sh
mkdir -p ~/my-first-website
cd ~/my-first-website
~/.local/bin/bw
```

Try:

> Make a pretty website about dogs. Make it work on a phone. Add a button that
> shows a friendly greeting. Keep everything in one file and do not download anything.

Then:

> Make the dog names bold. Keep the greeting button working.

Use `/preview` to open the saved static website. Work mode changes this project's
files and keeps saved versions. You can ask another question after a task finishes.
You do not need to start again.

## Stay in the conversation

- **Enter:** send a request or steer active work.
- **Tab:** queue notes together for the next turn.
- **Esc:** ask it to stop at a safe boundary.
- **Ctrl+R:** search your earlier input.
- **/plan:** discuss without editing files.
- **/work:** make changes.
- **/aside your question:** ask without changing the main model tip.
- **/exit:** save and leave. Reopen BW in the same folder to return.

The [interactive guide](docs/manual/09_INTERACTIVE_SESSION.md) explains saved
history, switching versions, retry and exploring another direction.
[Example prompts](examples/prompts/README.md) cover the separately configured tools.

## Why saved branches matter

Related tasks can start from shared model context and continue independently.
You can explore a different repair without replacing the current files, return
to an earlier saved point, and keep the model's reusable computation on the server.
A `.bw` file is a workflow recipe, not a KV-cache file. COW owns the computational
checkpoints; BW owns its durable workflow and references to them.

## Current release scope

This is a public research preview. Tested workflows include real CLI-to-server
coding, follow-up edits, queued steering, isolated alternatives and process-restart
continuation. See [executed project-loop evidence](validation/real-project-loop-20261020/README.md)
and [fresh-client installation evidence](validation/linux-lan-install-20261020/README.md).
Those results are bounded checks, not full G1–G5 certification or a guarantee on
unfamiliar hardware. CAD, Blender, image encoding and remote administration need
their own configured capabilities. The standard installer does not yet enable
model-driven browser inspection.

## For developers

- [Current preview and provenance](PUBLIC_PREVIEW.md)
- [Workflow language](spec/BW_FIRST_PRINCIPLES_v0.6.md)
- [Run and step a workflow](docs/AUTONOMOUS_RUN.md)
- [Registered tools](docs/TOOL_REGISTRY.md)
- [COW model integration](docs/MODEL_FLOW.md)
- [API integration plan](docs/COW_INTEGRATION_PLAN.md)
- [Context COW server source](https://github.com/CC-David-CC/Private_Context_COW)

The inference engine is based on [Strata](https://github.com/Niko1221/Strata).
This release uses the documented pinned source; the planned Strata refresh is separate.
