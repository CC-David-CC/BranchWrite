# Remote admin foundation (RM01), 2026-10-20

Executed: 7 CPU target/receipt admission methods on llm-60 and 8 installed
transport checks over real SSH from llm-49 to its owned QEMU admin01 guest.
This is not a model-facing tool, a CLI deployment journey or a G-gate PASS.
No inference/GPU work was performed by these checks. Stable dev44 remains the
interactive client; this dev45 candidate adds an as-yet-unwired transport module.

The VM was installed onto its blank dedicated 32GiB virtual disk. Initial boot
failed because grub-install reused the supplied ISO's signed GRUB image, whose
embedded configuration searched the ISO layout. The observed repair regenerated
an installed-root EFI image using --no-uefi-secure-boot, only inside this disposable
VM. ISO detached, /dev/vda2 ext4 booted and SSH worked. A subsequent CLEAN guest
reboot changed boot ID, preserved the file SHA and retained the pinned SSH host
key. This is not a power-loss or arbitrary OS installation qualification.
Executed initial installer/repair scripts and failure evidence are retained.

Remote checks: installed-root identity; exact spaces/quotes/literal $HOME/Unicode/
final newline and nonzero exit23; acknowledged remote exit255 distinguished from
SSH transport failure; 4096 exact binary bytes; retained completed receipt across
transport reopen without a second append; unacknowledged intent refused without
executing its command; actual remote deadline; actual output-size limit.
Targets use host-selected literal IP/user/port, pinned known hosts, private files,
root-owned SSH, no agent/config/proxy or inherited API-key environment. Credential
bytes are never sent to the model or copied into the VM. A bounded helper travels
in the SSH command; commands are JSON-framed stdin and exact /bin/bash -c data.

The host must record canonical FrameKernel dispatch before run(). Sidecar intent/
receipt files preserve transport evidence and cannot authorize or advance a BW
workflow. Completed outcomes can be read locally. Pending intent is not resent.
Client death before receipt publication remains indeterminate and needs explicit
inspection; no exactly-once claim. The VM is an administrative capability, so its
services may intentionally persist after a command. A shell cwd is not containment.

Before model-facing exposure: shared target ownership/unknown-effect blocking;
frozen typed tool definitions and grants; saved-launch/CLI configuration; exact
local-file upload with remote preimage checks; Kernel receipt reconciliation; then
real Q4 coding/install/deploy/edit/redeploy and stop/recovery journeys. Existing
local sandbox isolation must remain unchanged. See ADMIN-INTEGRATION-HANDOFF.md.
