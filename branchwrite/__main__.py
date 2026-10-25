"""Inspect or execute .bw programs through the one production interpreter."""
import argparse
import hashlib
import os
import stat
from pathlib import Path
import sys
import uuid
from .language import parse,render,ProgramSyntaxError,MAX_SOURCE_BYTES

def _source(path):
    # Nonblocking open avoids a FIFO waiting for its writer before fstat can
    # reject it. Read the opened descriptor, not a separately checked path.
    flags=os.O_RDONLY|getattr(os,'O_NONBLOCK',0)
    fd=os.open(path,flags)
    with os.fdopen(fd,'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ProgramSyntaxError('program source must be a regular file')
        raw=stream.read(MAX_SOURCE_BYTES+1)
    if len(raw)>MAX_SOURCE_BYTES:raise ProgramSyntaxError('source byte limit exceeded')
    try:return raw.decode('utf8')
    except UnicodeError as exc:raise ProgramSyntaxError('source must be valid UTF-8') from exc

def _run_result(action, *, on_result=None):
    from .kernel import TransitionError
    from .cow_client import CowClientError,GenerationIndeterminate
    from .tool_registry import EffectIndeterminate
    from .tool_dispatch import ReconciliationRequired
    from .model_dispatch import ModelReconciliationRequired
    import json
    try:
        code,result=action()
        if on_result is not None:return on_result(code,result)
        print(json.dumps(result,sort_keys=True));return code
    except (EffectIndeterminate,ReconciliationRequired,ModelReconciliationRequired,GenerationIndeterminate) as exc:
        print('branchwrite: unresolved original operation '+ascii(str(getattr(exc,'operation_id','unknown')))+'; reconcile before continuing',file=sys.stderr)
        if isinstance(exc,GenerationIndeterminate):
            print('branchwrite: request ended without completion proof: '+ascii(str(exc)),file=sys.stderr)
        if isinstance(exc,(EffectIndeterminate,ReconciliationRequired)):
            print('For tools, inspect branchwrite status RUN_DIRECTORY after the writer exits. Resume settles only a recorded result with its matching durable retirement proof; an unknown effect stays unresolved and must not be repeated.',file=sys.stderr)
        if isinstance(exc,(ModelReconciliationRequired,GenerationIndeterminate)):
            print('Use branchwrite reconcile STATE --operation-id ORIGINAL_ID, then branchwrite resume STATE. Unknown work remains unresolved.',file=sys.stderr)
        return 4
    except (TransitionError,CowClientError,ValueError,KeyError,TypeError) as exc:
        print('branchwrite: '+ascii(str(exc)),file=sys.stderr);return 2

def main(argv=None):
    if argv is None:argv=sys.argv[1:]
    if argv and argv[0]=='skills':
        try:
            from sss.__main__ import main as skills_main
        except ModuleNotFoundError:
            print('Skills³ is an optional package; install skills-cubed from CC-David-CC/sss to browse its skill map.',file=sys.stderr);return 2
        tail=argv[1:]
        if '--active' in tail:return skills_main(['tree',*tail])
        if tail and tail[0]=='legacy':return skills_main(['tree',*tail[1:]])
        commands={'graph','exercise','school-day','report','teaching-example','explore','workflows'}
        return skills_main(tail if tail and tail[0] in commands else ['graph',*tail])
    if argv and argv[0]=='learning':
        from .learning_cli import main as learning_main
        return learning_main(argv[1:])
    if argv and argv[0]=='lesson':
        from .lesson_cli import main as lesson_main
        return lesson_main(argv[1:])
    if not argv:
        argv=['session']
    if argv[0] in ('--save-api','--sampler','--cad-config','--blender-config'):
        argv=['session',*argv]
    parser=argparse.ArgumentParser(prog='branchwrite',description='Inspect .bw syntax or execute a host-authorized workflow.')
    commands=parser.add_subparsers(dest='command',required=True)
    commands.add_parser('lesson',help='Write verified lessons and request single or batched native training.')
    commands.add_parser('learning',help='Drive PCC-owned learning rounds and reconcile original work.')
    guided=commands.add_parser('start',help='Guide you through one coding task in the current project folder.')
    session=commands.add_parser('session',help='Keep talking while BranchWrite edits this project.')
    session.add_argument('project',type=Path,nargs='?',default=Path.cwd())
    session.add_argument('--state',type=Path,help='Resume this exact saved interactive session.')
    session.add_argument('--sampler',choices=('greedy','min-p','dry-min-p'),default=None,help='Sampler for new interactive requests; saved admitted work keeps its original settings.')
    session.add_argument('--save-api',action='store_true',help='Explicitly save the server key; default is memory only.')
    domain=session.add_mutually_exclusive_group()
    domain.add_argument('--cad-config',type=Path,help='Operator CAD runtime and fixed requirements for new Work requests.')
    domain.add_argument('--blender-config',type=Path,help='Operator Blender/MCP runtime for new Work requests.')
    guided.add_argument('--save-api',action='store_true',help='Explicitly save the API key privately; default: keep it in memory.')
    talk=commands.add_parser('talk',help='Talk through an idea; use /code when ready to edit the project.')
    talk.add_argument('--state',type=Path,help='Resume a saved conversation directory.')
    talk.add_argument('--save-api',action='store_true',help='Explicitly save the API key privately.')
    connection=commands.add_parser('connect',help='Save COW server settings; the API key is not saved by default.')
    connection.add_argument('url',nargs='?',help='COW server address supplied by your operator.')
    connection.add_argument('--save-api',action='store_true',help='Explicitly save the API key privately for future runs.')
    chat=commands.add_parser('chat',help='Use a durable user conversation stored in Context COW.')
    chat_commands=chat.add_subparsers(dest='chat_action',required=True)
    chat_init=chat_commands.add_parser('init',help='Create one named user-conversation branch.')
    chat_init.add_argument('--connection',type=Path,required=True)
    chat_init.add_argument('--state',type=Path,required=True)
    chat_init.add_argument('--branch',required=True)
    chat_init.add_argument('--title',default='User conversation')
    chat_send=chat_commands.add_parser('send',help='Add a user message and return its committed answer.')
    chat_send.add_argument('state',type=Path)
    chat_input=chat_send.add_mutually_exclusive_group(required=True)
    chat_input.add_argument('--message')
    chat_input.add_argument('--message-file',type=Path)
    chat_send.add_argument('--operation-id')
    chat_send.add_argument('--max-tokens',type=int,default=4096)
    chat_queue=chat_commands.add_parser('queue',help='Save a follow-up locally; combine pending messages into one next user turn.')
    chat_queue.add_argument('state',type=Path)
    queue_input=chat_queue.add_mutually_exclusive_group(required=True)
    queue_input.add_argument('--message')
    queue_input.add_argument('--message-file',type=Path)
    chat_queue.add_argument('--operation-id')
    chat_queue.add_argument('--max-tokens',type=int,default=4096)
    drain=chat_commands.add_parser('drain',help='Send the saved follow-up bundle when the assistant is ready.')
    drain.add_argument('state',type=Path)
    stop_add=chat_commands.add_parser('stop-add',help='Cancel an in-flight new answer and retry with added context.')
    stop_add.add_argument('state',type=Path)
    amend_input=stop_add.add_mutually_exclusive_group(required=True)
    amend_input.add_argument('--message')
    amend_input.add_argument('--message-file',type=Path)
    stop_add.add_argument('--operation-id')
    stop_add.add_argument('--max-tokens',type=int,default=4096)
    chat_continue=chat_commands.add_parser('continue',help='Continue an unfinished assistant turn.')
    chat_continue.add_argument('state',type=Path)
    chat_continue.add_argument('--operation-id')
    chat_continue.add_argument('--max-tokens',type=int,default=4096)
    chat_reconcile=chat_commands.add_parser('reconcile',help='Recover one saved original chat operation.')
    chat_reconcile.add_argument('state',type=Path)
    chat_reconcile.add_argument('--operation-id')
    for chat_name in ('history','status'):
        child=chat_commands.add_parser(chat_name)
        child.add_argument('state',type=Path)
        child.add_argument('--json',action='store_true')
    for name in ['check','canonicalize']:
        child=commands.add_parser(name);child.add_argument('program',type=Path)
    for name in ['run','step']:
        child=commands.add_parser(name);child.add_argument('program',type=Path)
        child.add_argument('--config',type=Path,required=True);child.add_argument('--state',type=Path,required=True)
        child.add_argument('--max-steps',type=int,default=1024)
    commands.add_parser('doctor',help='Check real client file and shell isolation without inference.')
    base=commands.add_parser('prepare-base',help='Build context from project files and saved COW branches, or admit an existing verified pack.')
    for name in ('connection','state'):base.add_argument('--'+name,type=Path,required=True)
    source=base.add_mutually_exclusive_group(required=True)
    source.add_argument('--context-pack',type=Path,help='Existing verified reference pack.')
    source.add_argument('--project',type=Path,help='Build a frozen project context from selected files and saved COW branches.')
    base.add_argument('--context-pack-id',help='Exact pack identity; required with --context-pack.')
    for name in ('read','read-dir','source-branch'):
        base.add_argument('--'+name,action='append',default=[])
    for name in ('branch','purpose','source-revision','operation-id'):base.add_argument('--'+name,required=True)
    base.add_argument('--capacity',type=int,required=True,help='Exact pinned profile capacity, not a tokenizer estimate.')
    base.add_argument('--reconcile',action='store_true',help='Explicitly recover a proven durable original context operation; never recompute unknown work.')
    context_status=commands.add_parser('context-status',help='Show the last durable project-context step and COW receipts without inference.')
    context_status.add_argument('state',type=Path);context_status.add_argument('--json',action='store_true')

    code=commands.add_parser('code',help='Start coding in an owned copy with explicit file grants.')
    code.add_argument('project',type=Path,nargs='?',default=Path.cwd(),help='Project directory; defaults to the directory where you run BranchWrite.')
    code.add_argument('--connection',type=Path,default=Path.home()/'.config'/'branchwrite'/'connection.json',help='Server profile; defaults to ~/.config/branchwrite/connection.json.')
    code.add_argument('--state',type=Path,help='Run state directory; defaults to a private unique folder under XDG_STATE_HOME.')
    task_input=code.add_mutually_exclusive_group(required=True)
    task_input.add_argument('--task-file',type=Path)
    task_input.add_argument('--task',help='Inline task text; never executed.')
    code.add_argument('--branch',help='Context COW branch name; generated when omitted.')
    code.add_argument('--sampler',choices=('greedy','min-p','dry-min-p'),default='greedy',help='Sampler preset for a new run; resume keeps its saved settings.')
    code.add_argument('--thinking',choices=('standard','off'),default='standard',help='New-run thinking mode; off decodes directly into the registered tool grammar. Resume keeps its saved mode.')
    code.add_argument('--instructions',choices=('worked-examples','compact'),default='worked-examples',help='Instructions for a new coding root; compact omits worked examples. Retained roots keep their original prefix.')
    for name in ('read','edit','create','read-dir','edit-dir','test-command'):
        code.add_argument('--'+name,action='append',default=[])
    origin=code.add_mutually_exclusive_group()
    origin.add_argument('--from-branch',help='Fork a completed conversation tip.')
    origin.add_argument('--from-prefix',help='Ask from a retained idle context root.')
    origin.add_argument('--project-bases',type=Path,help='Host catalog for a proposed Project Base choice.')
    origin.add_argument('--context-pack',type=Path,help='Verified reference pack for a new coding root.')
    code.add_argument('--context-pack-id',help='Exact reference-pack identity; paired with --context-pack.')
    code.add_argument('--refresh-context-pack',action='store_true',help='For a new run, rebuild changed sources into a new immutable pack before admission; resume never refreshes.')
    code.add_argument('--build-project-context',action='store_true',help='Build a frozen context from the files already granted by --read/--read-dir and optional saved COW branches.')
    code.add_argument('--context-source-branch',action='append',default=[],help='Include a completed saved COW branch as unverified reference examples.')
    code.add_argument('--auto-base',action='store_true',help='Choose the longest compatible fitting prefix from the host catalog; pin it for this run.')
    code.add_argument('--base-choice',type=Path,help='Untrusted JSON proposal to validate, not execute.')
    code.add_argument('--base-revision',help='Host-required source revision for the selected base.')
    code.add_argument('--base-reserve-tokens',type=int,help='Host-required token headroom; COW still checks actual capacity.')
    code.add_argument('--from-snapshot')
    code.add_argument('--shell-timeout',type=float,default=120)
    code.add_argument('--project-files',action='store_true',help='Let BW choose project-relative files to read, create and edit in its owned copy.')
    code.add_argument('--blender-config',type=Path,help='Operator-pinned Blender/MCP runtime for scene creation, controlled views and animation.')
    code.add_argument('--cad-config',type=Path,help='Operator-pinned build123d runtime and fixed geometry requirements. Requires --project-files.')
    code.add_argument('--max-steps',type=int,default=1024)
    code.add_argument('--explore',action='store_true',help='Try two isolated approaches, check both, and select a passing candidate.')
    code.add_argument('--approach',action='append',help='Approach instruction; provide exactly twice with --explore.')
    code.add_argument('--select-candidate',choices=('verified-first','first','second'),default='verified-first',help='Select only after both candidates settle and required checks pass.')
    resume=commands.add_parser('resume',help='Resume a saved coding setup without changing its task or source.')
    resume.add_argument('state',type=Path);resume.add_argument('--max-steps',type=int,default=1024)
    apply=commands.add_parser('apply',help='Apply a pinned export into a new owned project copy.')
    apply.add_argument('archive',type=Path);apply.add_argument('--source',type=Path,required=True)
    apply.add_argument('--destination',type=Path,required=True);apply.add_argument('--sha256',required=True);apply.add_argument('--operation-id')
    export=commands.add_parser('export',help='Export complete reviewed changes into a new archive.')
    export.add_argument('state',type=Path);export.add_argument('destination',type=Path)
    review=commands.add_parser('review',help='Inspect recorded file-tool changes without publication.')
    review.add_argument('state',type=Path);review.add_argument('--json',action='store_true')
    status=commands.add_parser('status',help='Read recorded run status without execution or inference.')
    status.add_argument('state',type=Path);status.add_argument('--json',action='store_true')
    status.add_argument('--tail',type=int,default=12,help='Number of recent committed activity summaries to show (0-64).')
    receipt=commands.add_parser('receipt',help='Inspect an exact locally retained COW generation receipt without contacting the server.')
    receipt.add_argument('state',type=Path);receipt.add_argument('--operation-id',required=True)
    receipt.add_argument('--show-answer',action='store_true',help='Display exact answer text; withheld by default.')
    receipt.add_argument('--json',action='store_true')
    reconcile=commands.add_parser('reconcile',help='Recover proven durable output for one pending model operation; does not advance the workflow.')
    reconcile.add_argument('state',type=Path);reconcile.add_argument('--operation-id',required=True)
    args=parser.parse_args(argv)
    if args.command=='session':
        from .interactive_cli import run
        return run(project=args.project,state=args.state,save_api=args.save_api,**({} if args.sampler is None else {'sampler':args.sampler}),
            **({} if args.cad_config is None else {'cad_config':args.cad_config}),
            **({} if args.blender_config is None else {'blender_config':args.blender_config}))
    if args.command=='code':
        if args.branch is None:
            args.branch='bw-'+uuid.uuid4().hex[:16]
            args._generated_branch=True
        else:
            args._generated_branch=False
        if args._generated_branch:
            print('[BranchWrite] Context COW branch: '+args.branch,file=sys.stderr,flush=True)
        if args.state is None:
            state_home=Path(os.environ.get('XDG_STATE_HOME',str(Path.home()/'.local'/'state')))
            if not state_home.is_absolute():
                print('branchwrite: XDG_STATE_HOME must be an absolute path',file=sys.stderr);return 2
            args.state=state_home/'branchwrite'/'runs'/args.branch
            args._generated_state=True
            print('[BranchWrite] New run state: '+str(args.state),file=sys.stderr,flush=True)
        else:
            args._generated_state=False
    try:
        if args.command=='connect':
            from .client_setup import command
            return command(args.url,save_api=args.save_api)
        if args.command=='start':
            from .guided_cli import run
            return run(save_api=args.save_api)
        if args.command=='talk':
            from .guided_cli import run
            return run(mode='chat',chat_state=args.state,save_api=args.save_api)
        if args.command=='chat':
            from .chat_cli import command
            return command(args)
        if args.command=='context-status':
            from .base_cli import status_command
            return status_command(args.state,as_json=args.json)
        if args.command=='prepare-base':
            from .base_cli import prepare
            return _run_result(lambda:prepare(args))
        if args.command=='doctor':
            from .client_doctor import command
            return command()
        if args.command=='reconcile':
            from .coding_reconciliation import reconcile_saved
            return _run_result(lambda:reconcile_saved(args.state,args.operation_id))
        if args.command=='apply':
            from .project_apply import command
            return command(args.archive,args.source,args.destination,args.sha256,args.operation_id)
        if args.command=='export':
            from .project_export import command
            return command(args.state,args.destination)
        if args.command=='review':
            from .coding_review import command
            return command(args.state,as_json=args.json)
        if args.command=='status':
            from .coding_status import command
            return command(args.state,as_json=args.json,tail=args.tail)
        if args.command=='receipt':
            from .receipt_cli import command
            return command(args.state,args.operation_id,show_answer=args.show_answer,as_json=args.json)
        if args.command in ('code','resume'):
            from .coding_cli import start,run_saved
            return _run_result(lambda:start(args) if args.command=='code' else run_saved(args.state,max_steps=args.max_steps))
        source=_source(args.program)
        if args.command in ('run','step'):
            # Lazy import: inspection commands remain read-only and dispatch-free.
            from .run_cli import execute
            return _run_result(lambda:execute(args.command,source,_source(args.config),args.state,max_steps=args.max_steps))
        nodes=parse(source);canonical=render(nodes)
        if args.command=='canonicalize':sys.stdout.buffer.write(canonical.encode('utf8'))
        else:
            count=0;pending=list(nodes)
            while pending:
                node=pending.pop();count+=1;pending.extend(node.body)
            print('Syntax OK: '+str(count)+' statements; canonical SHA256 '+hashlib.sha256(canonical.encode('utf8')).hexdigest())
            print('Execution: NOT_RUN (names, types, grants and effects are not admitted by syntax checking)')
        return 0
    except (OSError,ProgramSyntaxError) as exc:
        # Controlled syntax reasons contain no source text. Escape OS filename
        # data as a representation so it cannot become terminal control codes.
        print('branchwrite: '+ascii(str(exc)),file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
