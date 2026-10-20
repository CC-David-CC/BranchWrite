# First task with BranchWrite

Your server operator gives you a COW server address and an API key. BranchWrite runs on your Linux client. The model stays on the server.

## Set the server address

After installing the client, run:

```sh
branchwrite connect http://127.0.0.1:18099
```

Use the address your operator gave you. This example assumes an SSH tunnel.
Paste the key when asked. The terminal hides it. BW reads the model settings
from COW, so you do not type model hashes.

Settings go in ~/.config/branchwrite by default. connection.json contains server
and model identities. The API key is NOT saved by default. BW keeps a prompted
key in memory for the current run. A later run asks again, or reads BW_COW_API_KEY.
To explicitly save the key, run `branchwrite connect SERVER_ADDRESS --save-api`,
`branchwrite start --save-api`, or `branchwrite --save-api`. This writes a private
credentials.json outside the project. Reconnecting without --save-api removes
a previously saved key. Keep connection and credential files outside Git.
BW_COW_CONNECTION can select an operator-provided connection file.
BW_COW_API_KEY overrides the saved key for that process.

If the server is off, setup says so. Setup does not start it or submit a coding
task. An older COW server needs the discovery update or an explicit connection
file from its operator.

## Open your project

```sh
cd ~/projects/my-site
branchwrite
```

The ~ means your home folder. BW prints the project folder. If connection setup
is missing, it asks for the address and key here.

Describe the task in ordinary words. For example:
"Make the garden club homepage readable on a phone. Keep the green heading."

That is all the setup for a task. BW can read, create and edit files throughout
this project, including filenames it chooses later. You do not need to predict
which files will change or supply a test command. BW inspects the project and
chooses checks. File contents used for the task go to your configured server.

The project boundary still applies. Files outside it, links and Git's internal
administration are unavailable. Commands run in the existing isolated terminal;
use file tools for persistent edits. Network access is not granted by startup.

## Use or resume the result

BW edits a separate work copy and runs its chosen checks. Once both those checks
and the finish report succeed, it lists changes. Type yes when asked to put the
result in a new folder beside your original. Open the printed folder to use it.

For unfinished work, keep the saved run folder and use:

```sh
branchwrite resume /path/printed/by/branchwrite
```

An explicitly saved key is used only for the run's original connection and model profile.
Without a saved key, supply BW_COW_API_KEY when using the low-level resume command.
Keep the version used to start unfinished work. If an operation is unresolved,
follow the printed status/reconciliation instructions before retrying. Unverified
work returns a nonzero exit code.

## Roles and limits

- BranchWrite owns coding workflow, file tools, permissions, checks and review.
- Context COW owns model histories, controllers, branches and RAM/disk checkpoints.
- Strata performs model inference.
- The harness checks these pieces. Ordinary users do not run it.

Dev33 removes the filename and check-command questionnaires. A finish request
needs actual successful check receipts for the current files. A failed check or
an edit after checking cannot be counted as a pass. Model-selected checks are
useful evidence, not a guarantee that every requirement was tested.

This is still a prototype. Review/application uses a separate copy. Conversational
follow-ups and guarded application into the chosen working folder remain part
of the standalone-agent goal. The API key still stays in memory unless you
explicitly use --save-api.

## If you want to discuss the idea before coding

Type `/chat` at the task prompt, or start with `branchwrite talk`. Ask questions
normally. When you want edits, use `/code YOUR TASK`. The coding run starts from
the exact saved conversation point and gets a separate work branch. `/exit`
prints a resume command; `/continue` finishes an answer paused at its budget.
See [the first-run guide](08_FRIEND_FIRST_RUN.md) for a complete example.
