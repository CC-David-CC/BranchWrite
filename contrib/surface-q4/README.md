# Surface client and private Q4 PCC server (experimental)

This kit connects BranchWrite on an x86-64 Linux laptop to one existing PCC Q4 server over a restricted SSH tunnel. `BW` starts or reuses the server, connects the tunnel and launches the installed BranchWrite client in the current directory. Multiple clients use the server's existing scheduler; they do not share project files or a conversation merely because they share the server.

A Surface Book 2, 8 GB RAM, running CodiServer was tested with Qwen3.8-Flash-Next UD-Q4_K_XL on an RTX PRO 6000 server. From the actual Surface UI the model created and checked a hello-world file, then updated it in a follow-up after a server restart. Two concurrent short sessions used the same server. The portable client was also checked against that live server and the portable gate checked an already-running service. A clean install and cold start using the portable configuration have not yet been tested. These are limited tests, not a general reliability or security certification. The separate Surface 2 GB GPU experiment is documented in the PCC Surface branch; do not assume this remote setup needs that GPU.

The server must already have a **working, pinned PCC model, native build, Python environment and server profile**. Provisioning the 111 GB model, its pack, and the native engine is a substantial separate operation. See PCC's [Linux server setup](https://github.com/CC-David-CC/Private_Context_COW/blob/c59b053bf9799cdb73b799e8913843773770a3e3/docs/CONTEXT-COW-SERVER.md). The validated Q4 server used PCC source `c59b053bf9799cdb73b799e8913843773770a3e3` and a previously prepared Strata pack and profile. The directions below apply to a fresh user-owned server setup; they do not recreate a missing pack or promise that later PCC versions are compatible.

## Prepare the server

Use a dedicated Linux user with a working NVIDIA driver and CUDA environment. Build and prepare Q4 using the linked PCC guide, but create the PCC server **bound to loopback** `127.0.0.1:18099`, not `0.0.0.0`. For example, substitute your real paths in the guide's `cow_server_setup.py` command and add `--host 127.0.0.1 --port 18099 --ram-gib 24 --disk-gib 8`. These are checkpoint budgets, not total memory requirements. An RTX PRO 6000 server used roughly 82 GiB of VRAM in this configuration. Ensure sufficient RAM, disk, power and GPU availability before starting.

Copy `q4-gate` to `~/.local/libexec/branchwrite-q4-gate` on the server and make it executable. Create `~/.local/state/branchwrite-q4/server-launch.json` (directory mode 700, file mode 600) with **absolute paths**:

```json
{
  "source_directory": "/home/SERVERUSER/path/to/Private_Context_COW",
  "server_directory": "/home/SERVERUSER/path/to/prepared-cow-server",
  "python": "/home/SERVERUSER/path/to/server-venv/bin/python"
}
```

The prepared server directory must contain its private `server.json` and `api-key.txt`. The gate starts `tools/cow_server.py` from the selected source directory. Its paths and the prepared server's host, port and API-key path must match. It refuses to start a new server if another NVIDIA compute process is present; an already-running server using the same key is reused. It does not change firewall settings or start a public listener. The server remains running when clients exit; automatic idle shutdown is not implemented.

## Pair a client

Install BranchWrite with its [client instructions](../../docs/LINUX-QUICKSTART.md). On the client, generate a **new dedicated** SSH key (do not reuse or embed a private key in an ISO):

```sh
mkdir -p ~/.ssh ~/.local/state/branchwrite-q4 ~/.local/bin
chmod 700 ~/.ssh ~/.local/state/branchwrite-q4
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_bw_q4 -C branchwrite-q4
```

For unattended startup, the validated setup used an empty passphrase; this gives the account holding the private key access to the restricted gate and port. Protect the client account and use a passphrase/agent instead if appropriate.

Obtain the server's SSH host key fingerprint through a trusted independent channel. Record its verified host key in `~/.ssh/known_hosts_bw_q4`. Do not accept an unverified key merely because a scan returned it. Transfer the new **public** key to the server using an existing trusted administrator connection. In the server account's `~/.ssh/authorized_keys`, append one line consisting of these options followed by that public key, substituting the actual absolute gate path:

```text
restrict,port-forwarding,permitopen="127.0.0.1:18099",command="/home/SERVERUSER/.local/libexec/branchwrite-q4-gate" ssh-ed25519 PUBLIC_KEY_HERE
```

Preserve all existing authorized keys. The forced command permits only the literal SSH command `start`; port forwarding is limited to the specified loopback endpoint. Validate these restrictions for your OpenSSH version and local policy.

Using an existing trusted administrative SSH connection, copy the prepared server's `api-key.txt` to the client's `~/.local/state/branchwrite-q4/api-key.txt` with mode 600. Do not print, commit, email or embed the key in an image. Set up the client's private `~/.local/state/branchwrite-q4/client.json` (mode 600), substituting absolute client paths and the verified server address:

```json
{
  "ssh_target": "SERVERUSER@SERVER_LAN_ADDRESS",
  "ssh_key": "/home/CLIENTUSER/.ssh/id_ed25519_bw_q4",
  "known_hosts": "/home/CLIENTUSER/.ssh/known_hosts_bw_q4",
  "api_key_file": "/home/CLIENTUSER/.local/state/branchwrite-q4/api-key.txt"
}
```

Copy `BW` from this directory to `~/.local/bin/BW` and make it executable. Ensure `~/.local/bin` is on your interactive shell's `PATH`. Then:

```sh
cd ~/your-project
BW
```

The first use may take several minutes to load the model. A connection discovery checks the server identity and capabilities; the first time, BranchWrite writes a private connection file. Open a second project terminal and run `BW` again to reuse the server. Use a disposable project for the first file-creation and follow-up test. Requests send the task and relevant project content to the server; only use a trusted server.

If `BW` cannot connect, check the server is reachable, the verified host key, SSH key restrictions, correct private API key, whether another GPU job is running, and the server log. The first controller prefix can be lengthy. Do not treat the example prompt or successful chat as proof of a complete file workflow. Existing saved sessions remain bound to their original model and execution profile: changing server profiles may require a new session, not silent replay.

For the separate, unqualified laptop-only 2B path, see [LOCAL-MODEL.md](LOCAL-MODEL.md).
