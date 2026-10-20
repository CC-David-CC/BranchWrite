#!/bin/sh
# Linux client only. The model and Context COW run on the other computer.
set -eu
umask 077
if [ "$(uname -s)" != Linux ] || [ "$(uname -m)" != x86_64 ]; then
  echo "This preview installer needs 64-bit Intel/AMD Linux." >&2
  exit 1
fi
for tool in curl git tar sha256sum flock bwrap unshare; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "Missing: $tool. On Ubuntu/Debian, run:" >&2
    echo "  sudo apt update && sudo apt install -y curl git ca-certificates bubblewrap util-linux" >&2
    echo "Then run this installer again." >&2
    exit 1
  fi
done
if [ "$(id -u)" = 0 ]; then
  echo "Run this installer as your normal user, without sudo." >&2
  exit 1
fi
BW_HOME=${BW_HOME:-"$HOME/.local/share/branchwrite"}
BW_BIN=${BW_BIN:-"$HOME/.local/bin"}
BW_REF=${BW_REF:-"lan-preview-2026-10-20"}
mkdir -p "$BW_HOME"
exec 9>"$BW_HOME/install.lock"
flock -n 9 || { echo "Another BranchWrite installation is running." >&2; exit 1; }
stage=$(mktemp -d "$BW_HOME/setup.XXXXXXXX")
echo "Installing BranchWrite. Setup files: $stage"
uv_url=https://github.com/astral-sh/uv/releases/download/0.13.4/uv-x86_64-unknown-linux-gnu.tar.gz
curl --fail --location --retry 3 --connect-timeout 20 "$uv_url" -o "$stage/uv.tar.gz"
printf '%s  %s
' 2b428396f12572d4429cf210ca234dd599a33b3af0958a4d5ed569d63e3f344f "$stage/uv.tar.gz" | sha256sum --check --status
tar -xzf "$stage/uv.tar.gz" -C "$stage"
uv="$stage/uv-x86_64-unknown-linux-gnu/uv"
"$uv" --no-config python install 3.12.15 --install-dir "$stage/python" --no-bin --no-registry
python=$(UV_PYTHON_INSTALL_DIR="$stage/python" "$uv" --no-config python find --managed-python --no-project 3.12.15)
GIT_TERMINAL_PROMPT=0 git -c init.defaultBranch=main init -q "$stage/source"
GIT_TERMINAL_PROMPT=0 git -C "$stage/source" fetch --depth 1 https://github.com/CC-David-CC/BranchWrite.git "$BW_REF"
git -C "$stage/source" checkout -q --detach FETCH_HEAD
"$python" -I -B "$stage/source/tools/bootstrap_client.py" --source "$stage/source" --source-python "$python" --uv "$uv" --home "$BW_HOME" --bin "$BW_BIN"
case ":$PATH:" in
  *":$BW_BIN:"*) echo "Type bw in your project folder to begin." ;;
  *) printf 'For this terminal, run: export PATH="%s:$PATH"\n' "$BW_BIN" ;;
esac
