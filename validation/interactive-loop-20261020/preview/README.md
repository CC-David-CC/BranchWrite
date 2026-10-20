# Saved-version static preview, dev44

The new /preview command reads the selected WorkspaceVersions commit, hashes its
bounded web blobs and serves an in-memory bundle on 127.0.0.1. No directory
traversal, user transcript, API-key response or model operation is involved.
Relative static assets work; opaque URLs retire on refresh while the port stays
stable for an SSH tunnel. Terminal exit closes the server. Guide09 explains use.
The preview intentionally displays saved versions, not an external editor's
uncommitted changes. Dynamic Python/Node applications are outside this preview.

Executed red/green tests cover exact bytes, private/path rejection, MIME/HEAD,
relative assets, blob hash mismatch, bounded memory, failed refresh retaining the
old view, old URL retirement, stable port, host/absolute-URL aliases, slow-request
shutdown, remote instructions, and real prompt-toolkit command/exit wiring.
The final broader suite passed 404/404 with no skips or source changes during the
run (combined.json). Its initial invocation failed due to missing fixture import
paths and COW_CLI_SCRIPT; initial-environment files retain that failure. The first
implementation's successful suite is retained separately before stable-port work.

Installed final wheel on llm-49 passed a real PTY -> /preview -> HTTP fetch ->
refresh -> /exit journey against the earlier real-Q4 page. Returned bytes exactly
matched that browser-validated page; the original operation/workflow JSON records
remained byte-identical. The port stayed stable, the old URL became 404, and the
listener was gone after exit. No GPU was requested for preview. This wire test
uses urllib, not a claim of a human browser session through a desktop tunnel.
The identical page previously passed desktop/mobile Chromium in
../consumed-pause-live-q4/browser/.

Final wheel SHA256: 4b9f956bfbfef5c973394622ac8cce59d71753cc4fb7243e9bae91f7bcd906e9.
Raw installed-wheel evidence and builds are backed up to private box-git; see
backup.json. No Windows build/test data or public publication. Known cosmetic
rough edge: deliberately aborted malformed HTTP may print a stdlib socket
diagnostic; the request deadline still retires it and the terminal remains usable.
