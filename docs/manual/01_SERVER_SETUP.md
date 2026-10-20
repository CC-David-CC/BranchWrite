# Start the Context COW server

This procedure uses the existing tested runtime on **llm-60**. It starts a foreground COW HTTP server with one active request on GPU 0. It does not start ordinary chat serving or require an audit runner.

## 1 Connect and check availability

From Windows PowerShell:

~~~powershell
ssh llm-60
~~~

Now run these commands in that Linux terminal:

~~~bash
nvidia-smi --query-compute-apps=pid,used_memory --format=csv
ss -ltn
df -h /home/dflanag3
free -h
~~~

Do not stop an unknown GPU job or replace an occupied port. The example uses server port 8099. If it is occupied, choose an unused port and change the tunnel destination in the client guide.

The tested configuration is Q8, FP16 KV, GPU=[0], capacity 262144 and 512-token prefill chunks. Keep the supplied profile unchanged. Changing chunking, operators or model files requires a new execution profile; an old checkpoint is not interchangeable.

## 2 Select the verified files

~~~bash
COW=/home/dflanag3/src/context-cow-history-counts-20261019
PY=/home/dflanag3/src/Strata/.venv/bin/python
DEPS=/home/dflanag3/spatial-artifacts/grammar-first-20261016-v1/deps
PROFILE=/home/dflanag3/spatial-artifacts/project-base-three-builds-20261019-v1/dev28-pack-base-q8-v1/profile.json

git -C "$COW" rev-parse HEAD
test -x "$PY"
test -r "$PROFILE"
~~~

The server commit used in the tested run is:

895251441266dda1dd4d6437d98fda7251027b68

If this checkout has changed, use an isolated checkout of that commit. Do not reset someone else's working tree. Source startup validation checks the profile's declared file hashes.

The Python environment exists on llm-60. It used Python 3.12.3, Jinja2 3.1.6, regex 2026.9.29 and llguidance 1.9.1. The additional pinned packages are supplied by DEPS through PYTHONPATH. A BranchWrite client wheel is not a replacement for these server dependencies.

## 3 Make persistent storage and choose a key

~~~bash
umask 077
mkdir -p "$HOME/context-cow-manual"
mkdir -p "$HOME/context-cow-manual/store"
mkdir -p "$HOME/context-cow-manual/grammars"

read -rsp "Choose the private COW API key, then press Enter: " COW_API_KEY
echo
~~~

Use the same secret when the client guide asks for BW_COW_API_KEY. The read command hides what you type. Do not put the secret in Git, connection.json or a task prompt.

The store contains canonical histories, branch references and optional computational checkpoints. Reuse this store for later server restarts under the same compatible profile. Do not delete the store to clear an uncertain operation.

## 4 Start the server

Run this in the same terminal. Keep the terminal open:

~~~bash
env -i \
  HOME="$HOME" USER="$USER" \
  PATH=/usr/local/cuda/bin:/usr/bin:/bin LANG=C.UTF-8 \
  CUDA_VISIBLE_DEVICES=0 PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH="$DEPS:$COW:$COW/tools:$COW/experimental/branching_context/src" \
  /usr/bin/flock -n /home/dflanag3/branching-g3/native-client-speed.gpu0.lock \
  "$PY" -B -m serve.cow_http \
  --profile "$PROFILE" \
  --store "$HOME/context-cow-manual/store" \
  --host 127.0.0.1 --port 8099 \
  --text \
  --grammar-store "$HOME/context-cow-manual/grammars" \
  --api-key "$COW_API_KEY" \
  --ram-gib 24 --disk-gib 64 \
  --checkpoint-idle-seconds 1800
~~~

The lock coordinates with our GPU campaigns. Lock failure means another owner has the lease; do not remove the lock file to bypass it.

Wait for a JSON line with event "ready". The tested startup took about 76 seconds, but this is not a timeout guarantee. Confirm runtime_sources.status is "verified" and execution_profile_id is:

7ed02ba4f2e842b82c798b9194a8a7b489c6e86c85de9f41a0770a40f9d79e36

The 24 GiB RAM pool and 64 GiB disk pool are configured limits, not total model requirements. The model also uses RAM and VRAM. The server maintains at least 16 GiB available-host-memory admission headroom. A checkpoint idle limit of 1800 seconds expires eligible copies after 30 minutes; retained history may need explicit recomputation later. Expiry does not promise that every checkpoint stays resident.

The grammar store enables the client's authenticated inline tool grammars. Omitting it is not the same supported coding setup.

## 5 Check it from a second llm-60 terminal

~~~bash
curl --fail http://127.0.0.1:8099/health
~~~

This health endpoint is unauthenticated and establishes HTTP availability, not authorization or inference correctness. A useful response says service "context-cow". The client uses authenticated /cow endpoints, not an OpenAI chat URL.

Proceed to the client guide. Keep the server bound to loopback and use SSH forwarding.

## 6 Stop and restart

Press Ctrl+C in the server terminal. Let the process close its worker. Check nvidia-smi afterward. Reuse the same store and grammar directory next time, and enter the same API key to access the same authorization scope.

A graceful stop is preferable to killing Python during publication. After an interrupted client request, keep its run state and original operation ID; follow the handoff guide's recovery instructions. Never blindly submit the uncertain tool again.

## A different server

This is not yet a clean-machine installer. Read [Native engine inventory](03_NATIVE_RUNTIME.md) before copying this profile to another machine. Its absolute paths, source/model receipts, generated binary and hardware configuration must be supplied and validated there. Do not edit out a failed fingerprint check.
