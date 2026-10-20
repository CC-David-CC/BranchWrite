# Install the private BranchWrite client

Use [Install and connect](manual/02_BRANCHWRITE_SETUP.md) for the current client, then [the interactive guide](manual/09_INTERACTIVE_SESSION.md). [CURRENT_STATE.md](../CURRENT_STATE.md) records the installed version and server actually in use. Older install versions remain in docs/history/ and CLIENT_INSTALL_HISTORY.md for their original saved workflows.

The current package includes the UI, Pillow, ReportLab, PDFium and PDF reader dependencies. Install dependencies at setup time, not inside model tasks. Initial setup compiles bytecode before runtime admission; do not install into an environment with unfinished work.
