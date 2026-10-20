# Installed remote administration and bounded capture

Executed 2026-10-20, dev49. One host client (llm-49) targets its owned persistent
Ubuntu VM through pinned SSH. No GPU inference is required by these tests.

The prior real-Q4 autonomous admin pilot found a genuine helper defect: our global
RLIMIT_FSIZE intended to bound stdout also prevented apt from writing package
indices. The model diagnosed it and installed a Python static server instead.
That observed workaround is preserved, not relabelled as successful nginx install.

Red test: a legitimate2MiB file write fails with Errno27 on the old helper.
Fix: bounded in-memory selector capture, max1MiB per stdout/stderr stream, with
an operation deadline. No global command-file limit. Five subprocess checks pass:
large file, binary/nonzero exit, each output stream limit, timeout, simultaneous
streams. Timeout/retirement errors propagate as indeterminate effects.

Current combined CPU/client/HTTP-fixture suite:439/439, no failures/errors/skips,
107.739s, source unchanged. Actual installed dev49 CLI/Interpreter/Kernel/SSH/VM:
11 workflow regressions PASS, including original receipt reconciliation without
reexecution;2 installation checks PASS (large file and real apt/nginx install).
Independent host HTTP returned200 and nginx welcome content. Two additional real
SSH checks exercised output-limit and timeout on unprivileged same-UID processes.

The VM now runs nginx on port80. The preceding Python welcome-web service was
stopped to free that port; its recorded pilot result remains intact. The test
explicitly stops that owned service and does not represent a new autonomous run.
No reboot qualification is claimed. Privileged/mixed-UID cancellation, cross-host
target coordination and exact file upload/publication remain outstanding.

Installed wheel SHA-256:
fab6d2ccfe53265a62f8e74773161c42e49fe537a8b3f1f56b86fb971dd7c697

All code/evidence stays on Linux and private LAN Git. No G1-G5 certification claim.
