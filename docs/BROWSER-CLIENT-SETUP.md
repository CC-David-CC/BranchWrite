# Linux browser worker: tested setup and limits

BranchWrite can open an exact saved web page in an isolated browser, click a
button, fill a box and save a screenshot. The browser cannot see your home
folder or connect to a service on the host. It keeps Chromium's own sandbox.

This page describes the **browser worker**, not a finished automatic browser
feature in the normal `bw` session. The regular directory CLI still needs browser
capability admission and end-to-end integration. A screenshot reaching the model
also needs the COW server's pinned image encoder. A native `--vision` worker alone
does not enable that encoder. See the existing Linux quickstart for the tested
text client; do not mistake these developer commands for its beginner installer.

## Reproduced failures

The installed client uses an application-managed Python distribution. Its standard library
lives outside the virtual environment. Mounting only the environment made Python
fail with `No module named encodings` before Chromium started. The worker now
mounts both runtime roots read-only.

Ubuntu's ordinary Bubblewrap policy on the test VM strips capabilities
from its children, including capabilities needed inside Chromium's further user
namespace. Both the Snap browser and Playwright's matching browser refused to
start. Kernel audit records identified `unpriv_bwrap` denying `sys_admin`.
The launcher must not respond by disabling Chromium sandboxing.

## Dedicated AppArmor setup (administrator)

This exact profile was tested on an Ubuntu 26.04 VM, with the global
`kernel.apparmor_restrict_unprivileged_userns` value remaining `1`. It does not
replace or edit `/etc/apparmor.d/bwrap-userns-restrict`.

From this checkout, an administrator can install a separate non-setuid copy of
the packaged Bubblewrap binary and the dedicated profile:

```sh
sudo install -d -o root -g root -m 755 /usr/local/libexec
sudo install -o root -g root -m 755 /usr/bin/bwrap /usr/local/libexec/branchwrite-browser-bwrap
sudo install -o root -g root -m 644 packaging/apparmor/branchwrite-browser /etc/apparmor.d/branchwrite-browser
sudo apparmor_parser -Q /etc/apparmor.d/branchwrite-browser
sudo apparmor_parser -r /etc/apparmor.d/branchwrite-browser
```

Check for an existing installation before replacing files. The profile gives
this named executable permission to use user namespaces. It is a named
`unconfined` AppArmor profile, as used for Ubuntu's browser namespace permission;
it is not a claim of an additional AppArmor file-access sandbox. The actual file,
network and process boundaries remain Bubblewrap's namespace/mount restrictions,
its capability drop, and Chromium's own sandbox. No host Linux capability or
setuid bit is added. A measured worker had UID 1002, zero effective/permitted/
bounding capabilities, and `NoNewPrivs: 1`.

The worker automatically uses the dedicated path when present. It rejects a
symlink, non-root ownership, writable installation paths, setuid/setgid bits,
or bytes differing from `/usr/bin/bwrap`. A package upgrade may require the
administrator to refresh the copy. An invalid copy is an error, never a reason
to use it anyway. Without this dedicated installation, the worker uses ordinary
`/usr/bin/bwrap`; a host-policy rejection remains an error.

To remove only this optional installation, first stop owned browser jobs, then:

```sh
sudo apparmor_parser -R /etc/apparmor.d/branchwrite-browser
sudo rm -- /etc/apparmor.d/branchwrite-browser /usr/local/libexec/branchwrite-browser-bwrap
```

The system policy and global restriction remain intact. Other distributions and
policy versions need their own validation; this is not a fleet-wide deployment.

## Reproduce the worker checks (developer)

Use a separate environment; do not alter a previously installed, admitted
BranchWrite runtime in place. The executed VM environment used Python 3.12,
Playwright 1.64.0, Pillow 13.0.0 and Chromium 156.0.8078.4 (Playwright revision
1248). Install the browser matching the Playwright version:

```sh
python -m venv .venv-browser
.venv-browser/bin/python -m pip install playwright==1.64.0 Pillow==13.0.0
export PLAYWRIGHT_BROWSERS_PATH="$HOME/.local/share/branchwrite/test-browsers"
.venv-browser/bin/python -m playwright install --no-shell chromium
export BW_BROWSER_EXECUTABLE="$PLAYWRIGHT_BROWSERS_PATH/chromium-1248/chrome-linux64/chrome"
PYTHONPATH="$PWD:$PWD/tests" .venv-browser/bin/python -B -m unittest -v test_browser_isolation test_browser_worker_diagnostics test_browser_launcher
```

`python` here denotes a verified Linux interpreter; use the installed interpreter
name on your host. The browser also needs the distribution's runtime libraries
and fonts. Japanese/CJK text can be correct in the DOM while rendering as boxes
when a font is missing. On the tested Ubuntu VM, `fonts-noto-cjk` supplies that
coverage. Inspect screenshots as well as text receipts.

The broader executed selection is recorded under
`validation/browser-client-20261020/`. Two protected-catalog suites were not run
in this VM selection. Passing these worker checks is not a model-vision test, a
complete coding-agent browser run, or G1–G5 qualification.

Primary references: [Playwright browser installation](https://playwright.dev/python/docs/browsers)
and [Ubuntu AppArmor](https://documentation.ubuntu.com/security/security-features/privilege-restriction/apparmor/).
