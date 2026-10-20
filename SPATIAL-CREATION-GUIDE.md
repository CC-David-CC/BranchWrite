# BranchWrite coding, CAD and Blender pilot

BranchWrite writes the files and chooses tools. Context COW keeps the model's saved context and branch state on llm-60. The CAD and Blender tools execute on the Linux BranchWrite client, currently llm-49. Windows is the steering workstation; it does not build, render, or store the campaign outputs.

## What was actually demonstrated

Installed dev63 interactive CAD passed the exact plate request with real Q4: two builds, a self-repaired Location API error, unchanged independent STEP requirements and actual four-view review. The CLI reopened the same session for Blender and preserved the earlier CAD files/history. Its original Blender work resumed after an operator cache-mutation incident; the actual scene then passed one build, actual image review, independently45-degree single-arm movement and24 decoded H.264 frames. Saved file/context/export selection worked without any new model request. Current receipts: validation/cli-cad-session-q4-20261020/ and validation/cli-blender-session-q4-20261020/.

The carrier/base family has actual independent STEP fixture tests, including preserved mating interfaces, wrong-side notch and shifted carrier. This remains fixture coverage, not an autonomous carrier design pass or measured printed fit. build123d plus bd_warehouse environment setup was exercised with actual catalogue queries, M4 screw export/reopen and a matching clearance hole. Not every library component or thread form is qualified.

Blender4.5.3 and MCP SDK1.26.0 are pinned. The tool independently reopens .blend, renders four controlled views and24frames with CPU Cycles, fits cameras to evaluated geometry throughout the animation, and rejects stale source. Its adapter is bounded stdio MCP; no third-party live addon, network listener, telemetry or asset download is enabled. General arbitrary MCP support is separate. The actual scene is not accepted as CAD geometry.

## Operator setup on Linux

1. Install BranchWrite from this private checkout into a Python 3.12 virtual environment using the existing installation guide. The package now includes Pillow because image feedback needs it. Keep API keys in memory unless the user explicitly chooses --save-api.
2. Prepare a separate CAD environment using the pinned requirements under validation/cad-20261020. The initial CAD installation includes build123d==0.13.0 and its separately installed companion bd-warehouse==0.4.0 (Python import bd_warehouse); it is not a later optional add-on for this CAD environment. Use UV_LINK_MODE=copy when installing: shared package-cache hard links can change an admitted runtime's inode metadata during an unrelated install. Never weaken the hash/stat guard. Do not install packages into any admitted runtime while a task is using it.
3. Provide the OSMesa library directory for CPU VTK rendering. The current task-local runtime and Debian package versions are recorded in the evidence. No GPU is required for CAD construction or these CAD views.
4. Download the pinned Blender distribution and verify the release checksum. Create a separate MCP environment with mcp==1.26.0, using copy mode. Nothing installs a global addon or rewrites another client's configuration.
5. Enable COW's existing --vision-config option with its pinned encoder, projector and matching model/profile. A mixed-input native executable alone does not enable image uploads. The live runner now has this configuration; ordinary chat remains off.
6. Write an operator-owned CAD or Blender configuration. The model cannot choose runtime executables or rewrite the fixed requirement document.

### Install and check the initial CAD packages

Use Linux on the execution client, not the Windows steering workstation. A virtual environment is a separate folder of Python packages for this tool. From this private checkout, using the pinned uv installer:

```sh
uv venv --python 3.12.15 /your/private/cadvenv
uv pip install --link-mode copy --compile-bytecode --python /your/private/cadvenv/bin/python -r validation/cad-20261020/requirements.lock.txt
/your/private/cadvenv/bin/python -B tools/check_cad_environment.py
```

The check must print status PASS. It queries the installed catalogue, constructs the M4-0.7 by 16 mm ISO 4762 screw, exports and reopens it, and measures a real 4.5 mm matching clearance hole. Temporary smoke-check exports are removed. The full pinned package set includes bd-materials==0.2.4. Package names use hyphens; Python imports use underscores. Keep these large CAD packages out of the lightweight server-only or ordinary BW client installation.

For a named screw export, run examples/cad/m4_socket_head_screw.py using the CAD Python from a scratch output directory. For model candidates, the existing inspect_cad tool expects the named export part.step; change only the export filename accordingly. The fixed plate/carrier checkers deliberately reject unrequested extra hardware: installing a component library does not make their design requirements accept a screw assembly.

### Standard components and mating features

Use the installed bd_warehouse catalogue rather than guessing a class, standard or size. Python queries such as SocketHeadCapScrew.types() and SocketHeadCapScrew.sizes("iso4762") are available inside the existing isolated Python build. Select the purchased hardware, derive its mating features using helpers such as ClearanceHole, and inspect the actual reopened custom part. simple=True leaves out detailed helical threads for lighter assembly work; it does not prove manufactured thread fit.

The upstream catalogue includes fasteners, nuts/inserts/washers, bearings/bushings, transmission and linear-motion parts, seals/retainers, pipes/flanges and threads. Current executed setup evidence covers the M4 screw, placement, catalogue queries and matching clearance hole, not every catalogue family or thread form. Bearings and their PressFitHole, TapHole, ThreadedHole and InsertHole require their own measured fixtures before claiming supported design acceptance. See the [upstream installation](https://bd-warehouse.readthedocs.io/en/latest/installation.html) and [fastener API](https://bd-warehouse.readthedocs.io/en/latest/fastener.html).

Next hardware milestone: a bearing carrier with specified screws, actual mating seats and reopened geometry measurements. Screw engagement, access, surrounding material and interference need explicit checks. Other ecosystem packages (bd_beams_and_bars, bd_vslot, py_gearworks and PartCAD) are deferred until a real task needs them. No extra CAD service or second workflow representation is introduced.

Current client environments and binaries:

- CAD: /home/dflanag3/spatial-artifacts/bw-build123d-20261020/cadvenv/bin/python
- CPU render libraries: /home/dflanag3/spatial-artifacts/bw-build123d-20261020/osmesa-runtime/root/usr/lib/x86_64-linux-gnu
- Blender: /home/dflanag3/spatial-artifacts/bw-blender-20261020/blender-4.5.3-linux-x64
- MCP Python: /home/dflanag3/spatial-artifacts/bw-blender-20261020/mcpvenv/bin/python
- Source: /home/dflanag3/src/branchwrite-cad-20261020
- Private Git: box-git:/srv/data/git/BranchWrite.git, feat/build123d-task-family-20261020

CAD config fields are python, osmesa, timeout, and requirements. Copy the requirement document from acceptance/cad/plate-v1.json or carrier-v1.json, rather than embedding construction code. Blender config fields are distribution, mcp_python, timeout, require_animation. Paths are absolute; timeouts are positive and at most 120 seconds per native worker.

## Use it from a project directory

The server connection and key follow the existing BranchWrite setup. These optional domain tools require Linux execution environments on the client. With the server and operator configurations prepared:

```
/path/to/branchwrite code . --project-files --cad-config /path/to/cad-config.json --task "Build the required mounting plate. Inspect it and fix any failed measurements."
/path/to/branchwrite code . --project-files --blender-config /path/to/blender-config.json --task "Build a little colored mechanical scene and animate its moving part. Inspect the actual views and animation."
```

BW works in an owned copy, keeping the source project unchanged. The run JSON names its state directory. inspect_cad returns STEP, measurements, actual PNG views and a static HTML report. inspect_scene returns scene.blend, actual PNG views and an MP4. Exports are immutable workflow artifacts outside the source workspace; they are not source files for run_shell to find. The CLI's exports field names their hashes and local paths. Copy a chosen export to your desired destination; do not rename or modify the canonical artifact itself.

Use the existing resume command with the saved state after an interrupted client. Never create new operation IDs to get around unknown effects. A new task or requirement revision starts a new admitted run. Use --from-branch with the exact completed source branch to reuse its saved context, together with the project version you want to edit. A past model context does not isolate filesystem output; each run still gets its own owned workspace.

## Verification boundaries

Candidate Python never receives the protected CAD checker. The build process has no host home, credentials, network or GPU devices; it gets captured read-only input and bounded scratch. A syscall filter permits threads but rejects candidate-created processes and namespaces. The independent STEP checker and renderer run in a different retired namespace. Runtime bytes are hashed at admission and checked for changes at execution boundaries. This is bounded Linux x86-64 process isolation, not a kernel-security certification or cgroup RSS guarantee.

CAD inspects actual reopened geometry using direct OpenCascade reference CSG and feature measurements. Construction and checking share OpenCascade, so this does not independently certify the kernel. Frozen tolerances remain 1e-6 mm and 1e-5 mm3; they were not widened. The 90 mm plate contradiction remains analytically checkable: preserving 76 mm centers, 5 mm diameter and 8 mm edge material needs at least 97 mm width.

Every view and export names its source revision, requirements or render profile, runtime and artifact hashes. A source change makes the old acceptance evidence stale. Artistic quality is not established by a successful render. Blender acceptance currently checks the stated scene/render pipeline and, when requested, observed transform animation. Animation transforms are sampled at frames 1,12,24; all 24 output frames are actually rendered.

One fixed domain completion policy is selected per pilot run. Direct import of a CAD export into Blender, general mixed-domain completion, carrier model qualification, changed-plate model revision, infeasibility dialogue and matched-budget search comparisons remain unqualified or unimplemented. Normal coding/admin flows remain available. Long stress, adversarial parser campaigns, Q8 and cumulative gates remain separate.

## dev58 controlled-view correction

Two real renderer regressions were reproduced: a moving cube left the cameras fitted only to frame12, and a valid world-less .blend failed in the derived studio setup. The new bw.blender-cpu-views-motion.v2 render profile fits evaluated mesh bounds across all24 rendered frames, accounts for image aspect in each camera's projected basis, uses explicit horizontal orthographic fit and scale-relative clipping, and supplies a studio world when absent. Frames1,12,24 still provide the transform report; this is not a continuous-time motion/collision proof. The authored .blend is unchanged by the independent inspection. Front is negativeY, side positiveX, top positiveZ, with Z up.

New launches use dev58 and the new runtime/profile fingerprints. The live autonomous dev57 scene run keeps its admitted installation and old render profile; its eventual result is separate evidence and does not qualify dev58.
