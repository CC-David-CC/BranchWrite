# BranchWrite: start here

BranchWrite helps you make and change files by talking to a model.
You use two computers:

- **Server:** runs Context COW and the model. Your operator sets it up.
- **Client:** runs BranchWrite. This is the computer where you keep your project.

You do not need a GPU or model download on the client.

## Before you start

This preview supports 64-bit Intel/AMD Linux. These steps use Ubuntu or Debian.
Ask your operator for the server address and API key. An API key is a password
for this service. Do not put it in a project file or screenshot.

Open Terminal. Install the small system tools:

```sh
sudo apt update
sudo apt install -y curl git ca-certificates bubblewrap util-linux
```

The computer may ask for your Linux password. Letters do not appear as you type.
That is normal. Press Enter when you finish.

## Install BranchWrite

The tested download command will be added after the fresh-VM campaign.
Do not use a copied research environment as an installation.

The installer downloads its own Python and packages. It does not replace the
computer's Python. You do not need to activate a virtual environment.
A virtual environment is a separate place for a program's Python packages.

## Choose a project folder

For a new project:

```sh
mkdir -p ~/my-first-website
cd ~/my-first-website
~/.local/bin/bw
```

For an existing project, open Terminal in that folder and run
`~/.local/bin/bw`. That full path works even if typing `bw` is not set up yet.

## Connect

At **Server address**, type the address your operator gave you, for example
`http://10.0.7.68:8099`. Use the server computer's LAN address.
`127.0.0.1` means this computer; it does not mean another computer on your LAN.

At **API key**, paste your key and press Enter. The key stays in memory for this
session. It is not saved by default.

## Ask for a change

Try:

> Make a pretty one-page website about dogs. Use one HTML file. Make it work on
> a phone. Add a button that shows a friendly greeting. Do not download anything.

Then ask:

> Make the dog names bold. Keep the greeting button working.

BranchWrite works in a separate copy. Review the result before publishing it
back to your project. A successful command means its chosen checks passed;
it does not prove every part of a website is correct.

## While it works

You can add information, queue the next change, or stop the current turn.
The fresh-install campaign will verify these controls and add the exact keys.
A stopped run and an uncertain server reply must be resumed with their saved
identity, rather than submitting the same operation as unrelated new work.

## What stays on each computer?

Your project and BW's saved workflow are on the client. The server receives
the project content needed by the task and keeps the model's context.
Only use a server you trust. Keep project secrets out of the selected folder.

## Updating

Installations use separate versioned runtime folders. Keep old runtime folders
while you have saved work that uses them. Never delete an old runtime just to
make an update appear successful.
