# Keep talking while BranchWrite works

## For the person using it

This development interface runs in your Linux project folder. It uses the saved
server connection and asks for the key if needed. The key stays in memory unless
you explicitly choose `--save-api`. Your operator must already have started COW.

    cd ~/my-project
    /full/path/to/branchwrite

The latest installed client is on llm-49:

    source /home/dflanag3/spatial-artifacts/branchwrite-dev44-preview-20261020/venv/bin/activate
    cd ~/my-project
    branchwrite

Activation makes the short command available in this terminal. It does not move
your files or the model. Supply the operator's key when prompted; keep it private.

Describe your goal in ordinary words. Work mode chooses files and checks, then
updates this folder. Saved versions remain available. Project content used for
the task is sent to your configured model server. The model's chosen checks are
useful evidence, not a guarantee that the result satisfies every requirement.

- Enter sends a request. While work is active, Enter steers at its next safe boundary.
- Tab queues a followup. Several queued notes become one next request, in order.
- Esc asks to stop and keeps your draft. With a compatible consumed-pause COW
  server, an active model request saves at its next consumed-token boundary.
  Wait for the safe-boundary message. Tools still settle their existing step;
  older servers visibly fall back to waiting for the whole model step.
- `/plan` inspects and advises without changing files. `/work` permits editing.
- `/chat` discusses the project. `/aside QUESTION` answers without moving the main tip.
- `/history WORDS` searches saved requests. Its numbers are stable within this session.
- In Work mode, `/edit 2 NEW REQUEST` replaces request2 using the context and files
  from before it. Omit the number to edit the last completed Work request.
- `/explore 2 NEW REQUEST` uses the context after turn2 with your current files,
  in a separate folder. Your selected folder stays unchanged during the trial.
- `/switch 2` selects turn2 and restores its matching file version. A conflicting
  manual edit stops restoration instead of silently overwriting that edit.
- `/preview` gives you a browser link to the selected saved website. Use `/preview page.html`
  if your project has several pages. It uses the last saved file version.
- `/continue` resumes a paused or unsettled original workflow. `/exit` settles and exits.

Reopen the same project with the same connection to recover its session. A custom
`--state /absolute/path` selects that exact saved session. Unsettled effects require
explicit `/continue`; restarting does not silently repeat an unknown operation.

The no-argument launcher now opens this responsive session. `branchwrite session`
is an equivalent explicit spelling. `branchwrite start` keeps the earlier one-task
wizard for reproducing old runs. The resulting files and preview are on the client
machine shown at startup, which can be different from the model server.
Edit/explore currently target saved Work requests; discussion editing remains future work.

### Look at your website

1. Wait until BranchWrite has saved the page.
2. Type `/preview` and press Enter.
3. Open the link that BranchWrite prints. Keep BranchWrite running.
4. After another saved change or a branch switch, type `/preview` again and open
   the new link. It shows the selected saved version, including a separate exploration.

If you connected to the client with SSH, its `127.0.0.1` address belongs to the
remote client. BranchWrite prints one exact `ssh -N -L ...` command. Open a second
terminal on your own computer, run that command, and leave it running. Then open
the printed browser link on your own computer. The same connection works when
you refresh the preview during that BranchWrite session. Close that second
terminal when finished. You do not need to copy Linux paths into File Explorer.

This first preview handles saved static HTML, CSS, JavaScript, pictures and fonts.
It is not an application server for Python/Node backends. The bundle is limited
to 65 web files, 4 MiB each and 20 MiB total; an oversized bundle reports a clear
error. Hidden files and non-web source/configuration files are excluded. If you
change files in another editor, the preview continues to show BranchWrite's last
saved version until a new version is saved. Closing BranchWrite closes preview.

## For the agent maintaining it

BranchWrite Terminal presents input and progress. SessionService owns one worker;
SessionLedger uses FrameKernel/RuntimeLog for admitted operations. The inbox is
only unsent input. Context COW owns canonical model history, controller state,
branch references and optional RAM/disk checkpoints. Strata runs the model.
The audit harness observes outcomes and independently checks files/browser behavior.

Version controls pin the exact saved turn before acknowledging admission. Their
original text and target survive restart. Git stores file versions with opaque COW
references, not another conversation transcript. Edit selects the preceding boundary;
explore intentionally combines independent context/file bases and supplies fresh file
facts; switch performs no model inference. Normal followups fork exact stored tips.
The prepared prefix before the first request is read from its existing workflow,
so first-request editing can reuse it rather than create a replacement bootstrap.
COW may explicitly report recomputation if an optional checkpoint has expired.

Publication validates preimages, writes a durable intent, replaces individual files,
and records completion. A multi-file update is recoverable, not atomic as a set.
After a lost publication reply, recover that same identity and retained post-version;
never rerun the model merely because a success reply was lost. Preserve user Git
metadata, unrelated files, original turns and alternative worktrees.

Current evidence: the dev39 installed terminal completed four real-Q4 turns on
llm-49 through HTTP to llm-60, including a combined queued edit, Aside and Plan.
Independent Chromium desktop/mobile clicks passed on the generated page. Dev40
branch controls passed347 CPU client/server tests. Installed active steering
and matching-version selection now have real-Q4 evidence, including independent
computed-style and greeting-button browser checks at desktop/mobile sizes.
Installed dev42 additionally passed live edit/explore and saved-version switching against
combined COW source9f098e1e. Independent Chromium checked all three resulting pages
on desktop and phone. The audit confirms editing reused the prepared prefix and
exploration combined older context with current files in its own folder. Evidence:
validation/interactive-loop-20261020/live-edit-explore/. These facts do not qualify
the original G1-G5 gates.

Dev43 additionally passed a first-thought steering run with consumed-boundary
pause against candidate COW780e824a: one-token partial receipt, retained original
goal, and independent desktop/mobile formatting/button checks. Evidence:
validation/interactive-loop-20261020/consumed-pause-live-q4/. Fast pause requires
that new server; the restored original service has the older whole-step behavior.

Installed dev43 also passed Stop/close/reopen/continue against real Q4: same
workflow, one-token saved partial, next resume sourced that exact snapshot and
evaluated 2,048 output tokens with zero prefix-forward work. Its resulting page
passed independent desktop/mobile Chromium checks. This restarts the client, not
the native server. See validation/interactive-loop-20261020/stop-reopen-live-q4/.

Preview reads bounded, hash-checked blobs from WorkspaceVersions. HTTP resolves
captured bytes only; it cannot serve arbitrary paths or the COW API key. Its
loopback server is session-owned, uses an opaque URL, retains its port across
refreshes and retires on exit. Preview does not admit workflow/model requests.
The installed-wheel PTY test observed unchanged model-operation records.

Known work remains: repeated steering/network races, conversation-message editing,
mixed coding/admin journeys, broader recovery, performance
attribution and broader unfamiliar-workload qualification. Keep all work on private LAN Git.

## Choose a different sampler for new requests

Ordinary startup remains greedy. To try the existing Min-P profile, run
`branchwrite session --sampler min-p` in your project directory. The DRY fallback
is `--sampler dry-min-p`. These choices apply to new requests, not a generation
already underway. Reopening unresolved work keeps its original settings and IDs.
The interface prints the choice. This is a manual option; automatic detection of
repetitive thinking and a measured sampler fallback are still unfinished.

## When a check prevents completion

New coding runs now tell the model why the current finish was rejected. For
example, a check may have passed before a later file edit made it stale. BW gives
the model that recorded status so it can run a fresh check. A successful command
alone does not establish a successful task, and the recorded status does not
replace checking the latest files again before finishing.

For workflow authors: put VERIFY before TRANSFORM and add evidence=verified to
the tool-feedback transform. The evidence must be a returned Verification for
that same tool operation. The projection excludes protected reference answers.
Existing saved runs keep their pinned program/client version.


## CAD and Blender sessions (new-launch dev62)

The operator can enable a prepared domain environment with one startup option:

    branchwrite session --cad-config /path/to/cad-config.json
    branchwrite session --blender-config /path/to/blender-config.json

Choose one fixed domain per session. Type an ordinary request from
examples/prompts/build123d.txt or blender.txt. Followup, queue, stop, edit,
explore and saved-version controls use the same existing worker and ledger.
Plan, Chat and Aside stay read-only. Saved workflow recovery uses its original
configuration; startup options apply to new requests. Keep old installed client
builds for their admitted workflows; this does not promise cross-version upgrade.

The final display names actual saved outputs such as STEP, .blend, PNG and MP4.
Those immutable export paths are retained with the saved turn. They are separate
from editable source files. CAD acceptance remains the operator's fixed part
family, not every object a person could request. General mixed-domain completion
is unfinished. Focused plumbing checks pass; live interactive domain runs remain
to be qualified separately from the existing one-shot model demonstrations.


## Open the report or text you just made (dev63)

After a saved Work result, type /preview report.pdf to open that saved PDF in your
browser. If the project has one PDF and no website, /preview selects it. Use
/preview START_HERE.txt to read a saved text file. The same printed SSH tunnel
instructions apply when BranchWrite is on a remote client. Keep the terminal
running. The link shows the selected saved version, not unsaved editor changes.
Only the selected PDF/text document is served. Other text files are excluded.
