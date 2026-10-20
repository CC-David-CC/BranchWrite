# BranchWrite

## Install and start on Linux

Your model runs on a Context COW server. This client needs no GPU or model files.
First follow the [simple Linux setup guide](docs/LINUX-QUICKSTART.md). It includes
the system tools, one download command, LAN address/key setup and a tested
website example with pictures. Then open a terminal in your project folder and
run `~/.local/bin/bw`.

[Server setup](https://github.com/CC-David-CC/Private_Context_COW/blob/main/docs/CONTEXT-COW-SERVER.md)
| [Executed LAN install and restart smoke](validation/linux-lan-install-20261020/README.md)


Source preview, 2026-10-20. Server: [Context COW](https://github.com/CC-David-CC/Private_Context_COW). Original engine: [Strata](https://github.com/Niko1221/Strata). This preview predates the planned Strata 2.1 refresh. See [current release notes](PUBLIC_PREVIEW.md) and [example prompts](examples/prompts/README.md).

BranchWrite is an experimental Linux command-line coding agent powered by Context COW. It keeps a durable record of tool work and uses server-owned model branches and saved prefill.

Start in your Linux project folder with `branchwrite`, then describe what you want in ordinary words. The responsive terminal stays open while BW works: Enter adds steering, Tab queues notes together for the next turn, and Esc stops at a safe boundary. Work mode updates files in this folder and keeps saved versions. Plan and Chat let you discuss the project; Aside leaves its main model tip unchanged. Use `/preview` to open the selected saved static website; remote SSH clients get a tunnel command. Read the [interactive guide](docs/manual/09_INTERACTIVE_SESSION.md) for keys, history, branch exploration and recovery.

Your operator supplies the COW server address and API key. Keys stay in memory by default; `--save-api` explicitly opts into private storage. The original one-task wizard is still available as `branchwrite start` and works in an isolated copy for review.

Private Linux client installation: [CLIENT_INSTALL.md](docs/CLIENT_INSTALL.md). Project/task launcher: [CODING_LAUNCHER.md](docs/CODING_LAUNCHER.md). Latest bounded Q8 results: [STANDALONE_CODING_STATUS.md](docs/STANDALONE_CODING_STATUS.md).

## Manual setup and use

Start with [Context COW and BranchWrite manual guides](docs/manual/00_START_HERE.md) for server startup, client installation, connection, an HTML task and the current private handoff.

New coding default: **greedy with worked examples**. Min-P and DRY+Min-P are
explicit fallback profiles for verified task failures. Use
`examples/coding.bw`, omit `profiles`, and select COW `bootstrap: coding` for a
new example-backed context. See [the run guide](docs/AUTONOMOUS_RUN.md). Explicit
profiles stay exact; existing saved controllers are not rewritten.

Current Linux execution prototype: [run/step guide](docs/AUTONOMOUS_RUN.md).
A .bw file is a workflow recipe; Context COW separately owns native computational
checkpoints. Current delivery goal: one push-button autonomous coding run.
Original certification and broad unfamiliar-workload validation remain open.

# BranchWrite - private prototype

**Private implementation of one durable controller for model and tool work.**

The production [program reader](docs/PROGRAM_READER.md) supports read-only
syntax checks and canonicalization. Linux run/step also execute the supported
bounded model/tool loop through Context COW. Basic Agent Loop H00-H12 have
bounded autonomous Q4 passes,including actual browser images and desktop/phone
controls. Advanced workflow handlers and broad qualification remain incomplete;
see the executed evidence before selecting a workload.
The [model invocation adapter](docs/MODEL_FLOW.md), [registered tools](docs/TOOL_REGISTRY.md)
and [latest evidence](validation/CURRENT-CATALOG-STATUS.md) distinguish working
components from remaining integration and unqualified native/product cases.


Current private repository: `box-git:/srv/data/git/BranchWrite.git`. Product and command are BranchWrite / `branchwrite`.
GitHub/upstream publication requires separate owner approval. The retained v0.3.0
handoff describes the broader target; it is not a completed-product claim.
Active proposed contract: `spec/BW_FIRST_PRINCIPLES_v0.6.md`.

The current [Context COW integration plan](docs/COW_INTEGRATION_PLAN.md) maps this
contract to the inspected service, CLI/HTTP clients, sampler exploration and
full-path recovery tests. It is a plan; no product acceptance is implied.

Development now includes a native COW client, a bounded Linux edit/test executor,
and a [first coding pilot](docs/CODING_PILOT.md). The pilot completed real Q4
model/edit/test/feedback cases; [executed results and limits](validation/CODING_PILOT_Q4_2026-10-16.md)
distinguish working components from the proposed full runtime. This remains
private development, not a public release or complete product qualification.

The initial [GOLDEN PATH helper](docs/GOLDEN_PATH.md) keeps a stable purpose and
working examples in a COW prefix, then versions evidence-backed observations and
derived summaries. Workers can fork a specific summary's saved computation.
Automatic project harvesting/adoption and bounded thinking remain separate work.

The unit is a **typed computation frozen against its relevant exact state**, executed by
one durable interpreter. Independent continuations, native grammar progress, sampler
state, physical scopes, evidence and return slots remain independently owned.

## The change

The former seven verbs are author-facing intent categories, not a second interpreter.
The executable vocabulary is:

`EXPAND CONTINUE PLAN ACT OBSERVE TRANSFORM SAVE VERIFY CHALLENGE COMPARE SELECT COMPOSE COMMIT ABANDON`

Structural constructs remain `FLOW REPEAT BRANCH PARALLEL.PLAN PARALLEL.DO ON`.
`PLAN` freezes a computation; `SAVE` pins an already durable result. A successful typed
return closes a settled scope; `ABANDON` is not a euphemism for success or rollback.

The canonical workflow uses typed `.bw` text. Explicit JSON/JSON Schema model
output is also supported beside GBNF, including required fields, tool enums and
argument types. The owner retired the blanket JSON bans on 2026-10-17. This does
not introduce another workflow ledger or an automatic repair-to-JSON path.
Active configuration/catalogue files use TOML; raw artifacts remain exact bytes.
The unchanged original archive and historical specifications in `provenance/` still
contain the old JSON material. They are evidence, not active implementation inputs.
A pre-existing native service's internal transport encoding remains that service's
contract; this bundle neither requires model JSON support nor invents a new COW wire API.

## Start

For an installed private client, open a terminal in the project folder and run `branchwrite` for the guided first-task flow. See [First task](docs/manual/06_FIRST_TASK.md).


Read `START_HERE.md`, `CODEX_PROMPT.md`, the active specification, and `docs/MIGRATION.md`.
For the current coding experiment, follow `docs/CODING_PILOT.md`. The executor
runs on Linux with the documented bubblewrap/prlimit boundary and a separately
configured COW service. The complete client integration tests also need the
pinned COW source/dependency paths and `COW_CLI_SCRIPT`; they are not a standalone
Windows inference setup.

The following commands belong to the original offline handoff (Python 3.11+):

```sh
python tools/verify_handoff.py
python -m unittest discover -s tests -v
python tools/show_example.py
```

The final H02 source passes 323/323 offline tests after the explicit JSON-policy
retirement. Actual H00 JSON output, H01 browser capture and H02 image-only Q4
delivery/interpretation have separate bounded evidence under `validation/`.
Do not interpret a handoff check or reference test count as product acceptance.

These are **offline handoff/reference checks**, not product acceptance. The `reference/`
code is an executable semantic oracle for a limited language, finite grammar masks,
probability arithmetic, frozen dependencies and typed returns. It is not a native COW
adapter, general GBNF engine, sandbox, production scheduler, or GPU implementation.
Do not import it as a competing production runtime.

All product acceptance cases begin `not_run`. Actual repository, service, GPU, model
quality, native sampler parity, full grammar matching, OS isolation, power-loss recovery,
and execution overlap must be established in the real checkout and qualified profiles.

The previous handoff's 211 product cases are carried forward with an explicit migration
record. Its original 98 offline tests were rerun successfully in this preparation session.
Counts and executed results for this bundle are recorded in `validation/TEST_REPORT.md`.
