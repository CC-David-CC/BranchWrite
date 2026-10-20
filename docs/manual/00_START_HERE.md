# Use Context COW and BranchWrite

BranchWrite is the Linux terminal app you talk to. It works on the project folder where you start it. Context COW is the remote model server and owns saved model computation. The workflow harness checks what tools and files actually did. A .bw file is a workflow recipe, not a model checkpoint.

1. Your operator prepares the COW server and gives you its address and an API key.
2. Follow [Install and connect](02_BRANCHWRITE_SETUP.md).
3. Start branchwrite in a project folder and ask for the change in ordinary words.
4. Keep talking after it finishes. Use /preview to see saved HTML, PDF or text. Use /history and /switch to return to a saved version.

[Interactive controls](09_INTERACTIVE_SESSION.md) explains steering, bundled queued messages, Plan/Work/Chat/Aside, editing a request, exploring another file copy and recovery. [Example prompts](../../examples/prompts/README.md) gives one plain-text request per workflow with exact executed results. [PDF documents](11_PDF_DOCUMENTS.md) explains actual page review. [Remote administration](10_REMOTE_ADMIN.md) explains explicitly granted hosts. [CAD and Blender](../../SPATIAL-CREATION-GUIDE.md) explains the operator-prepared native runtimes.

[CURRENT_STATE.md](../../CURRENT_STATE.md) is the authoritative current machine/version/status map. [Development handoff](07_DEVELOPMENT_HANDOFF.md) links evidence and remaining work. Older manuals are archived in ../history/ for their original installations; do not choose an old dev24/dev30 package just because an archived page mentions it.

Windows is the SSH steering terminal. Builds, execution and outputs stay on Linux. Current client source: llm-49:/home/dflanag3/src/branchwrite-documents-20261020. Private Git: box-git:/srv/data/git/BranchWrite.git. The server is separately tracked in private_context_cow.git. No GitHub publication is authorized by this guide.
