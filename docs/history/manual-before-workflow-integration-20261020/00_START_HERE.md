# Run Context COW and BranchWrite yourself

BranchWrite is a command-line coding agent. Run it in a Linux project folder,
then describe the task. Context COW owns model histories and saved computation;
the website preview is only for viewing an HTML result.

For the current responsive terminal, start with [Interactive session](09_INTERACTIVE_SESSION.md).
Run `branchwrite` in the folder you want to work on. You can keep typing while it works.
Work mode updates that folder and retains saved versions; Plan and Chat keep files unchanged.
The guides below include older one-task installations and their separate-copy behavior.
Use `branchwrite start` only when you intentionally want that older flow.

Start with [First task](06_FIRST_TASK.md). Use the tested client pinned in
[Development handoff](07_DEVELOPMENT_HANDOFF.md). Keep unfinished runs on their
original installation. Windows is the SSH steering terminal.

You need two running programs: Context COW on llm-60 supplies the model, and BranchWrite on llm-49 edits an owned copy of your project. The audit harness is for development tests; you do not run it for ordinary coding.

| Read this | Purpose |
|---|---|
| [Your first coding task](08_FRIEND_FIRST_RUN.md) | Install the CLI and run a small coding task when the server operator has already prepared the server and given you a key. |
| [Server setup](01_SERVER_SETUP.md) | Start the existing verified Q8 runtime on llm-60. |
| [Client install and connection](02_BRANCHWRITE_SETUP.md) | Install BranchWrite on a Linux client and connect it through SSH. |
| [First task](06_FIRST_TASK.md) | Start in a project folder, approve file access, run a check, and make a safe copy of the result. |
| [Native engine inventory](03_NATIVE_RUNTIME.md) | Understand the native engine, model files and fresh-machine installation limits. |
| [Talk to the model](07_USER_CHAT.md) | Keep one current user-conversation tip, inspect history, and recover an interrupted reply. |
| [Create or edit an HTML site](04_HTML_WORKFLOW.md) | Give BranchWrite a task without another agent. Review and use the result. |
| [Project handoff](05_HANDOFF.md) | Exact locations, Git branches, current evidence and unfinished work. |

Start the server first, then open the client tunnel, then run BranchWrite. Keep the server and tunnel terminals open while coding.

A **terminal** is the window in which you type commands. **SSH** opens a terminal on another machine. A Python **virtual environment**, or **venv**, is a directory containing a separate Python command and this app's installed package. It does not contain the model.

All commands in these guides run in Linux Bash unless a block says Windows PowerShell. Stop if a command fails; read the reason before continuing. Do not replace a sandbox error with unsandboxed execution.

## Earlier native-tested locations

- Authoritative client source on **llm-49**: /home/dflanag3/src/branchwrite-model-reconciliation-20261019
- These guides on **llm-49**: /home/dflanag3/src/branchwrite-model-reconciliation-20261019/docs/manual
- Installed client on **llm-49**: /home/dflanag3/spatial-artifacts/branchwrite-dev28-package-20261019-v1/installed-check/venv/bin/branchwrite
- Server source on **llm-60**: /home/dflanag3/src/context-cow-history-counts-20261019
- Private client Git: box-git:/srv/data/git/BranchWrite.git
- Private server Git: box-git:/srv/data/git/private_context_cow.git

The Windows folders C:\Users\dflanag3\Documents\fleet\branchwrite and C:\Users\dflanag3\Documents\fleet\Public_Context_COW exist, but are older checkouts. They are not the current Linux installations. No new test artifacts or model files were copied to Windows.

To read the start guide from Windows PowerShell:

~~~powershell
ssh llm-49 "cat /home/dflanag3/src/branchwrite-model-reconciliation-20261019/docs/manual/00_START_HERE.md"
~~~

If you want your own local reading copy, you can explicitly download only these small guides:

~~~powershell
scp -r llm-49:/home/dflanag3/src/branchwrite-model-reconciliation-20261019/docs/manual "$HOME/Documents/fleet/branchwrite-manual"
~~~

This download is optional. It does not install the client on Windows.

## What is ready

Dev24 completed two real-Q8 coding tasks, reference refresh, review/export/apply and completed offline reopen. It has bounded functional evidence, not universal coding reliability or full G1?G5 certification. The development server was shut down after testing; these instructions start your own foreground instance. The ordinary chat server stays off.
