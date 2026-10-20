# llm-49 browser deployment evidence

These are the exact reviewed policy files used for the passing browser9/9 and
cross-host H01 run. They are specific to this host's installed executable paths.
Do not copy them blindly onto another machine or after upgrading Python/Node/
Chromium. Compare fingerprints.json and the source paths first. No system-wide
userns sysctl is changed; no sandbox is disabled. The vendor bwrap profile remains.

The local priority rules override executable transition selection only at the
listed project runtime paths. The named worker permits sys_admin/sys_chroot inside
the existing user namespace for Chromium's nested sandbox. Other capabilities
remain denied by default. An ordinary system-Python child still inherits
unpriv_bwrap and fails nested UID mapping. This authorizes a narrow host runtime
arrangement, not adversarial host security or universal platform compatibility.
Files at the allowed executable paths must remain trusted; the AppArmor rule is
path-based, not a cryptographic executable allowlist. Recorded hashes permit
review of changes; the policy itself does not enforce those hashes.

Install only when the destination files are absent or already byte-identical.
If local/bwrap-userns-restrict already contains other settings, review a combined
file manually. Never overwrite another application's local policy. From this dir:

    sudo install -m 0644 worker.profile /etc/apparmor.d/branchwrite-browser-worker
    sudo install -m 0644 bwrap-local.rules /etc/apparmor.d/local/bwrap-userns-restrict
    sudo apparmor_parser -r /etc/apparmor.d/branchwrite-browser-worker
    sudo apparmor_parser -r /etc/apparmor.d/bwrap-userns-restrict

Client dependencies used: Python3.14.4 venv, Playwright1.64.0, Pillow13.0.0,
matching downloaded Chromium156.0.8078.4, and Ubuntu libasound2t64. Failed earlier
library/policy attempts remain in the private raw evidence. The exact-browser-only
AppArmor profile from the initial attempt was removed after it proved ineffective.

Rerun tests/test_browser_capture.py and tests/test_capture_cli.py with the actual
browser executable in BW_BROWSER_EXECUTABLE. Expected current counts:9 and8, no
skips. Then rerun actual cross-host H01 before claiming live client qualification.
Full release/platform/sanitizer/soak campaigns remain outstanding.
