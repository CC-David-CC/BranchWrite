# Native Strata runtime and model files

Context COW is not itself the GPU inference engine. Its Python server starts a pinned native Strata-derived binary. That binary computes the model and captures/restores its computational state.

## Current llm-60 inventory

| Item | Location |
|---|---|
| Native binary | /home/dflanag3/spatial-artifacts/cow-vision-20261016-v1/vc07-dry-entropy-native-build-v1/strata-vision-dry-combinations-cow |
| Binary SHA256 | ae62045f75a8e11ba9d01b4da301d3bb87fe4ff342bab0ea7edc57276377824e |
| Native build receipt | /home/dflanag3/spatial-artifacts/cow-vision-20261016-v1/vc07-dry-entropy-native-build-v1/build.json |
| Generated native driver | The same directory, branch_driver.cpp |
| Linked Strata build | /home/dflanag3/branching-g3/context-cow-public-20261013/build |
| Q8 expert pack | /home/dflanag3/branching-g3/q8-pack |
| Model shards | /home/dflanag3/models/qwen38-flash-next-unsloth-gguf/Q8_0/ |
| First model shard | Qwen3.8-Flash-Next-Q8_0-00001-of-00006.gguf |
| GGUF reader helper | /home/dflanag3/spatial-artifacts/sampler-integration-1538b8b3-v1/source/tools/gguf_reader.py |
| Model hash receipt | /home/dflanag3/spatial-artifacts/cow-vision-20261016-v1/vc-rerun-20261018-v1/report-L05-q8-v1/model-receipt.json |
| Source receipt | /home/dflanag3/branching-g3/private-queue-20261012T0818/source.json |

The model needs all six shards plus the expert pack/tokenizer and expert profile selected by profile.json. The tiny first shard alone is not the model. Keep large weights and native checkpoint payloads outside Git.

The tested GPU was an RTX PRO 6000 Blackwell with about 96 GiB VRAM. The native executable has CUDA runtime/library dependencies. Starting this Q8 configuration on another GPU is not qualified by the llm-60 evidence.

## Inspect the exact binary and link dependencies

On llm-60:

~~~bash
NATIVE=/home/dflanag3/spatial-artifacts/cow-vision-20261016-v1/vc07-dry-entropy-native-build-v1/strata-vision-dry-combinations-cow
sha256sum "$NATIVE"
ldd "$NATIVE"
~~~

Do not start this native executable by itself as if it were the COW HTTP server. The server supplies its consumed-state protocol, controller and branch ownership.

## Inspect the build commands

The build receipt records actual compile and link argv arrays, working directories, input provenance, dependencies and exit codes. Print readable commands without executing them:

~~~bash
python3 - <<'PY'
import json, shlex
from pathlib import Path
receipt = Path("/home/dflanag3/spatial-artifacts/cow-vision-20261016-v1/vc07-dry-entropy-native-build-v1/build.json")
for step in json.loads(receipt.read_text())["commands"]:
    print("Working directory:", step["cwd"])
    print(shlex.join(step["argv"]))
PY
~~~

These are reproducibility records for an existing build tree. Do not paste them into the validated tree to overwrite the current binary. A fresh rebuild needs a new output directory, every referenced header/object/static library, its source provenance and a new build/profile receipt if its bytes change.

## What Git supplies and what it does not

The private Context COW repository contains the COW server/API, tests and development/build tools. The active server checkout is on branch fix/persistent-text-operation-status-20261019 at commit 6647ae4637cf43ea356cfb1bc799722238212434.

The research profile also refers to generated drivers, earlier native build outputs and model files outside that checkout. A Git clone is therefore not a complete standalone GPU deployment bundle. The private evidence area contains associated artifacts, but do not assume every absolute path in a profile has been restored merely because Git cloned successfully.

For another machine, the remaining installation work is to collect the exact dependency closure, rebuild/link for its GPU and CUDA environment, provision the model/pack, generate an honest location-specific profile and run focused startup/continuation checks. A portable clean-machine installer is unfinished. Do not disable source/model/hash validation or relabel an incompatible checkpoint to bypass that work.

For current use, start the already verified runtime on llm-60 using the server guide.
