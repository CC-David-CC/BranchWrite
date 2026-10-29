# Local MiniCPM/PCC Surface setup (experimental)

This path is independent of the remote Q4 server. `BW-local` starts a user-owned PCC server on loopback port 18101 and runs the installed BranchWrite client. It is for experimentation, not yet a dependable file-editing system: a local 2B Q5 conversation succeeded and bounded CPU tokenizer and checkpoint probes passed, but CPU and GPU file-task attempts did not complete within several minutes. The tested remote Q4 route is the one that completed the file task.

The following recreates the tested CPU components on x86-64 Linux; it needs internet for source and Python packages, suitable compiler/build tools, and an already obtained GGUF. It does not need sudo once those prerequisites are installed. Keep build folders new, and do not overwrite existing projects or private keys.

Install BranchWrite as described in its client guide. As the normal user:

```sh
mkdir -p ~/Applications/pcc-surface-runtime ~/Applications/Private_Context_COW
chmod 700 ~/Applications/pcc-surface-runtime
git clone https://github.com/CC-David-CC/Private_Context_COW.git ~/Applications/PCC-dense-attention
git -C ~/Applications/PCC-dense-attention checkout --detach 49560783d2e535c5a3f1c303747cbb7c4bc99da4
python3 -m venv ~/Applications/Private_Context_COW/.venv
~/Applications/Private_Context_COW/.venv/bin/python -m pip install -r ~/Applications/PCC-dense-attention/requirements-cow-server.txt
git clone https://github.com/ggml-org/llama.cpp.git ~/Applications/pcc-surface-runtime/llama.cpp
git -C ~/Applications/pcc-surface-runtime/llama.cpp checkout --detach 972d2313bc0bf0a45f634f77d95c9fb03aeab12c
cd ~/Applications/PCC-dense-attention
python3 experimental/branching_context/scripts/prepare_wen_llama.py --llama ~/Applications/pcc-surface-runtime/llama.cpp
python3 experimental/branching_context/scripts/build_llama_dense.py --llama ~/Applications/pcc-surface-runtime/llama.cpp --engine-build ~/Applications/pcc-surface-runtime/engine-cpu --output ~/Applications/pcc-surface-runtime/dense-cpu --build-engine --cpu-only
```

Place `MiniCPM5-2B-SSS-Muon-Full-U068-Q5_K_M.gguf` under `~/Downloads/minicpm/`. The tested file's SHA-256 was `5d3f60288c576c8122c4b950343611051365b2a1e7e2be3536e0175d825da439`; model weights are a separate artifact. Use the exact matching model or investigate compatibility, identity and licensing before substituting.

```sh
cd ~/Applications/PCC-dense-attention
~/Applications/Private_Context_COW/.venv/bin/python experimental/branching_context/scripts/prepare_llama_dense_profile.py \
  --model ~/Downloads/minicpm/MiniCPM5-2B-SSS-Muon-Full-U068-Q5_K_M.gguf \
  --build ~/Applications/pcc-surface-runtime/dense-cpu \
  --output ~/Applications/pcc-surface-runtime/profile-cpu-32k.json \
  --context 32768 --batch 64 --threads 4
```

Create the local server configuration and a **new private** API key. This example refuses to overwrite an existing server directory:

```sh
python3 - <<'PY'
import json, os, secrets
from pathlib import Path
h = Path.home()
b = h/'Applications/pcc-surface-runtime'
s = b/'server'
os.umask(0o077)
s.mkdir(mode=0o700, exist_ok=False)
k = s/'api-key.txt'
k.write_text(secrets.token_urlsafe(32)+'\n')
k.chmod(0o600)
c = dict(profile=str(b/'profile-cpu-32k.json'), store=str(s/'store'),
         api_key_file=str(k), host='127.0.0.1', port=18101,
         ram_gib=1, disk_gib=4, min_available_gib=1,
         checkpoint_idle_seconds=1800, scheduling='fifo')
p = s/'server.json'
p.write_text(json.dumps(c, indent=2)+'\n')
p.chmod(0o600)
PY
```

Copy `BW-local` into `~/.local/bin/BW-local`, make it executable, and run `BW-local` from a disposable project. The parent `~/Applications/pcc-surface-runtime` must remain mode 700 for private client settings. On first launch the server may take time to load; errors are reported with its user-owned log path. The profile binds exact source and model bytes; do not silently reuse old checkpoints after changes.

The eight-layer CUDA adaptation is a separate [experimental PCC branch](https://github.com/CC-David-CC/Private_Context_COW/tree/codiserver/surface-2gb-gpu-experiment-20261029) with important qualification limits. It is not the default above. No automatic idle shutdown is implemented; a GPU-backed server may keep the GPU awake until it exits. A clean installation using these instructions has not yet been exercised.
