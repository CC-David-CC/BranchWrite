"""Prepare the existing coding workflow; COW and RuntimeLog remain authoritative."""
import hashlib,json,os,re,stat,tempfile
from pathlib import Path
from .client_setup import key_for_connection
from .run_cli import _config,_pairs,execute,_source_notice
from .cow_client import CowClient,HTTPTransport,OperationJournal,OperationIndeterminate
PROGRAM="""FLOW coding
REPEAT attempts exhausted=stop max=32 until=verified
EXPAND decide from=current profile=control task=task -> proposed
PLAN freeze against=world from=proposed -> plan
ACT perform plan=plan -> outcome
TRANSFORM advance contract=cow-source input=proposed -> current
VERIFY check contract=command-evidence-and-finish input=outcome -> verified
TRANSFORM feedback contract=tool-feedback input=outcome evidence=verified -> task
END
END
"""
PROJECT_PROGRAM=PROGRAM.replace("command-evidence-and-finish","project-checks-and-finish").replace("evidence=verified -> task","evidence=verified profile=project-views -> task")
READ_PROGRAM=PROGRAM.replace("command-evidence-and-finish","read-only-and-finish")
CAD_PROGRAM=PROGRAM.replace('command-evidence-and-finish','cad-geometry-and-finish').replace('evidence=verified -> task','evidence=verified profile=cad-views -> task')
BLENDER_PROGRAM=CAD_PROGRAM.replace('cad-geometry-and-finish','blender-scene-and-finish')
MAX_LAUNCH_BYTES=1024*1024

def exploration_program(program,rule='verified-first'):
    from .language import parse,render,Statement
    body=parse(program)[0].body
    repeat=body[0]
    fields=tuple((key,'8' if key=='max' else value) for key,value in repeat.attributes)
    repeat=Statement(repeat.opcode,repeat.label,fields,repeat.output,repeat.body)
    arms=tuple(Statement('BRANCH',name,(('base','current'),('world',name)),body=(
        Statement('VALUE','task',(('type','Text'),('ref','approach-'+name))),repeat))
        for name in ('first','second'))
    parallel=Statement('PARALLEL.DO','candidates',(('base','current'),('budget','explore')),body=arms)
    selection=Statement('SELECT','choose',(('input','candidates'),('rule',rule)),output='selected')
    return render((Statement('FLOW','exploration',body=(parallel,selection)),))


def enable_exploration(launch,approaches=None,*,selection='verified-first'):
    """Opt in before admission; existing saved launches are never rewritten."""
    if approaches is None:
        approaches=['Use a straightforward solution with a clear, small implementation.',
                    'Try a meaningfully different decomposition or representation for the solution.']
    if (type(approaches) is not list or len(approaches)!=2
            or any(type(s) is not str or not s.strip() or len(s.encode())>8192 for s in approaches)
            or selection not in ('verified-first','first','second')):
        raise ValueError('Two bounded approach instructions and an explicit selection rule required')
    config=launch['config']
    if config.get('remotes'):raise ValueError('Exploration uses isolated local worlds, without shared remote mutations')
    if config.get('verification')==dict(schema=1,read_only=True):
        raise ValueError('Use a Work task with explicit checks for verified exploration')
    profile=config['profiles']['control']
    profile.update(request_tokens=512,max_requests=8,max_output_tokens=4096)
    config['exploration']=dict(schema=1,approaches=dict(zip(('first','second'),approaches)),
        selection=selection,budget=dict(max_parallel=2,max_requests=128,max_output_tokens=65536))
    for name,direction in config['exploration']['approaches'].items():
        config['bindings']['approach-'+name]=dict(type='Text',value=config['bindings']['task']['value']+
            '\n\nApproach instruction: '+direction+'\nRun the required checks on your candidate before finishing.')
    launch['program']=exploration_program(launch['program'],selection)
    return launch
def _bytes(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()
def build_launch(project,task,connection,*,branch,project_files=False,read_paths=(),edit_paths=(),create_paths=(),test_commands=(),from_branch=None,from_prefix=None,from_snapshot=None,shell_timeout=120,sampler="greedy",base_catalog=None,base_proposal=None,base_revision=None,base_reserve_tokens=None,context_pack=None,context_pack_id=None,refresh_context_pack=False,auto_base=False,mode="work",remotes=None,cad=None,blender=None):
    if mode not in ('work','plan','chat','aside'):raise ValueError('unsupported coding mode')
    from .coding_defaults import generation_profile
    profile=generation_profile(sampler)
    if from_prefix is not None and from_branch is not None:
        raise ValueError('choose a prepared prefix or a completed branch, not both')
    if from_prefix is not None:from_branch=from_prefix
    project=Path(project).resolve(strict=True)
    if not project.is_dir():raise ValueError('project must be a directory')
    if mode!='work':
        from .project_scope import expand_directories
        if edit_paths or create_paths or test_commands:raise ValueError('read-only mode cannot grant writes or execution')
        project_files=False;read_paths=expand_directories(project,['.'])
    keys={'endpoint_url','endpoint_pin','model_contract_id','execution_profile_id','eos_tokens'}
    if type(connection) is not dict or set(connection)!=keys:
        raise ValueError('connection needs only endpoint/profile identities and EOS IDs; credentials belong in BW_COW_API_KEY')
    HTTPTransport(connection['endpoint_url'])
    selection=None
    if type(auto_base) is not bool:raise ValueError('auto_base must be a boolean')
    if auto_base:
        if base_proposal is not None:raise ValueError('choose automatic host selection or a proposal, not both')
        from .base_choice import select_host_base
        selected=select_host_base(base_catalog,required_revision=base_revision,required_profile=connection['execution_profile_id'],reserve_tokens=base_reserve_tokens)
        base_proposal=json.dumps(dict(schema=1,base_id=selected['base']['base_id'],reason=selected['reason']))
    base_args=(base_catalog,base_proposal,base_revision,base_reserve_tokens)
    if any(value is not None for value in base_args):
        if any(value is None for value in base_args):
            raise ValueError('base selection requires catalog, proposal, source revision and token reserve')
        if any(value is not None for value in (from_branch,from_prefix,from_snapshot)):
            raise ValueError('choose a proposed Project Base or an explicit source, not both')
        from .base_choice import resolve_base_proposal
        selection=resolve_base_proposal(base_proposal,base_catalog,
            required_revision=base_revision,required_profile=connection['execution_profile_id'],
            reserve_tokens=base_reserve_tokens)
        from_prefix=selection['base']['branch'];from_branch=from_prefix
        from_snapshot=selection['base']['snapshot']
    pack=None
    refresh_receipt=None
    if type(refresh_context_pack) is not bool:
        raise ValueError('refresh_context_pack must be a boolean')
    if refresh_context_pack and context_pack is None:
        raise ValueError('refresh requires an explicit pinned context pack')
    if context_pack is not None or context_pack_id is not None:
        if context_pack is None or context_pack_id is None:
            raise ValueError('provide context pack path and identity together')
        if selection is not None or from_branch is not None or from_snapshot is not None:
            raise ValueError('reference packs require a new bootstrap, not an existing context')
        if not isinstance(context_pack,(str,Path)) or not Path(context_pack).is_absolute():
            raise ValueError('context pack path must be absolute')
        from .context_pack import load_verified_prefix, refresh_pack
        if refresh_context_pack:
            from datetime import datetime,timezone
            # Only new admission: old packs/roots are immutable. Source capture
            # is not semantic validation or a lock on subsequent external edits.
            refresh_receipt=refresh_pack(context_pack,output=Path(context_pack).parent,
                as_of=datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),
                expected_id=context_pack_id)
            context_pack=refresh_receipt['pack_path']
            context_pack_id=refresh_receipt['pack_id']
        # Admission verifies current source bytes. Saved launches retain the
        # pin; normal resume keeps its already admitted canonical COW root.
        load_verified_prefix(context_pack,expected_id=context_pack_id)
        pack=dict(path=str(context_pack),pack_id=context_pack_id)
    if type(task) is not str or not task.strip() or len(task.encode('utf8'))>262144:raise ValueError('bounded nonempty task text required')
    if type(branch) is not str or not 1<=len(branch)<=128:raise ValueError('bounded branch name required')
    if type(project_files) is not bool:raise ValueError('project_files must be a boolean')
    if project_files and test_commands:raise ValueError('project mode selects checks during the task')
    if mode=='work' and not project_files and (not test_commands or any(type(c) is not str or not c.strip() for c in test_commands)):
        raise ValueError('at least one explicit verification command is required')
    if from_snapshot is not None and from_branch is None:raise ValueError('a snapshot requires its source branch')
    if from_branch is not None and (type(from_branch) is not str or not from_branch):raise ValueError('source branch required')
    if from_snapshot is not None and (type(from_snapshot) is not str or not re.fullmatch('[0-9a-f]{64}',from_snapshot)):raise ValueError('invalid source snapshot')
    cow=dict(connection,branch=branch,mode='ask',bootstrap='coding',grammar_registration='inline')
    fork=None
    if from_branch is not None:
        cow.pop('bootstrap');cow['mode']='ask' if from_prefix is not None else 'append_user'
        fork=dict(source_branch=from_branch,snapshot=from_snapshot)
    config=dict(schema=1,source=str(project),source_policy='metadata-free-project-v1',run_id=branch,
        grant=dict(read_paths=sorted(set(read_paths)|set(edit_paths)|set(create_paths)),
                   edit_paths=list(edit_paths),create_paths=list(create_paths),allow_tests=False,allow_shell=True),
        bindings=dict(task=dict(type='Text',value=task)),cow=cow,
        shell=dict(timeout=shell_timeout),profiles=dict(control=profile),
        verification=dict(schema=1,commands=[dict(command=c,disposition='exited',exit_code=0) for c in test_commands]))
    if project_files:
        config['grant']['project_files']=True
        config['verification']=dict(schema=1,selected_checks=True)
        if cad is None and blender is None:
            config['profiles']['project-views']=dict(kind='image-feedback',source='current')
    if cad is not None and blender is not None:raise ValueError('choose one fixed-domain acceptance policy per run; other tools retain their observations')
    if blender is not None:
        from .blender_tools import validate_blender_config
        if mode!='work' or not project_files:raise ValueError('Blender requires work mode and project files')
        config['blender']=validate_blender_config(blender)
        config['verification']=dict(schema=1,blender=True)
        config['profiles']['cad-views']=dict(kind='image-feedback',source='current')
        config['bindings']['task']['value']+=('\nUse inspect_scene on ordinary project Python to create scene.blend, independently reopen it, render controlled views and a 24-frame 12fps animation. The host runs Blender 4.5.3, CPU Cycles, through stdio MCP. Coordinates are Z-up; the controlled front camera looks from negative Y, side from positive X, and top from positive Z. Script entry runs in /work; save scene.blend there. No external assets or network. The .blend, movie and views are immutable workflow exports outside the source directory; they are not source files. A current successful inspect_scene receipt plus finish is the scene completion path. Views become stale after any source edit. The scene must have visible mesh objects and a useful transform animation.\n')
    if cad is not None:
        from .cad_config import validate_cad_config
        if mode!='work' or not project_files:raise ValueError('CAD requires work mode and project file access')
        config['cad']=validate_cad_config(cad)
        config['verification']=dict(schema=1,cad=True)
        config['profiles']['cad-views']=dict(kind='image-feedback',source='current')
        config['bindings']['task']['value']+=('\nUse inspect_cad to build ordinary project Python, reopen its STEP, measure fixed requirements and inspect actual views. It requires part.step as the export name. The host fixes requirements; never edit them. Environment: build123d 0.13.0 plus bd_warehouse 0.4.0, millimetres. Standard component types and sizes can be queried inside inspect_cad Python; simple=True omits detailed helical threads. Adding standard hardware still requires an appropriate host acceptance policy, not editing the fixed requirements. The STEP export and views are retained as immutable workflow artifacts outside the source directory. Do not search for part.step in the source workspace or try to import build123d through run_shell; inspect_cad supplies that environment. A successful current inspect_cad receipt plus finish is the CAD completion path. Geometry evidence and views are invalid after source edits.\nFixed requirements: '+json.dumps(cad['requirements'],sort_keys=True))
    if mode!='work':
        config['grant']['allow_shell']=False
        config.pop('shell')
        config['verification']=dict(schema=1,read_only=True)
        config['bindings']['task']['value']='Read-only '+mode+' request. Inspect relevant project files if needed. Answer honestly; do not edit files or run commands.\n\n'+task
    if mode=='work' and remotes:
        from .remote_config import validate_targets
        config['remotes']=validate_targets(remotes)
        config['grant']['remote_targets']=sorted(remotes)
    if selection is not None:
        # Ordinary frozen input provenance, not another workflow or live alias.
        config['bindings']['project_base_choice']=dict(type='Text',value=_bytes(selection).decode())
    if pack is not None:config['context_pack']=pack
    if refresh_receipt is not None:
        config['bindings']['project_base_refresh']=dict(type='Text',value=_bytes(refresh_receipt).decode())
    config=_config(_bytes(config).decode(),prepared_prefix=from_prefix is not None)
    return dict(schema=1,program=BLENDER_PROGRAM if blender is not None else CAD_PROGRAM if cad is not None else READ_PROGRAM if mode!='work' else PROJECT_PROGRAM if project_files else PROGRAM,config=config,fork=fork)
def _prefix_launch(launch):
    config=launch.get('config')
    return (launch.get('fork') is not None and type(config) is dict
        and type(config.get('cow')) is dict and config['cow'].get('mode')=='ask')
def _validate(launch):
    if type(launch) is not dict or set(launch)!={'schema','program','config','fork'} or type(launch['schema']) is not int or launch['schema']!=1:
        raise ValueError('unsupported coding launch')
    config=_config(_bytes(launch['config']).decode(),prepared_prefix=_prefix_launch(launch))
    project=config['grant'].get('project_files',False)
    readonly=config.get('verification')==dict(schema=1,read_only=True)
    expected=BLENDER_PROGRAM if 'blender' in config else CAD_PROGRAM if 'cad' in config else READ_PROGRAM if readonly else PROJECT_PROGRAM if project else PROGRAM
    if 'exploration' in config:expected=exploration_program(expected,config['exploration']['selection'])
    if launch['program']!=expected:raise ValueError('coding program and project grant differ')
    if project and 'blender' not in config and 'cad' not in config and config.get('verification')!=dict(schema=1,selected_checks=True):raise ValueError('project check policy required')
    fork=launch['fork']
    if fork is not None:
        if (type(fork) is not dict or set(fork)!={'source_branch','snapshot'}
                or type(fork['source_branch']) is not str or not fork['source_branch']
                or type(fork['snapshot']) is not str or not re.fullmatch('[0-9a-f]{64}',fork['snapshot'])
                or launch['config']['cow'].get('mode') not in ('append_user','ask')
                or 'bootstrap' in launch['config']['cow']):
            raise ValueError('retained launch must pin an exact source snapshot')
    elif launch['config']['cow'].get('bootstrap')!='coding':
        raise ValueError('new coding launch requires its bootstrap')
def _prepare_default_state_parent(state):
    state=Path(state).absolute()
    xdg=state.parents[2]
    if xdg.is_symlink():raise ValueError('XDG state home must not be a symlink')
    xdg.mkdir(parents=True,exist_ok=True,mode=0o700)
    info=xdg.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.getuid():
        raise ValueError('XDG state home must be an owned real directory')
    for directory in (state.parents[1],state.parent):
        try:directory.mkdir(mode=0o700)
        except FileExistsError:pass
        info=directory.lstat()
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.getuid()
                or stat.S_IMODE(info.st_mode)&0o077):
            raise ValueError('BranchWrite state parents must be private owned directories')

def _state(state,*,create=False,source=None):
    state=Path(state).absolute()
    if state.is_symlink():raise ValueError('state must be a real owned directory')
    if source is not None and state.resolve().is_relative_to(Path(source).resolve()):
        raise ValueError('run state must be outside the source project')
    if create and not state.exists():state.mkdir(mode=0o700)
    info=state.lstat()
    if not stat.S_ISDIR(info.st_mode) or stat.S_IMODE(info.st_mode)!=0o700 or info.st_uid!=os.getuid():
        raise ValueError('state must be an owned directory with mode0700')
    return state
def save_launch(state,launch):
    import fcntl
    _validate(launch)
    state=_state(state,create=True,source=launch['config']['source'])
    raw=_bytes(dict(launch=launch,sha256=hashlib.sha256(_bytes(launch)).hexdigest()))+b'\n'
    if len(raw)>MAX_LAUNCH_BYTES:raise ValueError('coding launch is too large')
    path=state/'coding-launch.json'
    # Serialize trusted setup publishers; atomic rename leaves one file link
    # even if the process stops before staging cleanup. No workflow lives here.
    lockfd=os.open(state/'.coding-launch.lock',os.O_RDWR|os.O_CREAT|getattr(os,'O_NOFOLLOW',0),0o600)
    with os.fdopen(lockfd,'r+b') as lock:
        info=os.fstat(lock.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1 or info.st_uid!=os.getuid() or stat.S_IMODE(info.st_mode)!=0o600:
            raise ValueError('invalid coding setup lock')
        fcntl.flock(lock.fileno(),fcntl.LOCK_EX)
        if path.exists() or path.is_symlink():
            if read_launch(state)!=launch:raise ValueError('run setup changed; use a new run state')
            return
        fd,name=tempfile.mkstemp(prefix='.coding-launch-',dir=state);temporary=Path(name)
        try:
            with os.fdopen(fd,'wb') as stream:
                os.fchmod(stream.fileno(),0o600);stream.write(raw);stream.flush();os.fsync(stream.fileno())
            os.replace(temporary,path)
            directory=os.open(state,os.O_RDONLY|getattr(os,'O_DIRECTORY',0))
            try:os.fsync(directory)
            finally:os.close(directory)
        finally:
            if temporary.exists():temporary.unlink()
def read_launch(state):
    state=_state(state)
    fd=os.open(state/'coding-launch.json',os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_NONBLOCK',0))
    with os.fdopen(fd,'rb') as stream:
        info=os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1 or info.st_uid!=os.getuid() or stat.S_IMODE(info.st_mode)!=0o600:
            raise ValueError('coding launch must be a private owned regular file')
        raw=stream.read(MAX_LAUNCH_BYTES+1)
    if len(raw)>MAX_LAUNCH_BYTES:raise ValueError('coding launch is too large')
    envelope=json.loads(raw)
    if type(envelope) is not dict or set(envelope)!={'launch','sha256'} or envelope['sha256']!=hashlib.sha256(_bytes(envelope['launch'])).hexdigest():
        raise ValueError('coding launch integrity check failed')
    _validate(envelope['launch'])
    return envelope['launch']
def _client(state,launch):
    cow=launch['config']['cow']
    return CowClient.http(cow['endpoint_url'],journal=OperationJournal(Path(state)/'cow-operations'),api_key=key_for_connection(cow),endpoint_pin=cow['endpoint_pin'],notice_handler=_source_notice)
def run_saved(state,*,max_steps=1024,control=None,progress=None,model_pause=None):
    if type(max_steps) is not int or max_steps<=0:raise ValueError('finite positive step budget required')
    launch=read_launch(state)
    if launch['fork'] is not None:
        fork=launch['fork'];operation='bw-code-fork-'+hashlib.sha256(_bytes(launch)).hexdigest()[:40]
        # The original pinned source and journal ID survive retries. An uncertain
        # fork remains uncertain; never select a newer head or invent a new ID.
        try:
            _client(state,launch).fork(fork['source_branch'],fork['snapshot'],launch['config']['cow']['branch'],operation)
        except OperationIndeterminate as exc:
            raise OperationIndeterminate('Original fork operation '+operation+' is unresolved; reconcile its original journal intent before continuing') from exc
    options={}
    if control is not None:options['control']=control
    if progress is not None:options['progress']=progress
    if model_pause is not None:options['model_pause']=model_pause
    return execute('run',launch['program'],_bytes(launch['config']).decode(),state,max_steps=max_steps,**options,**({'prepared_prefix':True} if _prefix_launch(launch) else {}))
def start(args,*,control=None,progress=None,model_pause=None):
    if type(args.max_steps) is not int or args.max_steps<=0:raise ValueError('finite positive step budget required')
    if getattr(args,'_generated_state',False):
        project=Path(args.project).resolve(strict=True)
        candidate=Path(args.state).absolute().resolve()
        if candidate.is_relative_to(project):raise ValueError('default run state must stay outside the source project')
        _prepare_default_state_parent(args.state)
    # An existing run must keep its original root and admitted configuration.
    # Fail before capturing new sources or publishing a different derived pack.
    if getattr(args,'refresh_context_pack',False) and (Path(args.state)/'coding-launch.json').exists():
        raise ValueError('refresh applies only to a new run state; use resume for admitted work')
    from .__main__ import _source
    connection=json.loads(_source(args.connection),object_pairs_hook=_pairs)
    task=getattr(args,'task',None)
    if task is None:
        task_file=getattr(args,'task_file',None)
        if task_file is None:raise ValueError('inline task text or task file is required')
        task=_source(task_file)
    from .project_scope import expand_directories
    read_dirs=getattr(args,'read_dir',())
    edit_dirs=getattr(args,'edit_dir',())
    reads=list(args.read)+expand_directories(args.project,read_dirs) if read_dirs else args.read
    edits=list(args.edit)+expand_directories(args.project,edit_dirs) if edit_dirs else args.edit
    catalog_path=getattr(args,'project_bases',None)
    proposal_path=getattr(args,'base_choice',None)
    base_revision=getattr(args,'base_revision',None)
    reserve=getattr(args,'base_reserve_tokens',None)
    auto_base=getattr(args,'auto_base',False)
    if auto_base and proposal_path is not None:raise ValueError('choose --auto-base or --base-choice, not both')
    if auto_base and any(value is None for value in (catalog_path,base_revision,reserve)):
        raise ValueError('--auto-base requires --project-bases, --base-revision and --base-reserve-tokens')
    if not auto_base and any(value is not None for value in (catalog_path,proposal_path,base_revision,reserve)):
        if any(value is None for value in (catalog_path,proposal_path,base_revision,reserve)):
            raise ValueError('provide --project-bases, --base-choice, --base-revision and --base-reserve-tokens together')
    catalog=None if catalog_path is None else json.loads(_source(catalog_path),object_pairs_hook=_pairs)
    proposal=None if proposal_path is None else _source(proposal_path)
    context_pack=getattr(args,'context_pack',None)
    context_pack_id=getattr(args,'context_pack_id',None)
    project_receipt_sha256=None
    build_project_context=getattr(args,'build_project_context',False)
    source_branches=tuple(getattr(args,'context_source_branch',()) or ())
    if source_branches and not build_project_context:
        raise ValueError('--context-source-branch requires --build-project-context')
    if build_project_context:
        if context_pack is not None or context_pack_id is not None or getattr(args,'refresh_context_pack',False):
            raise ValueError('choose project context building or an existing/refreshable context pack')
        if (args.from_branch is not None or getattr(args,'from_prefix',None) is not None
                or args.from_snapshot is not None or catalog_path is not None
                or proposal_path is not None or auto_base):
            raise ValueError('project-built context starts a new root; choose one explicit source path')
        # Validate ordinary coding admission before touching project context
        # or querying saved branches. This pass is pure and has no I/O effects.
        build_launch(args.project,task,connection,branch=args.branch,project_files=getattr(args,'project_files',False),
            read_paths=sorted(set(reads)),edit_paths=sorted(set(edits)),create_paths=args.create,
            test_commands=args.test_command,from_branch=None,from_prefix=None,from_snapshot=None,
            shell_timeout=args.shell_timeout,sampler=getattr(args,"sampler","greedy"),
            context_pack=None,context_pack_id=None,refresh_context_pack=False)
        from .project_context import append_event,capture_context_pack,read_stable_branch,resume_context_pack
        from .cow_client import CowClient,OperationJournal
        state=_state(args.state,create=True,source=args.project)
        pack_info=resume_context_pack(args.project,state,read_files=tuple(args.read),
            read_dirs=tuple(read_dirs),branch_names=source_branches,output=state/'context-packs')
        if pack_info is None:
            branches=()
            if source_branches:
                append_event(state,'SOURCE_BRANCH_READ_STARTED',branch_names=list(source_branches))
                client=CowClient.http(connection['endpoint_url'],
                    journal=OperationJournal(state/'cow-operations'),
                    api_key=key_for_connection(connection),endpoint_pin=connection['endpoint_pin'],
                    notice_handler=_source_notice)
                branches=tuple(read_stable_branch(client,name) for name in source_branches)
            from datetime import datetime,timezone
            pack_info=capture_context_pack(args.project,state,read_files=tuple(args.read),
                read_dirs=tuple(read_dirs),branches=branches,
                as_of=datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),
                output=state/'context-packs')
        context_pack=Path(pack_info['pack_path'])
        context_pack_id=pack_info['pack_id']
        from .base_cli import _read_private_json
        source_receipt=_read_private_json(state/'context-source-receipt.json')
        project_receipt_sha256=hashlib.sha256(_bytes(source_receipt)).hexdigest()
    launch=build_launch(args.project,task,connection,branch=args.branch,project_files=getattr(args,'project_files',False),
        read_paths=sorted(set(reads)),edit_paths=sorted(set(edits)),create_paths=args.create,
        test_commands=args.test_command,from_branch=args.from_branch,
        from_prefix=getattr(args,'from_prefix',None),from_snapshot=args.from_snapshot,shell_timeout=args.shell_timeout,sampler=getattr(args,"sampler","greedy"),base_catalog=catalog,base_proposal=proposal,base_revision=base_revision,base_reserve_tokens=reserve,context_pack=context_pack,context_pack_id=context_pack_id,refresh_context_pack=getattr(args,'refresh_context_pack',False),auto_base=auto_base,cad=None if getattr(args,'cad_config',None) is None else json.loads(Path(args.cad_config).read_text(),object_pairs_hook=_pairs),blender=None if getattr(args,'blender_config',None) is None else json.loads(Path(args.blender_config).read_text(),object_pairs_hook=_pairs))
    if project_receipt_sha256 is not None:
        launch['config']['bindings']['project_context_receipt_sha256']=dict(
            type='Text',value=project_receipt_sha256)
    if getattr(args,'explore',False):
        enable_exploration(launch,getattr(args,'approach',None),selection=getattr(args,'select_candidate','verified-first'))
    elif getattr(args,'approach',None):raise ValueError('--approach requires --explore')
    existing=Path(args.state)/'coding-launch.json'
    if launch['fork'] is not None and launch['fork']['snapshot'] is None:
        if existing.exists():
            prior=read_launch(args.state)
            if prior['fork'] is not None and prior['fork']['source_branch']==launch['fork']['source_branch']:
                launch['fork']['snapshot']=prior['fork']['snapshot']
        if launch['fork']['snapshot'] is None:
            # Read-only selection before publication. The snapshot,not a live
            # branch name,is saved before any mutating setup/inference request.
            head=_client(args.state,launch).head(launch['fork']['source_branch'])
            launch['fork']['snapshot']=head.root if launch['config']['cow']['mode']=='ask' else head.tip
    save_launch(args.state,launch)
    options={}
    if control is not None:options['control']=control
    if progress is not None:options['progress']=progress
    if model_pause is not None:options['model_pause']=model_pause
    return run_saved(args.state,max_steps=args.max_steps,**options)
