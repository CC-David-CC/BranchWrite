# Admit a project without naming every file

The code command accepts repeated --read-dir and --edit-dir options alongside
the existing explicit file grants.

Example:
branchwrite code /project --task "Fix the failing tests" --connection connection.json --state /runs/fix --branch fix --read-dir . --edit-dir src --test-command "python3 -m unittest discover -s tests"

A dot selects the project root. Directory names use canonical POSIX paths within
the project. Admission expands current regular files into sorted exact grants.
Edit files are also readable. Git administration is omitted; .github remains
ordinary project data. Links, special files, escapes and oversized/deep trees are
rejected. The existing project limits remain4MiB/file,64MiB/20,000entries and
64levels. No model-controlled grant expansion is added.

The selected filenames are saved in coding-launch.json and canonically bound
through the configuration digest. resume uses those saved grants and does not
rescan. New files acquire no rights automatically. Reissuing code after the tree
changes may reject changed setup; use resume for the original admitted work, or
a new run state for new authority. Creation still needs explicit --create paths.

Directory enumeration selects names, not immutable content bytes. Existing
project_baseline captures the actual copied input separately before dispatch.
The existing model tool schema lists authorized filenames, and read-only shell
projection exposes only granted files. Large enumerated schemas and search UX
remain performance/usability work; no new native inference API is required.
