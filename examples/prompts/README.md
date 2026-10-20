# Try a complete workflow from the CLI

Each .txt file contains one request. It is ordinary text, not executable code,
a .bw workflow or a model checkpoint. Read results.json for the exact executed
status. Unexecuted prompts are marked pending; prior-version passes keep their
version and limits.

Your operator installs BranchWrite, starts Context COW and supplies the server
connection and API key. The key stays in memory by default. Start in a new project
folder. For ordinary interactive work:

    cd ~/my-project
    /full/path/to/branchwrite

Paste a prompt, press Enter, and keep talking when it finishes. Enter while busy
steers; Tab queues a later request. /plan discusses before editing, /work enables
work, /aside asks a question without moving the main tip. /explore keeps an
alternative in a separate project copy. /history searches saved requests.

For a repeatable single CLI job, with the operator connection already saved:

    branchwrite code . --project-files --task-file /path/to/examples/prompts/code.txt
    branchwrite code . --project-files --task-file /path/to/examples/prompts/writing.txt
    branchwrite code . --project-files --task-file /path/to/examples/prompts/pdf.txt

These code commands keep your original directory unchanged and return an owned
workspace and immutable exports. Use the actual returned paths. A remote Linux
path belongs to that client machine, not your Windows File Explorer. The normal
interactive Work interface instead publishes guarded changes into its project.

PDF support is included in the initial installation. Do not install packages
inside a model task. The PDF tools build in an isolated worker and render actual
saved pages. Every current page and current named checks are required before
completion; that evidence alone cannot certify good writing or good layout.

CAD and Blender currently also require the operator's prepared domain runtime:

    branchwrite code . --project-files --cad-config /path/to/cad-config.json --task-file /path/to/examples/prompts/build123d.txt
    branchwrite code . --project-files --blender-config /path/to/blender-config.json --task-file /path/to/examples/prompts/blender.txt

The CAD example is the fixed plate family supplied by that configuration. Do not
reuse its fixed acceptance rules for an unrelated mechanical design. build123d
and bd_warehouse belong to initial CAD environment setup, not per-task installs.
Blender uses the existing bounded MCP adapter; general arbitrary MCP is separate.
New-launch dev62 and later accept these operator configurations in the interactive
session: branchwrite session --cad-config /path/to/cad-config.json, or
branchwrite session --blender-config /path/to/blender-config.json. One fixed
domain is chosen per CLI launch for new Work turns. Reopening with a different
operator domain can retain the same saved files and context; admitted recovery
keeps its original launch. The model still needs actual domain acceptance.
Installed dev63 CAD and Blender passed real Q4 interactive runs, including
reopen/recovery and saved-version selection; see results.json.
Saved outputs are displayed and retained with their turn. General mixed-domain
acceptance is still outstanding.

admin-deploy.txt needs the explicitly configured admin01 remote capability.
It does not authorize other hosts. followup.txt is a second turn after a website
exists. A passing command is evidence about that command; inspect actual outputs.

Do not repeat an unknown operation using a new ID. Reopen its saved run and use
the existing continue/reconciliation path. Keep tested failures and their receipts.

For new work, the prepared dev64 installation is listed in ../../docs/manual/02_BRANCHWRITE_SETUP.md. Its initial setup includes PDF dependencies and compiled bootstrap caches. Use original installations for already admitted work. These prompts do not grant remote hosts or runtime executables.
