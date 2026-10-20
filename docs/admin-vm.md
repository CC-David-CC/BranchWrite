# Disposable Linux admin fixture

This VM lets BranchWrite test real software installation, service management and
file deployment alongside ordinary coding work. It is separate from inference.
A listening port is not proof of a working guest: guest login and service checks
must run after installation.

## Current placement

- QEMU host: llm-49 (r4090), under dflanag3, KVM available.
- Runtime: /home/dflanag3/.local/share/bw-vm/admin01 (0700).
- Script and host evidence: /home/dflanag3/spatial-artifacts/branchwrite-vm-20261020.
- Four virtual CPUs, 4 GiB RAM, 32 GiB sparse qcow2 disk.
- SSH forward: 127.0.0.1:22220 on llm-49 to guest port 22.
- Web forward: 127.0.0.1:18080 on llm-49 to guest port 80.
- Serial log and QMP/VNC Unix sockets stay inside the private runtime directory.
- No host filesystem, SSH agent, GPU or block device is passed into the guest.
- User-mode NAT allows outbound networking for package installation. It is not
  an outbound firewall: do not treat this as permission to administer other LAN
  hosts. Later BW grants must name this fixture as the only admin target.

## Prepare and check

On llm-49, install the host packages once:

    sudo apt-get install --no-install-recommends qemu-system-x86 qemu-utils ovmf

Run the checked-in helper on that host:

    python3 tools/admin_vm.py prepare
    python3 tools/admin_vm.py check

The check starts a paused KVM machine with a disposable disk overlay, queries
real QEMU state and listeners, then quits and verifies process exit. It does not
boot a guest or validate SSH into one. The generated guest-key is for this
fixture only. Never commit it, an installer credential or the VM disk.

## Install when the owner's ISO is ready

Owner said the ISO is being built on a5500's Desktop, expected after
2026-10-20 10:13:52 UTC. Wait for the completed file; preserve its original bytes
and record SHA-256 on both ends of transfer. Do not copy a partial download.
The image is expected to contain a maint account and preinstalled SSH keys;
verify the actual guest configuration instead of assuming it.

    python3 tools/admin_vm.py start --iso /absolute/path/to/completed.iso
    python3 tools/admin_vm.py status

Installer interaction depends on the supplied ISO. Configure its boot/installer
only after inspecting that image. QMP and VNC are private Unix sockets, not LAN
listeners. To request clean shutdown:

    python3 tools/admin_vm.py powerdown

Check that the guest really exits. The `quit` action is a hard power-off of this
owned fixture; use it only for deliberate crash tests or a stuck disposable VM.

## Initial SSH and deployment acceptance

1. Pin the guest SSH host key in a fixture-specific known_hosts file. This run
   used first-use discovery on the private loopback forward after verifying its
   owning QEMU PID, then enforced StrictHostKeyChecking=yes. Console verification
   is another option. Do not disable host-key checking.
2. Try an installed authorized key first. If a bootstrap credential is needed,
   use it interactively without echoing or recording it. Do not put credentials
   in command arguments, shell history, evidence or Git.
3. Log in as maint via llm-49's loopback SSH forward. Check the guest hostname,
   account, OS, filesystem and virtualization identity. Confirm it is the guest.
4. Exercise SSH success and nonzero exit status, then transfer a small file with
   spaces and Unicode in its name. Compare exact bytes and delete that test file.
5. Confirm sudo scope inside the guest. Install/start nginx there, copy a small
   test site to the guest web directory, and fetch it through port 18080.
6. Shut down cleanly. Preserve an installed base image and use per-trial qcow2
   overlays. Never snapshot a running filesystem as if it were a clean base.
7. Only then grant BW this exact target and interleave: create site, put it on
   the test server, change wording, redeploy, verify served content, then recover
   from a failed deployment. Independently inspect files, command status and HTTP.

Current limitation: host preparation and KVM proof do not establish BranchWrite
admin integration. That still needs the real guest and the bounded remote tool.

QEMU option reference: https://www.qemu.org/docs/master/system/invocation.html
QMP reference: https://www.qemu.org/docs/master/interop/qmp-spec.html

## Executed results and replacement watch

The original CodiServer-VM-light-amd64.iso is 2,074,392,576 bytes. SHA-256:
205cbe604ffda46169dedd62436d3c21e0efa7fec6bb37f7740e0e29aae7665d.
Direct LAN copy from a5500 (10.0.7.87) to llm-49 took20.30s at97.45MiB/s.
The first Windows-relayed attempt managed2.24MiB/s and was stopped; its partial
file was deleted. Future bulk transfers must use direct Linux-to-Linux SSH.
The owner's standing permission allows configuring LAN SSH keys. llm-49's
fleet key is now authorized on a5500 from10.0.7.95, with forwarding/PTY disabled.

Original image: BIOS live boot passed, hostname codiserver-vm, kernel
7.0.14-codiserver-base. Five checks passed: guest identity, public-key SSH,
sudo, exact nonzero command status23, and SCP byte roundtrip. The16,394-byte
fixture covered spaces/Unicode in its name, arbitrary binary bytes and a final
newline. Its temporary files were removed. QEMU's private VNC console returned
RFB003.008 and a screenshot showed the graphical login screen. Guest desktop
sharing is an on-demand helper, not an observed automatically running listener.

This is a live overlay root with about2GiB writable RAM; it is not an installed
persistent guest. Do not claim restart/persistence or installation coverage.
The owner reported a FAT-formatting problem in the UEFI installer and is building
a replacement. Do not test installation using the known-bad old installer.

A one-shot monitor runs on llm-49 (initialPID2416878). It polls a5500's Desktop
for new/replaced regular .iso files, requires stable size/mtime/inode for60s,
checks the SHA-256 sidecar when present, copies directly over the LAN, rechecks
source stability and copied bytes, requests clean shutdown of this exact VM,
and boots the replacement with OVMF UEFI. It then stops monitoring so it cannot
silently reboot a later admin workload. It never performs an installation.
Read its current state instead of trusting the original PID:

    cat /home/dflanag3/spatial-artifacts/branchwrite-vm-20261020/iso-watch-status.json

After replacement: recheck guest identity and SSH host key, authorize the dedicated
test public key if needed, rerun SSH/SCP, then test the actual UEFI/FAT installation
on the owned blank32GiB virtual disk. Preserve the old image/result as evidence.
Credentials, SSH private keys, disks and ISO files are never part of Git evidence.


## Replacement image switched and checked

The one-shot monitor detected and switched to the rebuilt image. It is
2,075,211,776 bytes; SHA-256
`a432129ef6d19441454b62b0e88a36c7488e9ad148a204b03ce80164d0c2753c`.
The direct-copy-plus-verification phase took20.28s. The old guest shut down
cleanly. The replacement uses OVMF UEFI with KVM enabled; its observed QEMU
PID was2419152. The monitor exited successfully after this one switch.

Inside the replacement guest, `/sys/firmware/efi` exists, kernel remains
7.0.14-codiserver-base, and Python is3.14.4. Both `/usr/sbin/mkfs.fat` and
`/usr/sbin/fsck.fat` are present. Actual FAT32 formatting and a read-only
filesystem check passed on a disposable128MiB image, which was then removed.
This establishes that the formatter executes successfully in the new guest;
the actual UEFI boot-partition installation and disk reboot remain untested.

Public-key SSH, passwordless sudo, exact exit23 propagation, and a16,395-byte
SCP roundtrip passed. The roundtrip included arbitrary binary bytes, spaces,
Unicode U+00E9 in the filename, and a final newline. The first filename probe
was accidentally converted to ASCII by the steering-shell pipe; that narrower
byte-transfer result is retained separately. The corrected probe used an ASCII
Python escape and verified the exact filename on the guest before copying back.

The rebuilt guest has a new host key. After checking the new QEMU PID owned
the private loopback forward, first-use discovery pinned it in
`/home/dflanag3/.local/share/bw-vm/admin01/known_hosts-a432129ef6d1`.
Subsequent connections enforced strict checking. This was not console-based
cryptographic verification. The dedicated test public key was added through an
interactive bootstrap login; no password or private key entered Git or evidence.

Compact evidence is in
`validation/interactive-loop-20261020/vm-replacement-uefi/`.
The active root is still a live overlay. The owned blank32GiB virtio disk is
`/dev/vda` inside this guest. Inspect the supplied Ubiquity installer before
installing; no install or nginx deployment has yet run on the replacement.
