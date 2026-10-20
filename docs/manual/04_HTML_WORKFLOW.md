# Ask the BranchWrite CLI agent to create or edit an HTML website

## Simple start

Open a terminal in the project folder and run `branchwrite`. Describe what you
want; BW chooses files to read, create or edit and selects checks. You do not
need filename lists or a prewritten test command. It works in an isolated copy
and offers the verified result for review. See [First task](06_FIRST_TASK.md).

The optional browser only previews the generated site. It is not the BranchWrite
client or COW math viewer. The detailed command below documents the older
explicit-grant interface for reproducible experiments.

First complete the server/client guides. Activate the dev28 venv, keep the SSH tunnel open, and export BW_COW_API_KEY in this client terminal.

## Create a new website

On the Linux client, make a new project directory. If my-site already exists, choose a new name:

~~~bash
mkdir -p "$HOME/projects" "$HOME/bw-runs"
mkdir "$HOME/projects/my-site"
cat > "$HOME/projects/my-site/check_site.py" <<'PY'
"""Small offline structural smoke check, not a browser/design acceptance test."""
from html.parser import HTMLParser
from pathlib import Path

class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.stylesheets = []
        self.language = None
        self.title_depth = 0
        self.title = []
    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        attributes = dict(attrs)
        if tag == "html":
            self.language = attributes.get("lang")
        if tag == "title":
            self.title_depth += 1
        if tag == "link" and "stylesheet" in attributes.get("rel", "").split():
            self.stylesheets.append(attributes.get("href"))
    def handle_endtag(self, tag):
        if tag == "title":
            self.title_depth = max(0, self.title_depth - 1)
    def handle_data(self, data):
        if self.title_depth:
            self.title.append(data)

root = Path(__file__).resolve().parent
html = (root / "index.html").read_text(encoding="utf-8")
css = (root / "style.css").read_text(encoding="utf-8")
assert "\x00" not in html + css, "NUL bytes are not valid source text here"
page = Page()
page.feed(html)
page.close()
for tag in ("html", "head", "title", "body", "h1"):
    assert tag in page.tags, f"Missing <{tag}>"
assert page.language, "Set the page language on <html>"
assert "".join(page.title).strip(), "Use a nonempty page title"
assert "style.css" in page.stylesheets, "Link the local style.css stylesheet"
assert css.strip() and "{" in css and "}" in css, "Write CSS rules"
print("PASS: basic HTML structure and local stylesheet")
PY
~~~

This creates a small standard-library structural check. The same script is in docs/manual/examples/check_site.py. It checks structure, not screenshots, visual design or browser behavior.

Create a task file outside the project:

~~~bash
cat > "$HOME/branchwrite-client/site-task.txt" <<'TASK'
Create a simple, attractive static website for a small garden club.
Create index.html and style.css. Use a clear heading, a short welcome,
a list of upcoming activities, and a contact section.
Use semantic HTML, a descriptive page title, and responsive CSS.
Link the local stylesheet as style.css. Do not use remote fonts,
external libraries, a backend, or JavaScript.
Read check_site.py. Keep it unchanged.
Run python3 check_site.py. Finish only after that command really passes.
TASK
~~~

Run BranchWrite. Use fresh state/branch names for a new task:

~~~bash
branchwrite code "$HOME/projects/my-site" \
  --connection "$HOME/branchwrite-client/connection.json" \
  --state "$HOME/bw-runs/site-first" \
  --branch david-site-first \
  --task-file "$HOME/branchwrite-client/site-task.txt" \
  --read check_site.py --read index.html --read style.css \
  --create index.html --create style.css \
  --edit index.html --edit style.css \
  --test-command "python3 check_site.py" \
  --sampler greedy \
  --max-steps 1024
~~~

The missing index.html/style.css names are explicitly creatable. The edit grants let it correct those same files after creation. The check script is readable but not editable. These grants do not give tools access to arbitrary client files or the inference server.

Progress goes to stderr. The final stdout is a JSON result. A successful task exits 0 and reports verified=true. That means the configured command evidence and finish policy passed; inspect the appearance yourself.

The commands, parser and grants were checked locally. A separate installed dev25 real-Q8 campaign based on this garden-club task passed its structural check and interrupted-run recovery. Parent-operated desktop/mobile rendering passed on llm-60. This is bounded evidence, not a guarantee for arbitrary website tasks; inspect your own result.

## Find and preview the result

The new website is here, not in your original project:

~~~bash
ls -l "$HOME/bw-runs/site-first/world/workspace"
branchwrite status "$HOME/bw-runs/site-first"
branchwrite review "$HOME/bw-runs/site-first"
~~~

Serve that directory locally in a separate Linux client terminal:

~~~bash
python3 -m http.server 8080 --bind 127.0.0.1 \
  --directory "$HOME/bw-runs/site-first/world/workspace"
~~~

If your browser is on Windows, open a separate Windows PowerShell terminal:

~~~powershell
ssh -N -L 127.0.0.1:18080:127.0.0.1:8080 llm-49
~~~

Then visit http://127.0.0.1:18080 in your browser. This is the website preview, not the model API. Stop the preview and its tunnel with Ctrl+C when done.

## Export and use the reviewed website

~~~bash
branchwrite export "$HOME/bw-runs/site-first" "$HOME/site-first.zip"
sha256sum "$HOME/site-first.zip"
~~~

Copy the actual reported SHA256 below; replace ACTUAL_ARCHIVE_SHA256:

~~~bash
branchwrite apply "$HOME/site-first.zip" \
  --source "$HOME/projects/my-site" \
  --destination "$HOME/projects/my-site-reviewed" \
  --sha256 ACTUAL_ARCHIVE_SHA256 \
  --operation-id david-site-first-apply
~~~

Apply creates a new owned project copy. It checks the original project still matches the captured input. It does not overwrite the original directory or push Git changes. The destination must be new. Keep the operation ID for retry after a lost acknowledgment.

Your usable output is now in my-site-reviewed. You may review/copy the files into a live site yourself. Replacing a live checkout is a separate publication decision.

## Edit an existing website

Choose the real source folder and a real verification command. For a simple site with index.html, style.css and the same check script:

~~~bash
branchwrite code "$HOME/projects/my-site-reviewed" \
  --connection "$HOME/branchwrite-client/connection.json" \
  --state "$HOME/bw-runs/site-change" \
  --branch david-site-change \
  --from-prefix david-site-first \
  --task "Read the existing site. Improve its mobile layout and add a short meeting-times section. Keep the garden club content and check script. Run python3 check_site.py before finishing." \
  --read index.html --read style.css --read check_site.py \
  --edit index.html --edit style.css \
  --test-command "python3 check_site.py" \
  --sampler greedy
~~~

The --from-prefix option reuses the idle root prepared by the first run; the client pins its exact root snapshot at admission. It does not include the first finished conversation. If you did not run the first example, omit this option or supply a known compatible prefix branch. An evicted checkpoint may require reported recomputation; a branch name is not a GPU-residency lock.

For another website, change the file grants and test command to match that project. Directory grants such as --read-dir assets or --edit-dir assets cover an existing bounded directory; they are not permission to edit unrelated directories. A Git project is copied without its .git administration.

Review/export/apply this task into another new destination. The source folder remains unchanged.

## Continue or branch

For unfinished work:

~~~bash
branchwrite resume "$HOME/bw-runs/site-change"
~~~

Use the same versioned venv, state and credentials. Do not replace the task/configuration of an admitted run. Exit 3 means the step budget stopped before verified completion; inspect status and resume. Exit 1 means the program completed without verified success. Exit 2 is an admission/runtime error. Exit 4 means an original operation is unresolved.

For a separate task sharing a prepared idle context, code supports --from-prefix BRANCH with an exact --from-snapshot ID. For a completed conversation use --from-branch BRANCH instead. These are different turn boundaries. Use exact retained references; do not assume any arbitrary tip is an idle prefix.

A new task also supports --sampler min-p or --sampler dry-min-p. Greedy is the first choice. Resume preserves its originally saved sampler settings.

A pinned reference pack can be admitted with --context-pack PATH --context-pack-id ID. Add --refresh-context-pack only for a new run that should rebuild changed approved reference sources. That preserves old packs and roots; changed prefix bytes require a new prefill.

### Build a project context from files and saved branches

The current source branch adds `--build-project-context`. It uses only paths
already granted with `--read` and `--read-dir`; it does not scan the whole
project. Add `--context-source-branch NAME` to include a completed saved COW
branch as unverified examples. For example:

~~~bash
branchwrite code "$HOME/projects/my-site" \
  --connection "$HOME/branchwrite-client/connection.json" \
  --state "$HOME/bw-runs/site-with-context" \
  --branch david-site-context \
  --task "Review the current site and fix broken links" \
  --read index.html --read style.css --read-dir docs \
  --context-source-branch earlier-link-repair \
  --build-project-context \
  --edit index.html --edit style.css \
  --test-command "python3 check_site.py"
~~~

Before inference, BranchWrite freezes those selected file bytes and exact saved
branch tip identities into a durable client receipt, then builds the pinned
reference pack. Prior branch conversations are examples, not proof of current
source contents or permission to use tools. The saved run pins the receipt hash
alongside its COW request.

If the process stops before the coding launch is published, rerun the same
command with the same state and arguments; it recovers the frozen files and
branch history instead of capturing newer data. Use `branchwrite context-status
STATE` to see the last durable stage. Once the coding launch exists, use
`branchwrite resume STATE`. A changed project or branch should be admitted
under a new state, giving it a new prefill.

This feature is in private BranchWrite source branch
`feat/explicit-model-reconciliation-20261019` (dev29 source). It is not the
default client installation. Focused receipt tests and local CPU Context COW
HTTP recovery tests pass. In the crash test, the client dies after the immutable
source snapshot is durable but before the outer receipt is published. The COW
HTTP server is stopped; a new client process recovers the frozen files and saved
branch history without contacting the server.

If `branchwrite context-status STATE` reports
`SOURCE_SNAPSHOT_RECOVERY_CANDIDATE`, the embedded receipt survived. Rerun the
original `branchwrite code` command with the same state and source selections.
BranchWrite verifies the frozen bytes and reuses that snapshot. The status view
shows the last durable log entries. Once the coding launch exists, use
`branchwrite resume STATE`.

After the offline recovery, the test restarts the local COW HTTP server and runs
the actual resume command. It confirms the worker branch is created and
`branchwrite status STATE --json` reads its workflow ledger.

This proves bounded context recovery and resume handoff through the HTTP API
with a deterministic CPU backend. The offline recovery step stubs inference;
the later resume uses the actual CLI and CPU fixture. This does not prove Q4/Q8
quality or speed, recovery during a live model/tool operation, or full
autonomous-task continuation after restart.


Never resolve an unknown tool effect by submitting the same action with a new operation ID.
