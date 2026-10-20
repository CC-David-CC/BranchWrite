# Install BranchWrite and connect

## Use the prepared Linux client

Windows is the steering wheel. Open PowerShell and type:

```powershell
ssh llm-49
```

In that Linux terminal, make a project folder and run the current client:

```sh
mkdir -p ~/projects/my-first-bw-project
cd ~/projects/my-first-bw-project
/home/dflanag3/spatial-artifacts/bw-private-install-dev65-20261020/release/venv/bin/branchwrite
```

Type the server address your operator gives you. On this fleet the original Q4 service is http://10.0.7.68:8099; a separately controlled trial uses18099. Check CURRENT_STATE.md before choosing. Use the operator's API key when asked. The key stays in memory. --save-api is an explicit choice to save it. Do not post the key or put it in a project file.

You can say: Make a pretty little website about dogs. When it finishes, ask for a change. You do not need to know the filenames. Work mode can read, create and edit project files in an owned workspace and publishes guarded changes into this project. Saved versions let you go back. /plan discusses before editing; /aside asks a temporary question. /preview shows a saved HTML site, PDF or text file. On a remote client, follow its printed SSH tunnel instructions to see that result on your own computer.

## Install on a different Linux client

Your operator provides the private wheel and its SHA256. No model or CUDA installation belongs on the client. A virtual environment, or venv, is a separate folder of Python packages for this app.

The operator first installs Python3.11 or newer, Git, OpenSSH client, bubblewrap and util-linux. Python3.12.15 is the current prepared-client interpreter. On Ubuntu/Debian, an administrator can install missing OS tools with:

```sh
sudo apt-get update
sudo apt-get install python3 python3-venv git openssh-client bubblewrap util-linux
```

Do not replace the system Python. No sudo is used by model-generated local commands. The separate explicitly granted remote-admin tools have the permissions of their configured remote account.

Put the wheel supplied by your operator in ~/Downloads. In Linux:

```sh
python3 --version
python3 -m venv ~/branchwrite-client/venv
~/branchwrite-client/venv/bin/python -m pip install ~/Downloads/branchwrite-0.1.0.dev65-py3-none-any.whl
~/branchwrite-client/venv/bin/branchwrite doctor
```

This initial installation downloads the declared packages and compiles their Python caches. If using uv instead, use uv pip install --link-mode copy --compile-bytecode --python ~/branchwrite-client/venv/bin/python followed by the wheel path. Do not use --no-deps. For an offline install, your operator must supply all dependency wheels and use --no-index --find-links with that wheel directory. A wheel alone is not an offline dependency bundle.

The prepared dev65 wheel SHA256 is 856308e203fcbb0cd73fb21c0144e8fc56f2a41c947fbd2a7a7854d607077bcf. Verify the wheel you receive against its operator manifest. A different hash is a different artifact; do not silently substitute it for an unfinished run.

Start the installed app from the project directory:

```sh
cd ~/my-project
~/branchwrite-client/venv/bin/branchwrite
```

No shell activation is required. The app learns authenticated model/profile identities from the real server connection; you do not type invented identities into JSON. A direct LAN connection needs a reachable server address. SSH tunneling is optional when the operator requires it, not an automatic extra hop.

## Keep saved work usable

Keep an unfinished run's original installation, session state and admitted configuration. Reopen that session and use /continue when an operation needs reconciliation. Do not resend an unknown effect under a new ID. New package versions and execution profiles are not silently interchangeable.

Runtime integrity checks remain enabled. Do not install, delete caches, or run package maintenance in an admitted environment. Initial cache compilation and early CLI bootstrap prevent another ordinary help/client invocation from creating late package caches. Unrelated programs changing a shared Python runtime must still be detected.

PDF authoring and actual page rendering are included. CAD additionally needs the prepared build123d plus bd_warehouse environment. Blender needs the pinned distribution and bounded MCP environment. These are operator setup steps described in ../../SPATIAL-CREATION-GUIDE.md. They are not per-task installs. General model-directed browser tools and arbitrary MCP servers remain separate work; /preview lets the person inspect saved outputs now.

The operator can run tools/verify_client_wheel.py --wheel PATH --work-dir NEW_DIRECTORY, optionally --wheelhouse COMPLETE_OFFLINE_DIRECTORY. It installs without source imports, exercises an actual isolated shell/file operation, builds/reopens/renders a PDF and checks help does not mutate the admitted runtime. This is an installation check, not model or release certification.

## Operator: release-owned Python base

A venv shares its original Python standard library. For saved workflows, prepare
a dedicated standalone Python and use the tested installer from this repository:

```sh
python3 tools/install_private_client.py --source-python /path/to/standalone/bin/python3.12 --uv /path/to/uv --wheel /path/to/branchwrite-0.1.0.dev65-py3-none-any.whl --dest /new/path/to/branchwrite-release
/new/path/to/branchwrite-release/venv/bin/branchwrite doctor
```

Use a new destination. The installer refuses system Python as a cloning source.
It verifies the copied interpreter, installs default dependencies and makes the
release runtime read-only. Keep full integrity checks on. Do not maintain or
install packages inside an admitted runtime. The operator prepares this once;
the person using BranchWrite only starts the app in their project folder.
See PUBLIC_PREVIEW.md for current scope and retained earlier client versions.
