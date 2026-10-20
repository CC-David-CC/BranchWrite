# Start BranchWrite, talk, then make a small website

Your operator runs the Context COW model server. You install the small
BranchWrite client on a Linux computer and use the server address and API key
that your operator gives you. The current private build is a research prototype.

## Install once

Open a terminal. A terminal is an app where you type commands. On Ubuntu or
Debian, install Python and the tool that keeps coding commands in their allowed
workspace:

```bash
sudo apt-get update
sudo apt-get install python3 python3-venv bubblewrap util-linux
python3 -m venv "$HOME/branchwrite/venv"
```

A **virtual environment** is a folder that keeps this app's Python packages
separate from your other programs. It is not another computer.

Your operator supplies the private wheel file and its SHA-256 checksum. Check
that checksum with `sha256sum /path/to/the/wheel.whl`. Replace the example path
below with that file's actual path:

```bash
"$HOME/branchwrite/venv/bin/python" -m pip install /path/to/the/wheel.whl
"$HOME/branchwrite/venv/bin/branchwrite" doctor
```

`doctor` checks the local coding sandbox. If a check fails, give the error to your
operator. Do not turn off the sandbox to get past it. You do not need to install
a model or GPU driver on the client computer.

## Open your project

For a new practice project:

```bash
mkdir -p "$HOME/projects/my-first-page"
cd "$HOME/projects/my-first-page"
"$HOME/branchwrite/venv/bin/branchwrite"
```

For an existing project, open a terminal in its folder and run the same command.
BranchWrite uses that current folder. It works in a separate copy and shows you
where to find the result.

The startup banner names the **client machine**. If you opened BranchWrite over
SSH from Windows, the files are on that remote Linux client, not in Windows or
WSL. Its Linux path will not open in Windows File Explorer. Use the operator's
private preview link or copy the reviewed project back to your computer. The
Windows desktop currently steers this installation; it is not the coding client.

The first run asks for the COW server address and then the API key. Paste the
exact address your operator supplies. The key is hidden while you type it and
stays in memory for this session. Server settings are saved. The API key is saved
only if you explicitly launch with `--save-api`. Use only your trusted operator's
server; project contents used for a coding task go to that server.

## Talk first, if you want

At `What would you like changed?`, type:

```text
/chat
```

Then type a question, for example:

```text
I want a simple website with a blue heading and a button. What should it say?
```

Conversation mode sends your messages to COW and saves the conversation there.
It does not read project files or run coding tools. To open directly in this
mode next time, use:

```bash
"$HOME/branchwrite/venv/bin/branchwrite" talk
```

When you are ready for coding, type:

```text
/code Create index.html for My First BranchWrite Page. Use a blue heading, a short welcome paragraph, and a Say hello button that displays Hello, David! Make it work on phones. Use one file and no downloads.
```

That starts a separate coding workflow from the exact saved conversation point.
Later conversation changes cannot silently change the task already admitted.
BW chooses the project files and checks it needs. You do not have to name every
file in advance. The project folder is its scope; this does not grant access to
other folders or credentials.

You can also type the coding task directly at the original startup prompt,
without entering conversation mode.

## Finish or return later

After coding, BW reports whether its checks passed and lists the changed files.
Review them. If you want the separate result folder, type `YES` when asked.
Your original project folder remains unchanged. A passing check is evidence for
that check; it is not a guarantee that every possible website behavior is correct.

In conversation mode:

- `/exit` leaves the conversation and prints a command to resume it.
- `/continue` finishes an answer paused at its token budget.
- `/history` reads the saved conversation from COW.
- `/status` shows pending work and the saved tip.
- `/reconcile` recovers a submitted operation after a disconnect, using its
  original operation ID.

Use the exact printed `branchwrite talk --state ...` command to resume the same
conversation. Do not start a new operation to guess whether an old one completed.
Coding still has its own saved run and `branchwrite resume ...` recovery command.
See [saved receipts and recovery](06_RECEIPTS_AND_RECOVERY.md) for the details.

This first terminal loop waits for each answer before taking more input. The
lower-level `chat queue` and `chat stop-add` commands support queued follow-ups
and stop-and-amend from another terminal. Integrating those into one interactive
terminal remains separate work. Conversation-to-coding ends this chat session;
it does not yet automatically feed the coding results back into the conversation.
