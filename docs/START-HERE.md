# Start here: let's make something with BW

**BW is an app you open inside a project folder and talk to.**

Think of the folder as your workbench. It holds the things you are making,
like a website, a game, or a little program.

## 🏍️ Your first mission: a motorcycle website

You could say:

> “Make me a simple website about motorcycles.”

Then:

> “Make the title bigger. That button doesn’t work—fix it.”

BW lets the AI read files, change them, and run commands to check its work.
You can keep talking, ask questions, and try another idea together.

## Meet the three teammates

- **BW is the app you talk to.** You tell it what you want to make or change.
- **PCC runs the AI brain.** It can run on your computer or another computer.
- **S³ is the practice room and report card.** We use it to test the AI and see
  whether training helped or made something worse.

**You don’t need to use the practice room to chat with BW.**

## You are the project captain

Opening BW in a folder and chatting is already built. What we haven’t fully
proved is that our little trained AI will reliably finish everyday jobs inside
it. It has completed some small tasks, but it still makes mistakes.

The app exists. The little brain inside it still needs supervision. You can
ask it to work on a practice project; we’re not ready to leave it alone managing
an important computer.

For your motorcycle website, open the page, read the words, and try the buttons.
If something is wrong, tell BW what happened. Checking the result is part of
building something together!

## Ready to set up your workbench?

The setup steps below are for Linux. Once BW is installed and its PCC server is
running, you open your project folder in a terminal and launch BW. If setup is
new to you, ask someone comfortable with Linux to help with this part.

PCC's full name is **Private Context COW**. It contains a modified Strata core
and the COW layer. BW manages your task, permitted tools, and saved project files.

You can use one suitable Linux computer for both programs. A separate laptop or
a collection of GPUs is optional. If PCC is remote, keep your project on your
BW client and connect to the chosen server.

## Choose the route for your machine

**[Read the shared PCC/BW guide](https://github.com/CC-David-CC/Private_Context_COW/blob/main/docs/START-HERE.md).**
It covers setup, first use, model context and checkpoints, forks, the new server
features and the research-model testing programme.

| Your setup | Where to start |
| --- | --- |
| **RTX PRO 6000 Blackwell, 96 GB** | The main guided Flash server or a separately configured dense model. The large-model reference had 128 GB system RAM. |
| **RTX 4090, 24 GB** | The smaller Qwen3.5-9B native-adapter route has bounded model-state and BW website checks. Large Flash trials have important memory/latency and coding/recovery limits. |
| **RX 7900 XTX, 24 GB** | The separate dense-model HIP branch has native/HTTP/restart evidence. Main's NVIDIA Flash installer and the latest complete feature stack are not qualified on it. |
| **R730 with two P4s** | Current evidence covers client/CPU/cache-storage roles. Combined PCC/BW GPU inference still needs qualification; the P4s were not used for the LAN test's inference. |
| **Shared/rented A100** | Run the allocated PCC model server and connect BW through an appropriate private connection. The tested BW client was on a separate Linux host. |

The guide explains the exact distinction between a working route and a separate
preview. It does not ask a P4-only or AMD user to install NVIDIA Flash software
and hope that it will work.

## Install current BW

On 64-bit Intel/AMD Linux, install these system tools:

```sh
sudo apt update
sudo apt install -y curl git ca-certificates bubblewrap util-linux
```

Then install BW as your normal user:

```sh
curl -fsSL https://raw.githubusercontent.com/CC-David-CC/BranchWrite/main/install.sh -o "$HOME/branchwrite-install.sh"
BW_REF=main sh "$HOME/branchwrite-install.sh"
```

`BW_REF=main` selects current source. Without it the installer selects its older
frozen preview. An operator can pin a reviewed commit instead. Keep the runtime
versions needed by existing saved work. This documentation change does not
represent a fresh installation test of the new source.

After your selected PCC server is ready:

```sh
mkdir -p ~/my-first-website
cd ~/my-first-website
~/.local/bin/bw
```

Enter PCC's configured address and API key. For the same machine this is commonly
`http://127.0.0.1:8099`; for a remote server use its configured LAN or forwarded
address. The API key is the service's password. Keep it private.

## Try it

Ask for a simple one-file website. Type `/preview` after it finishes, open the
printed link and check the result yourself. Ask for another change in the same
session.

Use `/history website` to find saved Work turn numbers. For example:

- `/explore 1 Make it more playful.` uses the context after turn 1 and current
  files in a separate alternative folder.
- `/edit 1 Make a formal website.` starts before that Work request with the
  corresponding file version.
- `/switch 1` selects that saved turn and restores its matching files, refusing
  conflicting manual edits.

`1` is an example turn number. Read the
[interactive guide](manual/09_INTERACTIVE_SESSION.md) for all controls, safe stop,
reopening and continuation. [Two checked approaches](PARALLEL-EXPLORATION.md) is
a separate explicit workflow option.

## Do the DeepInfra-inspired features help BW?

Yes. They live in PCC's **COW layer**. The server can find reusable computation,
consider cached work when choosing a local worker, transfer compatible checkpoints
between configured peers, separate input and continuation GPU roles, and use an
optional tokenizer for measured long pieces. BW keeps using normal task/model
requests; it does not need its own competing cache manager.

Current BW also checks advertised server capabilities and identities. Completed
results reopen from BW's saved records without a running model server. Update an
older client to obtain these client-side changes; turning on a server option
does not update an installed BW binary.

The options are off by default. Ordinary single-GPU reuse needs no peer; peer
transfer and split GPU roles require the corresponding configured resources.
See the [shared feature explanation and settings](https://github.com/CC-David-CC/Private_Context_COW/blob/main/docs/START-HERE.md#what-the-deepinfra-inspired-features-do).

## What the research testing means

Wen/Wen 1.1 and original Qwen models exercised real mechanics and small workflows:
independent branches, checked state preservation, selected restore/transfer cases,
pause/resume, tokenization equality and read/edit/test/finish tasks.

**This was not a full real-world day of inference load. Feature unification and
testing are still unfinished.** A small mechanics/task pass does not establish
arbitrary project quality, sustained many-user operation, all hardware combinations
or a general throughput improvement. Read the
[research-model explanation and remaining work](https://github.com/CC-David-CC/Private_Context_COW/blob/main/docs/START-HERE.md#why-we-used-a-research-model)
and [BW's recorded integration results](STACK-INTEGRATION.md).
