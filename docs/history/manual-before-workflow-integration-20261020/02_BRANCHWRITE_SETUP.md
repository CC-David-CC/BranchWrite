# Install BranchWrite and connect to COW

## Current tested installation

Dev33's simple project startup is installed on llm-49:

```sh
/home/dflanag3/spatial-artifacts/branchwrite-dev33-project-20261020/installed-check/venv/bin/branchwrite
```

It connects directly to the dedicated Q4 COW service on llm-60. The API key stays
in memory unless --save-api is selected. Follow [First task](06_FIRST_TASK.md).
The source integration of durable receipts, bundled follow-ups and new startup
is a separate dev37 candidate until its current checks are complete.

A virtual environment is a folder containing this app's Python installation.
Keep separate environments for pinned older runs. The model stays on the server.
The detailed historical setup below remains for those older installations.

## 1 Use the existing installation or install the wheel

On Windows PowerShell, open a Linux client terminal:

~~~powershell
ssh llm-49
~~~

On llm-49, the simplest option is the existing installation:

~~~bash
source /home/dflanag3/spatial-artifacts/branchwrite-dev30-package-20261020-v1/installed-check/venv/bin/activate
branchwrite --help
~~~

For a separate installation on an Ubuntu/Debian client, install the host tools if missing. This package-manager command needs that client's administrator permission:

~~~bash
sudo apt-get update
sudo apt-get install python3 python3-venv bubblewrap util-linux openssh-client git
~~~

Create a venv, which keeps this app's Python package separate:

~~~bash
python3 --version
mkdir -p "$HOME/branchwrite-install"
python3 -m venv "$HOME/branchwrite-install/venv"
source "$HOME/branchwrite-install/venv/bin/activate"
~~~

Get the wheel from an account with access to private box-git:

~~~bash
scp box-git:/srv/data/git/private_context_cow.evidence/branchwrite-dev30-package-20261020-v1/wheel/branchwrite-0.1.0.dev30-py3-none-any.whl "$HOME/branchwrite-install/"
~~~

SSH access to box-git must already be configured. Alternatively, the same wheel exists on llm-49 under /home/dflanag3/spatial-artifacts/branchwrite-dev30-package-20261020-v1/wheel/. Copy that file through your authorized SSH connection.

Check its hash:

~~~bash
sha256sum "$HOME/branchwrite-install/branchwrite-0.1.0.dev30-py3-none-any.whl"
# Expected: 2bbde88b7edc6a7c8aff062d5d7ac8703d1f7a902d6cb4e922b25e3d5873c872
~~~

Expected SHA256:

8e6b4912cc49e6958c99e88d9a003885912378e16b47443b92ca96398983a6d6

Install without downloading other Python packages:

~~~bash
python -m pip install --no-index --no-deps "$HOME/branchwrite-install/branchwrite-0.1.0.dev30-py3-none-any.whl"
branchwrite --help
~~~

The CLI needs Python 3.11 or newer. If python3 --version reports an older version, stop and install a supported distribution-provided interpreter before making the venv. Do not replace the system Python in place. Dev24 was exercised on Linux/Python 3.14.4. A successful pip install does not establish that the host permits the Linux tool sandbox. BranchWrite checks the actual shell boundary before model work. A sandbox refusal is an error, not permission to run tools without isolation.

Keep this venv and wheel for unfinished dev30 runs. Existing dev28 runs must keep their dev28 environment. New source versions change frozen interpreter/tool identities; do not silently upgrade an unfinished run.

## 2 Establish ordinary SSH access to llm-60

From the Linux client:

~~~bash
ssh dflanag3@llm-60
~~~

Exit that session after checking the host identity:

~~~bash
exit
~~~

If SSH is not configured, create a personal client key with ssh-keygen and install its public key through your authorized account access, for example with ssh-copy-id. Verify the host key fingerprint. Do not reuse retired temporary campaign keys or copy a private key from someone else's account.

## 3 Open a tunnel in its own client terminal

Start the server first using the server guide. In a separate Linux client terminal run:

~~~bash
ssh -N -o ExitOnForwardFailure=yes \
  -L 127.0.0.1:18099:127.0.0.1:8099 \
  dflanag3@llm-60
~~~

Leave this terminal open. It forwards client port 18099 to server port 8099. A local connection to 18099 now reaches COW through SSH. Use a different local port if 18099 is occupied, and change connection.json accordingly.

In another client terminal:

~~~bash
curl --fail http://127.0.0.1:18099/health
~~~

## 4 Create connection.json and enter the API key

In the client terminal where you will run BranchWrite:

~~~bash
umask 077
mkdir -p "$HOME/branchwrite-client"

cat > "$HOME/branchwrite-client/connection.json" <<'JSON'
{
  "endpoint_url": "http://127.0.0.1:18099",
  "endpoint_pin": "llm-60-manual-ssh",
  "model_contract_id": "3fcd9cfc2e977dbf56522e710cb3903e03ab00ca2ed5d0daa3d9f840edf5a833",
  "execution_profile_id": "7ed02ba4f2e842b82c798b9194a8a7b489c6e86c85de9f41a0770a40f9d79e36",
  "eos_tokens": [248044, 248046]
}
JSON

read -rsp "Paste the server COW API key, then press Enter: " BW_COW_API_KEY
echo
export BW_COW_API_KEY
~~~

These identities are for the exact Q8 profile in the server guide. If you use another profile, obtain its actual identities and EOS token IDs from the operator. Do not invent them. endpoint_pin is the client's stable name for this trusted SSH endpoint; it is not a substitute for SSH host-key verification.

Do not store the key inside connection.json or source files. Each new client shell needs the exported variable. Closing the tunnel or shutting down the server does not erase saved client workflows.

## 5 Run a coding task

Follow [Create or edit an HTML site](04_HTML_WORKFLOW.md). Each new task gets a new run-state directory and server branch name. To continue an unfinished task, use resume with its original state.

## Private source checkout and installation check

A source checkout is optional for users of the wheel:

~~~bash
git clone --branch feat/explicit-model-reconciliation-20261019 \
  box-git:/srv/data/git/BranchWrite.git "$HOME/src/BranchWrite"
~~~

The exact dev30 wheel source is b48b8ac9043cb8678329e83f1f6e57abf610c084. Later commits on that branch may be evidence/docs changes or further development. Inspect the handoff before building. Keep the packaged wheel as the tested installation.

The repository includes a separate no-model install check:

~~~bash
python3 "$HOME/src/BranchWrite/tools/verify_client_wheel.py" \
  --wheel "$HOME/branchwrite-install/branchwrite-0.1.0.dev30-py3-none-any.whl" \
  --work-dir "$HOME/branchwrite-install/check-dev30"
~~~

Use a new check directory. This check installs the wheel into a new venv, verifies packaged assets, creates an actual file and runs a read-only isolated shell. It does not perform inference or certify an arbitrary machine.

No audit harness, COW source tree, CUDA package or model weights belong in the client wheel.

## Optional browser tools

The basic website workflow uses your own browser for preview. Internal browser
capture is optional and additionally requires Pillow, Playwright and a Chromium
executable that can start with its sandbox enabled inside the client isolation.
The tested llm-49 browser currently fails that sandbox startup. Installing Python
packages alone does not resolve it. Do not disable sandboxing to continue; use
the manual preview workflow until this client environment is qualified. Current
source reports this failure explicitly; the installed dev25 wheel may show a
blank capture error. Working internal captures were separately tested on llm-60.

## Development-source client self-check

Current development source additionally supplies `branchwrite doctor`. It creates
only temporary owned files, checks literal-byte transport through a real isolated
shell, verifies the source remains unchanged and checks worker retirement. Exit 0
means these client checks passed; exit 2 reports a failed check. It does not load a
model or validate the server/browser. This command is included in dev30.
After activating the dev30 venv, run `branchwrite doctor`.
