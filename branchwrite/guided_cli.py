"""Friendly first-run entry over the canonical BranchWrite/COW coding path."""
from __future__ import annotations

import getpass
import os
import re
import sys
import uuid
from argparse import Namespace
from pathlib import Path

from .coding_cli import start as coding_start


def _slug(text: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:32]
    return value or "coding-task"


def _private_runs_dir(home: Path, env) -> Path:
    base = Path(env.get("XDG_STATE_HOME") or (home / ".local" / "state")).expanduser()
    runs = base / "branchwrite" / "runs"
    runs.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = runs.lstat()
    if not runs.is_dir() or runs.is_symlink() or info.st_uid != os.getuid() or (info.st_mode & 0o077):
        raise ValueError("BranchWrite run folder must be a private, owned folder with mode 700: " + str(runs))
    return runs.resolve(strict=True)


def _verified_summary(code, result, *, project, state, branch, runs_dir, input_fn, output_fn):
    if not isinstance(result, dict):
        output_fn("The run stopped without a readable result. Its saved state is at: " + str(state))
        return code or 2
    # Always surface the canonical finish text, including a reported blocker.
    # Passing model-selected checks alone does not certify the user's task.
    from .run_report import read_report, terminal_text
    if (state / "ledger").exists():
        try:
            report = read_report(state)
            if report["answer"] is not None:
                output_fn("BranchWrite's final report:")
                output_fn(terminal_text(report["answer"]))
        except (OSError, ValueError, RuntimeError, KeyError) as exc:
            output_fn("The saved final report could not be read: " + terminal_text(str(exc)))
            return 2
    if code != 0 or result.get("verified") is not True:
        output_fn("This run did not verify successfully. Nothing was copied into your project.")
        output_fn("Saved work: " + str(state / "world" / "workspace"))
        output_fn("To continue later, use: branchwrite resume " + str(state))
        return code or 3

    output_fn("BranchWrite ran its chosen checks successfully; this is not independent acceptance of the task.")
    output_fn("Your original project folder is unchanged.")
    output_fn("Saved run: " + str(state))
    try:
        from .coding_review import inspect_changes
        review = inspect_changes(state)
    except (OSError, ValueError, RuntimeError, KeyError) as exc:
        output_fn("I could not make the complete change review: " + str(exc))
        output_fn("The result remains in: " + str(state / "world" / "workspace"))
        return 2

    changed = review.get("changes", [])
    if not review.get("complete_project_patch"):
        output_fn("The run has no complete project review; it will stay in its saved work folder.")
        return 0
    if not changed:
        output_fn("No project files changed.")
        return 0
    output_fn("Files changed:")
    for row in changed:
        output_fn("  " + row["path"])
    suffix = branch.rsplit("-", 1)[-1]
    destination = project.parent / (project.name + "-branchwrite-" + suffix)
    output_fn("A separate copy can be made here: " + str(destination))
    output_fn("This does not replace your original folder.")
    answer = input_fn("Type YES to make that separate copy, or press Enter to keep the saved work only: ").strip()
    if answer.casefold() not in ("y", "yes"):
        output_fn("No project copy was made. Your saved work is at: " + str(state / "world" / "workspace"))
        return 0

    archive = runs_dir / (branch + "-review.zip")
    try:
        from .project_export import export_changes
        from .project_apply import apply_export
        exported = export_changes(state, archive)
        applied = apply_export(archive, project, destination, expected_sha256=exported["sha256"])
    except (OSError, ValueError, RuntimeError, KeyError) as exc:
        output_fn("The safe copy could not be made: " + str(exc))
        output_fn("Your original folder is unchanged. Saved work remains at: " + str(state / "world" / "workspace"))
        return 2
    output_fn("Done. Your new copy is here: " + applied["path"])
    output_fn("Open that folder to use the changes. Your original is still unchanged.")
    output_fn("Review archive: " + exported["path"])
    return 0


def run(*, cwd=None, home=None, environ=None, input_fn=None, output_fn=print, secret_fn=None, save_api=False, mode="code", chat_state=None):
    """Use the existing COW conversation or canonical coding workflow."""
    interactive = input_fn is None
    input_fn = input if input_fn is None else input_fn
    secret_fn = getpass.getpass if secret_fn is None else secret_fn
    env = os.environ if environ is None else environ
    if interactive and not sys.stdin.isatty():
        output_fn("Open a terminal in the project folder, then run branchwrite again.")
        return 2
    cwd = Path.cwd() if cwd is None else Path(cwd)
    home = Path.home() if home is None else Path(home)
    submitted = False
    state = None
    try:
        if mode not in ("code", "chat"):
            raise ValueError("Choose code or chat mode.")
        if chat_state is not None and mode != "chat":
            raise ValueError("A saved conversation requires chat mode.")
        project = cwd.resolve(strict=True)
        if not project.is_dir():
            raise ValueError("Open a terminal inside a project folder before starting BranchWrite.")
        from .client_setup import connection_path, read_connection, saved_api_key, command as connect_command
        connection = connection_path(home, env)
        output_fn("BranchWrite")
        import socket
        output_fn("Client machine: " + socket.gethostname())
        output_fn("Project files are on this client machine; the COW server runs the model.")
        output_fn("Project: " + str(project))
        session_keys = []
        if not connection.exists():
            if env.get("BW_COW_CONNECTION"):
                raise ValueError("The connection file selected by BW_COW_CONNECTION is missing. Correct it or unset it and run branchwrite connect.")
            status = connect_command(home=home, environ=env, input_fn=input_fn,
                                     secret_fn=secret_fn, output_fn=output_fn,
                                     save_api=save_api, on_key=session_keys.append)
            if status:
                return status
        admitted_connection = read_connection(connection)
        key = env.get("BW_COW_API_KEY") or (session_keys[0] if session_keys else None) or saved_api_key(connection)
        if not key:
            output_fn("Your server key is needed for this run. It is typed privately.")
            key = secret_fn("COW API key: ").strip()
            if not key:
                raise ValueError("No API key was entered.")
        if save_api and not session_keys:
            from .client_setup import connect
            connect(admitted_connection["endpoint_url"], key, home=home, environ=env, save_api=True)
            output_fn("API key saved privately (--save-api).")

        def start_task(task, source=None):
            nonlocal submitted, state
            if not task.strip():
                raise ValueError("Enter a task before starting.")
            runs_dir = _private_runs_dir(home, env)
            if runs_dir.is_relative_to(project):
                raise ValueError("Run storage must be outside the project folder.")
            branch = "bw-" + _slug(task) + "-" + uuid.uuid4().hex[:8]
            state = runs_dir / branch
            args = Namespace(
                project=project, connection=connection, state=state, task=task, task_file=None,
                branch=branch, sampler="greedy", project_files=True, read=[], edit=[],
                create=[], read_dir=[], edit_dir=[], test_command=[],
                from_branch=source[0] if source else None, from_prefix=None,
                from_snapshot=source[1] if source else None,
                shell_timeout=120, max_steps=1024, project_bases=None, base_choice=None,
                base_revision=None, base_reserve_tokens=None, context_pack=None,
                context_pack_id=None, refresh_context_pack=False, auto_base=False,
            )
            output_fn("Starting the saved BranchWrite + Context COW workflow...")
            submitted = True
            return _run_and_report(args, project, state, branch, runs_dir, input_fn, output_fn)

        # Chat and coding use the same private connection setup. A prompted key
        # stays in this process; neither chat state nor a coding launch stores it.
        with _temporary_api_key(key):
            if mode == "chat":
                return _conversation(connection, chat_state, project, home, env,
                    input_fn, output_fn, start_task)
            output_fn("BranchWrite will work in a separate copy. Your project folder stays unchanged.")
            output_fn("BW can read, create and edit files in this project, and will choose checks for its work.")
            output_fn("Project contents used for the task are sent to your configured model server.")
            output_fn("To talk through an idea first, type /chat.")
            task = input_fn("What would you like changed? ").strip()
            if task == "/chat" or task.startswith("/chat "):
                return _conversation(connection, None, project, home, env,
                    input_fn, output_fn, start_task, first_message=task[5:].strip())
            return start_task(task)
    except (OSError, ValueError, RuntimeError, KeyError) as exc:
        output_fn("BranchWrite could not start: " + str(exc))
        return 2
    except (KeyboardInterrupt, EOFError):
        if submitted and state is not None:
            output_fn("The run was interrupted after submission. Keep this run folder; do not start the same task again.")
            output_fn("Check its saved state first: branchwrite status " + str(state))
            output_fn("If a model or tool operation is unresolved, reconcile that original operation before resuming.")
        else:
            output_fn("Canceled before the task was submitted. Nothing was sent and no run was created.")
        return 130


def _conversation(connection, state, project, home, env, input_fn, output_fn,
                  start_task, *, first_message=""):
    """A terminal presentation of chat_cli; COW still owns the conversation.

    No project contents are loaded in talk mode. /code is the explicit handoff
    to the existing scoped coding workflow, forked from a committed COW tip.
    Local drafts and operation receipts do not replace canonical server history.
    """
    import shlex
    from . import chat_cli
    from .cow_client import OperationIndeterminate
    state = None if state is None else Path(state).expanduser().absolute()
    if state is not None:
        existing = chat_cli._read(chat_cli._state_dir(state))
        if existing["connection"] != chat_cli._connection(connection):
            raise ValueError("This conversation uses a different saved server/profile. Select its original connection.")
    output_fn("Conversation mode. Type a question or talk through an idea.")
    output_fn("/code YOUR TASK starts editing in a separate project copy. /exit leaves the conversation.")
    output_fn("/continue finishes a paused answer. /history, /status, /reconcile and /help are also available.")

    def resume_hint():
        if state is not None:
            output_fn("Resume this conversation: branchwrite talk --state " + shlex.quote(str(state)))
    def controller_notice():
        if state is None:
            return
        chat = chat_cli._read(state)
        if chat.get("head") is not None and chat.get("pending") is None:
            status = chat_cli._current_controller(chat_cli._client(state, chat), chat)
            if status == "active":
                output_fn("The answer is paused at its token budget. Use /continue to keep the same answer going.")
    resume_hint()
    while True:
        try:
            message = first_message or input_fn("You> ").strip()
            first_message = ""
        except (EOFError, KeyboardInterrupt):
            resume_hint()
            return 0
        if not message:
            continue
        if message in ("/exit", "/quit"):
            resume_hint()
            return 0
        if message in ("/help", "/chat"):
            output_fn("Type any question to talk. Use /code YOUR TASK when you want files changed.")
            output_fn("Use /continue, /history, /status or /reconcile for this saved conversation; /exit leaves it.")
            continue
        if message == "/code" or message.startswith("/code "):
            try:
                task = message[5:].strip() or input_fn("What would you like changed? ").strip()
                if not task:
                    output_fn("Enter a task after /code.")
                    continue
                source = chat_cli.coding_source(state) if state is not None else None
            except (EOFError, KeyboardInterrupt):
                resume_hint()
                return 0
            except (OSError, ValueError, RuntimeError, KeyError) as exc:
                output_fn("Cannot start coding from this conversation: " + str(exc))
                continue
            output_fn("Coding mode: BW can read, create and edit files in this project copy and choose checks.")
            output_fn("Project contents used for the task are sent to your configured model server.")
            resume_hint()
            # Coding failures use the coding recovery path. Never swallow an
            # uncertain tool effect and return to the ordinary chat input loop.
            return start_task(task, source)
        try:
            if message in ("/continue", "/history", "/status", "/reconcile"):
                if state is None:
                    output_fn("Send a message first.")
                    continue
                action = {"/continue": chat_cli.continue_command, "/history": chat_cli.history_command,
                          "/status": chat_cli.status_command, "/reconcile": chat_cli.reconcile_command}[message]
                action(state)
                controller_notice()
                continue
            if message.startswith("/"):
                output_fn("Unknown command. Type /help for the available commands.")
                continue
            if state is None:
                runs = _private_runs_dir(home, env)
                if runs.is_relative_to(project):
                    raise ValueError("Run storage must be outside the project folder.")
                branch = "bw-talk-" + uuid.uuid4().hex
                state = runs / branch
                chat_cli.init_command(connection, state, branch, "Conversation about " + project.name, report=False)
                resume_hint()
            chat_cli.send_command(state, message)
            controller_notice()
        except OperationIndeterminate as exc:
            output_fn(str(exc))
            output_fn("Use /reconcile to recover the saved operation before sending anything new.")
        except (OSError, ValueError, RuntimeError, KeyError) as exc:
            output_fn("Conversation could not complete that action: " + str(exc))
        except (EOFError, KeyboardInterrupt):
            output_fn("Interrupted. Any submitted operation keeps its saved ID; reconcile before sending again.")
            resume_hint()
            return 130


class _temporary_api_key:
    def __init__(self, key):
        self.key = key
        self.previous = None

    def __enter__(self):
        self.previous = os.environ.get("BW_COW_API_KEY")
        os.environ["BW_COW_API_KEY"] = self.key

    def __exit__(self, *_):
        if self.previous is None:
            os.environ.pop("BW_COW_API_KEY", None)
        else:
            os.environ["BW_COW_API_KEY"] = self.previous


def _run_and_report(args, project, state, branch, runs_dir, input_fn, output_fn):
    from .__main__ import _run_result
    return _run_result(
        lambda: coding_start(args),
        on_result=lambda code, result: _verified_summary(
            code, result, project=project, state=state, branch=branch,
            runs_dir=runs_dir, input_fn=input_fn, output_fn=output_fn,
        ),
    )
