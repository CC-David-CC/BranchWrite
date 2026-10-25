"""CLI bindings for the one Interpreter. JSON here is host configuration only.

No model/tool loop lives here. CLI restart reopens the canonical RuntimeLog and
uses original source bindings; it never rebases a resumed workflow on a new tip.
"""
import hashlib
import json
import os
from pathlib import Path
from .client_setup import key_for_connection
import stat
import time
from contextlib import ExitStack
from .records import RuntimeLog,Artifact,decode
from .kernel import FrameKernel
from .execution import Executor,Grant
from .tool_registry import ToolRegistry
from .interpreter import Interpreter,Value,AdmissionError,_SUPPORTED,validate_tool_feedback
from .cow_client import CowClient,OperationJournal,OperationIndeterminate
from .model_dispatch import ModelAdapter
from .language import parse
from .coding_defaults import generation_profile,system_prefix,controller_prefix
from .model_inputs import model_content

def _artifact_exports(log,outcomes):
    """Return only rooted, exact native/document artifacts from visible results."""
    exports=[]
    media={'part.step':'application/step','scene.blend':'application/x-blender','animation.mp4':'video/mp4',
           'index.html':'text/html','render.json':'application/json'}
    for frame,value in outcomes:
        if value['tool'] not in ('inspect_cad','inspect_scene','build_pdf','render_pdf'):continue
        details=value['details']
        for item in details.get('asset_manifest',[]):
            ref=Artifact(item['sha256'],item['bytes']);log.read_artifact(ref);name=item['name']
            kind='image/png' if name.endswith('.png') else 'application/pdf' if name.endswith('.pdf') else media[name]
            exports.append(dict(name=name,sha256=ref.sha256,bytes=ref.size_bytes,media_type=kind,
                path=str(log.artifacts/ref.sha256),tool_frame=frame['id'],source_id=details.get('source_id',details.get('pdf_sha256'))))
    return exports

def _progress_notice(event):
    """Display-only status; stdout and canonical workflow records stay separate."""
    import sys
    messages={'model_started':'Working on model output.',
              'model_step_returned':'Model step recorded.',
              'tool_started':'Running a tool.',
              'tool_returned':'Tool result recorded.'}
    from .tool_progress import detail_message
    detail=detail_message(event)
    if detail is not None:message=detail
    elif event.startswith('pause:'):message=event[len('pause:'):]
    elif event in messages:message=messages[event]
    else:return
    try:print('[BranchWrite] '+message,file=sys.stderr,flush=True)
    except OSError:pass

def _source_notice(event):
    """Display provisional work observations; stdout stays machine-readable."""
    import sys
    kind=event['event']
    field='history_tokens' if kind=='source_recomputation_started' else 'prefix_forward_tokens'
    count=event.get(field)
    shown=str(count) if type(count) is int and count>=0 else 'unknown'
    if kind=='source_recomputation_started':
        message='Recomputing retained context: '+shown+' input positions.'
    elif kind=='source_recomputed':
        message='Recomputed '+shown+' input positions; this request paid the prefix cost.'
    else:
        message='Context recomputation failed: '+json.dumps(event.get('error','unknown'),ensure_ascii=True)
    print('[COW] '+message,file=sys.stderr,flush=True)

def _pairs(items):
    result={}
    for key,value in items:
        if key in result:raise AdmissionError('duplicate host configuration field')
        result[key]=value
    return result

def _browser_config(spec):
    """Admit the host geometry menu once for validation and actual execution."""
    from .browser_capture import BrowserConfig
    required={'executable','width','height','timeout'}
    if (type(spec) is not dict or not required<=set(spec) or set(spec)-required-{'viewports'}
            or type(spec['executable']) is not str):
        raise AdmissionError('closed host browser configuration required')
    menu=()
    if 'viewports' in spec:
        choices=spec['viewports']
        if type(choices) is not dict or not 1<=len(choices)<=8:
            raise AdmissionError('bounded named host viewport mapping required')
        rows=[]
        for name,size in choices.items():
            if type(size) is not list or len(size)!=2:
                raise AdmissionError('viewport geometry must be a two-integer list')
            rows.append((name,*size))
        menu=tuple(rows)
    return BrowserConfig(Path(spec['executable']),spec['width'],spec['height'],spec['timeout'],viewports=menu)

def _shell_config(spec,*,validate_only=False):
    from .terminal import ShellConfig,validate_shell_parameters
    if type(spec) is not dict or 'timeout' not in spec or set(spec)-{'timeout','expected_hostname'}:raise AdmissionError('closed host shell configuration required')
    # Parsing a launch is data validation. The execution path below still
    # admits pinned host binaries before any model work; never trust overflow
    # UID65534 or relax root ownership to make nested configuration tests pass.
    validate_shell_parameters(spec['timeout'],spec.get('expected_hostname'))
    if validate_only:return None
    return ShellConfig(timeout=spec['timeout'],expected_hostname=spec.get('expected_hostname'))

def _config(text,*,prepared_prefix=False):
    if type(prepared_prefix) is not bool:raise AdmissionError('explicit source validation context required')
    try:config=json.loads(text,object_pairs_hook=_pairs,parse_constant=lambda _: (_ for _ in ()).throw(AdmissionError('nonfinite host configuration value')))
    except (ValueError,TypeError) as exc:raise AdmissionError('invalid host configuration') from exc
    required={'schema','source','run_id','grant','bindings'}
    if type(config) is not dict or (not required<=set(config) or set(config)-required-{'source_policy','cow','profiles','verification','browser','shell','context_pack','remotes','cad','blender','exploration','tool_feedback'}) or type(config['schema']) is not int or config['schema']!=1:
        raise AdmissionError('unsupported host configuration fields/schema; credentials belong in BW_COW_API_KEY')
    if 'tool_feedback' in config:validate_tool_feedback(config['tool_feedback'])
    if 'exploration' in config:
        from .exploration import budget
        spec=config['exploration']
        if (type(spec) is not dict or set(spec)!={'schema','approaches','selection','budget'} or spec['schema']!=1
                or type(spec['approaches']) is not dict or set(spec['approaches'])!={'first','second'}
                or any(type(s) is not str or not s.strip() or len(s.encode())>8192 for s in spec['approaches'].values())
                or spec['selection'] not in ('verified-first','first','second') or config.get('remotes')):
            raise AdmissionError('Closed isolated exploration configuration required')
        budget(spec['budget'])
    if type(config['source']) is not str or not Path(config['source']).is_absolute():raise AdmissionError('absolute source path required')
    if type(config['run_id']) is not str or not config['run_id'] or len(config['run_id'])>128:raise AdmissionError('bounded run ID required')
    grant=config['grant']
    required_grant={'edit_paths','read_paths','create_paths','allow_tests'}
    if (type(grant) is not dict or not required_grant<=set(grant)
            or set(grant)-required_grant-{'capture_paths','interact_paths','asset_paths','allow_shell','mode_paths','mode_mask','output_paths','project_files','remote_targets'} or type(grant['allow_tests']) is not bool):
        raise AdmissionError('explicit closed host grant required')
    for name in ('edit_paths','read_paths','create_paths','capture_paths','interact_paths','asset_paths','mode_paths','output_paths'):
        if name not in grant:continue
        if type(grant[name]) is not list or any(type(v) is not str for v in grant[name]):raise AdmissionError('grant paths must be string lists')
    names=grant.get('remote_targets',[])
    if type(names) is not list or any(type(v) is not str for v in names):raise AdmissionError('explicit remote target name grants required')
    from .remote_config import validate_targets
    try:remotes=validate_targets(config.get('remotes',{}))
    except (ValueError,TypeError) as error:raise AdmissionError('invalid remote capability configuration') from error
    if any(name not in remotes for name in names):raise AdmissionError('remote target grant has no host definition')
    if 'allow_shell' in grant and type(grant['allow_shell']) is not bool:raise AdmissionError('shell grant must be an exact boolean')
    if 'source_policy' in config and config['source_policy']!='metadata-free-project-v1':raise AdmissionError('unsupported source input policy')
    if config.get('source_policy')=='metadata-free-project-v1':
        paths=(path for name,values in grant.items() if name.endswith('_paths') for path in values)
        if any('.git' in Path(path).parts for path in paths):
            raise AdmissionError('project grants cannot expose Git administration')
    if config.get('verification')==dict(schema=1,read_only=True) and ('cad' in config or 'blender' in config):raise AdmissionError('read-only configuration cannot enable CAD or Blender execution')
    if 'blender' in config:
        from .blender_tools import validate_blender_config
        validate_blender_config(config['blender'])
    if 'cad' in config:
        from .cad_config import validate_cad_config
        validate_cad_config(config['cad'])
    if 'shell' in config:_shell_config(config['shell'],validate_only=True)
    if grant.get('allow_shell',False) and 'shell' not in config:raise AdmissionError('shell grant requires explicit host shell configuration')
    captures=grant.get('capture_paths',[])
    if any(path not in grant['read_paths'] for path in captures):raise AdmissionError('capture paths require explicit read grants')
    if any(path not in captures or path not in grant['read_paths'] for path in grant.get('interact_paths',[])):
        raise AdmissionError('interaction paths require explicit capture and read grants')
    assets=grant.get('asset_paths',[])
    if any(path not in grant['read_paths'] for path in assets):
        raise AdmissionError('assets require explicit read grants')
    # Grant admission owns canonical paths, bounds, duplicates and resource types.
    Grant(tuple(grant['edit_paths']),grant['allow_tests'],
          read_paths=tuple(grant['read_paths']),create_paths=tuple(grant['create_paths']),
          capture_paths=tuple(captures),interact_paths=tuple(grant.get('interact_paths',[])),
          asset_paths=tuple(assets),allow_shell=grant.get('allow_shell',False),mode_paths=tuple(grant.get('mode_paths',[])),mode_mask=grant.get('mode_mask',0),output_paths=tuple(grant.get('output_paths',[])),project_files=grant.get('project_files',False),remote_targets=tuple(names))
    browser=config.get('browser')
    if browser is not None:
        _browser_config(browser)
    if captures and browser is None:raise AdmissionError('capture grants require a host browser configuration')
    if 'profiles' not in config:config['profiles']={'control':generation_profile()}
    if type(config['bindings']) is not dict or type(config['profiles']) is not dict:raise AdmissionError('named bindings/profiles required')
    for name,value in config['bindings'].items():
        if type(value) is not dict or set(value)!={'type','value'} or value['type'] not in ('Text','ToolProposal','ModelInput'):
            raise AdmissionError('CLI initial data must be explicitly typed text/proposal/model-input values')
        if value['type']=='ModelInput':
            if type(value['value']) not in (str,list):raise AdmissionError('typed ModelInput requires text or ordered parts')
            try:model_content(value['value'])
            except ValueError as exc:raise AdmissionError('invalid model input: '+str(exc)) from exc
        elif type(value['value']) is not str:raise AdmissionError('text/proposal value must be text')
    if any(name in config['bindings'] for name in ('world','current','host-config-sha256')):raise AdmissionError('reserved initial binding name')
    cow=config.get('cow')
    if cow is not None:
        keys={'endpoint_url','endpoint_pin','model_contract_id','execution_profile_id','eos_tokens','branch','mode'}
        if type(cow) is not dict or not keys<=set(cow) or set(cow)-keys-{'bootstrap','grammar_registration','controller_prefix'} or cow['mode'] not in ('ask','append_user') or any(type(cow[k]) is not str or not cow[k] for k in keys-{'eos_tokens'}):
            raise AdmissionError('explicit closed COW source/profile configuration required')
        if 'bootstrap' in cow and (cow['bootstrap']!='coding' or cow['mode']!='ask'):raise AdmissionError('coding bootstrap requires a new context-only ask boundary')
        if 'grammar_registration' in cow and (cow['grammar_registration']!='inline' or not (cow.get('bootstrap')=='coding' or ('bootstrap' not in cow and (cow['mode']=='append_user' or (prepared_prefix and cow['mode']=='ask'))))):
            raise AdmissionError('inline grammar registration requires coding bootstrap or an explicit retained-context task')
        if 'controller_prefix' in cow and (cow['controller_prefix'] not in ('compact','compact-finish-request') or cow.get('bootstrap')!='coding' or cow.get('grammar_registration')!='inline'):
            raise AdmissionError('compact controller instructions require a new inline coding root')
        if type(cow['eos_tokens']) is not list or not cow['eos_tokens'] or any(type(t) is not int or t<0 for t in cow['eos_tokens']):raise AdmissionError('actual EOS token IDs required')
    if 'context_pack' in config:
        import re
        pack=config['context_pack']
        if (type(pack) is not dict or set(pack)!={'path','pack_id'}
                or type(pack['path']) is not str or not Path(pack['path']).is_absolute()
                or type(pack['pack_id']) is not str or not re.fullmatch('[0-9a-f]{64}',pack['pack_id'])):
            raise AdmissionError('context_pack requires an absolute path and SHA-256 pack_id pin')
        if cow is None or cow.get('bootstrap')!='coding':
            raise AdmissionError('reference packs require a new coding bootstrap; saved roots stay immutable')
    return config

def _retained_bootstrap(client, cow, seed):
    operation = 'bw-root-' + seed
    saved = client.journal.read(operation)
    if saved is not None:
        body = json.loads(client.journal.decode_body(saved))
        if (saved.get('method') != 'POST' or saved.get('path') != '/cow/text/context'
                or saved.get('branch') != cow['branch']
                or type(body) is not dict
                or set(body) != {'branch', 'namespace_id', 'messages', 'operation_id', 'stream'}
                or body.get('branch') != cow['branch'] or body.get('operation_id') != operation
                or body.get('stream') is not True):
            raise AdmissionError('retained bootstrap intent differs from this coding setup')
    return saved

def _coding_bootstrap(client, cow, config, seed, registry, *, task_bound, output_paths, command_requirements):
    """Recover acknowledged setup locally, or admit one fresh exact prefix."""
    operation = 'bw-root-' + seed
    saved = _retained_bootstrap(client, cow, seed)
    if saved is not None:
        if saved.get('state') != 'complete':
            raise OperationIndeterminate('Original context bootstrap ' + operation
                + ' is unresolved; no automatic resend or prefix replacement is permitted')
        prepared = client.read_completed_generation(operation)
        receipt = prepared.receipt
        if (receipt.branch.name != cow['branch'] or receipt.branch.tip != receipt.snapshot
                or receipt.branch.root != receipt.snapshot
                or receipt.raw.get('model_contract_id') != cow['model_contract_id']
                or receipt.raw.get('execution_profile_id') != cow['execution_profile_id']):
            raise AdmissionError('retained bootstrap receipt differs from this coding root/profile')
        return receipt.branch
    pack = config.get('context_pack')
    pack_args = {} if pack is None else dict(context_pack=pack['path'], context_pack_id=pack['pack_id'])
    if cow.get('grammar_registration') == 'inline' and task_bound:
        prefix = controller_prefix(registry.model_schema(), style=cow.get('controller_prefix','worked-examples'), **pack_args)
    else:
        prefix = system_prefix(registry.model_schema(),
            command_output_paths=output_paths,
            command_requirements=command_requirements, **pack_args)
    namespace = client.create_namespace('BranchWrite coding', 'bw-ns-' + seed)['namespace_id']
    prepared = client.load_context(cow['branch'], namespace,
                                  [dict(role='system', content=prefix)], operation)
    return prepared.receipt.branch

def _candidate_worlds(state,registry,kernel,verification):
    """Owned copies with frozen grants; no shared mutation targets."""
    root=state/'candidates'
    if not root.exists():root.mkdir(mode=0o700)
    info=root.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_mode&0o077 or info.st_uid!=os.getuid():
        raise AdmissionError('Candidate container must be an owned private real directory')
    worlds={}
    for name in ('first','second'):
        path=root/name
        if not path.exists():
            if kernel.frames():raise AdmissionError('Saved candidate world is missing; refusing to recreate it')
            ex=Executor.create(registry.executor.workspace,path,browser=registry._browser,shell=registry._shell)
        else:
            info=path.lstat()
            if not stat.S_ISDIR(info.st_mode) or info.st_mode&0o077 or info.st_uid!=os.getuid():
                raise AdmissionError('Candidate world must be an owned private real directory')
            ex=Executor(registry.executor.workspace,path,path/'workspace',browser=registry._browser,shell=registry._shell)
        if registry._grant.allow_tests:ex.check_test_boundary()
        if registry._grant.allow_shell:ex.check_shell_boundary()
        child=ToolRegistry(ex,registry._grant,test_timeout=registry._test_timeout,
            cad=registry._cad,blender=registry._blender,pdf=registry._pdf)
        worlds[name]=dict(registry=child,verification=verification)
    return worlds


def execute(command,source,config_text,state,*,max_steps,prepared_prefix=False,control=None,progress=None,model_pause=None):
    if model_pause is not None and not callable(model_pause):raise AdmissionError('Read-only model pause callback required')
    pause_notice=lambda message:(progress or _progress_notice)('pause:'+message)
    # Only the sealed prepared-prefix launcher supplies this validation context.
    # Raw configs keep the existing no-guessed-boundary guard. The server still
    # validates idle/context-only state before any token work.
    config=_config(config_text,prepared_prefix=prepared_prefix)
    nodes=parse(source);pending=list(nodes)
    while pending:
        node=pending.pop()
        if node.opcode not in _SUPPORTED|{'FLOW'}:raise AdmissionError('unsupported execution operation: '+node.opcode)
        pending.extend(node.body)
    # Data parsing is portable; execution admission is host-bound. Check the
    # actual pinned shell/hostname before creating state or contacting COW.
    shell=_shell_config(config['shell']) if 'shell' in config else None
    state=Path(state).absolute()
    if state.exists() or state.is_symlink():
        info=state.lstat()
        if not stat.S_ISDIR(info.st_mode) or stat.S_IMODE(info.st_mode)!=0o700:raise AdmissionError('state must be an owned real directory with mode0700')
    else:state.mkdir(mode=0o700,parents=False)
    with RuntimeLog(state/'ledger') as log, ExitStack() as effects:
        kernel=FrameKernel(log)
        world=state/'world';source_dir=Path(config['source'])
        browser=None
        if 'browser' in config:
            browser=_browser_config(config['browser'])
        if not world.exists():
            if kernel.frames():raise AdmissionError('owned workspace missing; do not recreate under a saved workflow')
            executor=Executor.create(source_dir,world,browser=browser,shell=shell,project_input=config.get('source_policy')=='metadata-free-project-v1')
        else:
            if world.is_symlink() or not world.is_dir():raise AdmissionError('owned world must be a real directory')
            executor=Executor(source_dir,world,world/'workspace',browser=browser,shell=shell)
        spec=config['grant'];grant=Grant(tuple(spec['edit_paths']),spec['allow_tests'],create_paths=tuple(spec['create_paths']),read_paths=tuple(spec['read_paths']),capture_paths=tuple(spec.get('capture_paths',[])),interact_paths=tuple(spec.get('interact_paths',[])),asset_paths=tuple(spec.get('asset_paths',[])),allow_shell=spec.get('allow_shell',False),mode_paths=tuple(spec.get('mode_paths',[])),mode_mask=spec.get('mode_mask',0),output_paths=tuple(spec.get('output_paths',[])),project_files=spec.get('project_files',False),remote_targets=tuple(spec.get('remote_targets',[])))
        # Candidate tests need their own sandbox even when the trusted CLI is
        # isolated. Reject an unusable execution boundary before any COW call.
        # A completed workflow replays locally without launching a new process.
        frames=kernel.frames()
        if grant.allow_tests and (not frames or kernel.frame('program')['state']!='Closed'):
            executor.check_test_boundary()
        if grant.allow_shell and (not frames or kernel.frame('program')['state']!='Closed'):
            executor.check_shell_boundary()
        from .remote_config import load_targets
        remote_targets=load_targets({name:config['remotes'][name] for name in grant.remote_targets}) if grant.remote_targets else ()
        from .cad_config import load_cad_config
        cad=load_cad_config(config['cad']) if 'cad' in config else None
        from .blender_tools import load_blender_config
        blender=load_blender_config(config['blender']) if 'blender' in config else None
        from .pdf_tools import PdfCapability
        pdf=PdfCapability() if grant.project_files else None
        registry=ToolRegistry(executor,grant,remote_targets=remote_targets,cad=cad,blender=blender,pdf=pdf);adapter=None
        parallel={}
        if 'exploration' in config:
            from .parallel_dispatch import DispatchPool
            pool=effects.enter_context(DispatchPool(config['exploration']['budget']['max_parallel']))
            worlds=_candidate_worlds(state,registry,kernel,config.get('verification'))
            parallel=dict(worlds=worlds,parallel_budgets={'explore':config['exploration']['budget']},dispatcher=pool)
        bindings={k:Value(v['type'],v['value']) for k,v in config['bindings'].items()}
        # This digest prevents changed source/grants/endpoint/branch declarations
        # being treated as continuation of an already admitted run. No secret.
        canonical=json.dumps(config,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()
        bindings['host-config-sha256']=Value('Text',hashlib.sha256(canonical).hexdigest())
        if config.get('source_policy')=='metadata-free-project-v1':
            from .project_baseline import BINDING,capture,load,parse_reference,reference_text
            if kernel.frames():
                root=kernel.frame('program')
                original=decode(log.read_artifact(Artifact(*root['inputs'])))
                saved=original['bindings'].get(BINDING)
                if type(saved) is not tuple or len(saved)!=2 or saved[0]!='Text':
                    raise AdmissionError('saved project input manifest missing; no automatic migration')
                # Validate retained payloads before any dispatch; never recapture
                # from a workspace that may already contain tool effects.
                load(log,parse_reference(saved[1]))
                bindings[BINDING]=Value(*saved)
            else:
                bindings[BINDING]=Value('Text',reference_text(capture(log,registry)))
        if config.get('cow',{}).get('grammar_registration')=='inline' and ('task' in bindings or 'bootstrap' not in config['cow']):
            from .coding_defaults import continuation_input
            task=bindings.get('task')
            if task is None or task.type not in ('Text','ModelInput'):
                raise AdmissionError('coding continuation requires an explicit task input')
            requirements=tuple((row['command'],row['disposition'],row['exit_code'])
                for row in config.get('verification',{}).get('commands',[]))
            completion_policy=('cad-geometry-and-finish' if config.get('verification')==dict(schema=1,cad=True) else 'blender-scene-and-finish' if config.get('verification')==dict(schema=1,blender=True) else None)
            bindings['task']=Value(task.type,continuation_input(task.data,registry.model_schema(),command_requirements=requirements,**({} if completion_policy is None else dict(completion_policy=completion_policy))))
            if 'exploration' in config:
                for name in ('first','second'):
                    value=bindings['approach-'+name]
                    bindings['approach-'+name]=Value('Text',continuation_input(value.data,registry.model_schema(),
                        command_requirements=requirements,**({} if completion_policy is None else dict(completion_policy=completion_policy))))

        if 'cow' in config:
            cow=config['cow'];client=CowClient.http(cow['endpoint_url'],journal=OperationJournal(state/'cow-operations'),api_key=key_for_connection(cow),endpoint_pin=cow['endpoint_pin'],notice_handler=_source_notice)
            # Finished work replays the original ledger locally. Unfinished
            # work must still validate the server before any COW operation.
            if not frames or kernel.frame('program')['state']!='Closed':
                client.require_capabilities(cow['model_contract_id'],cow['execution_profile_id'],
                    required=('text','inline_grammars') if cow.get('grammar_registration')=='inline' else ('text',))
            adapter=ModelAdapter(client,run_id=config['run_id'],model_contract_id=cow['model_contract_id'],execution_profile_id=cow['execution_profile_id'],eos_tokens=tuple(cow['eos_tokens']),model_pause=model_pause,pause_notice=pause_notice)
            runtime=Interpreter(kernel,registry,adapter=adapter,profiles=config['profiles'],verification=config.get('verification'),progress=progress or _progress_notice,tool_feedback=config.get('tool_feedback'),**parallel)
            runtime.preflight(source,{**{name:value.type for name,value in bindings.items()},'world':'World','current':'COWSource'})
            if cow.get('grammar_registration')=='inline':
                # Full pure preflight above must succeed before publishing metadata.
                # This operation is immutable registration,not model execution.
                # A lost acknowledgment replays only the original journaled bytes.
                from .coding_defaults import grammar_registry
                from .cow_client import OperationIndeterminate
                registration_id='bw-grammar-'+hashlib.sha256(canonical+source.encode('utf8')).hexdigest()[:40]
                direct=any(profile.get('grammar_state')=='BW_TOOLS_DIRECT' for profile in config['profiles'].values())
                try:registered=client.register_grammars(grammar_registry(registry,direct=direct),registration_id)
                except OperationIndeterminate:registered=client.replay_original(registration_id)
                adapter=ModelAdapter(client,run_id=config['run_id'],model_contract_id=cow['model_contract_id'],
                    execution_profile_id=cow['execution_profile_id'],eos_tokens=tuple(cow['eos_tokens']),model_pause=model_pause,pause_notice=pause_notice,
                    grammar_mapping=registered['states'])
                runtime=Interpreter(kernel,registry,adapter=adapter,profiles=config['profiles'],verification=config.get('verification'),progress=progress or _progress_notice,tool_feedback=config.get('tool_feedback'),**parallel)
                runtime.preflight(source,{**{name:value.type for name,value in bindings.items()},'world':'World','current':'COWSource'})
            if kernel.frames():
                root=kernel.frame('program');original=decode(log.read_artifact(Artifact(*root['inputs'])))
                old=original['bindings']['current'];bindings['current']=Value(*old)
            else:
                if cow.get('bootstrap')=='coding':
                    # Context creation uses the existing original-intent journal.
                    # Retrying setup reuses these IDs/bytes; it never overwrites
                    # a foreign branch or reconstructs a saved model context.
                    seed=hashlib.sha256(canonical+source.encode('utf8')).hexdigest()[:40]
                    head=_coding_bootstrap(client,cow,config,seed,registry,
                        task_bound='task' in bindings,output_paths=grant.output_paths,
                        command_requirements=getattr(runtime._file_policy,"commands",()))
                else:head=client.head(cow['branch'])
                bindings['current']=Value('COWSource',dict(head=dict(name=head.name,revision=head.revision,tip=head.tip,root=head.root),mode=cow['mode']))
        if adapter is None:runtime=Interpreter(kernel,registry,profiles=config['profiles'],verification=config.get('verification'),progress=progress or _progress_notice,tool_feedback=config.get('tool_feedback'),**parallel)
        runtime.start(source,bindings)
        limit=1 if command=='step' else max_steps
        report=runtime.run(max_steps=limit,control=control)
        root=kernel.frame('program')
        result=dict(status=report.status,frame=report.frame,verified=bool(report.value and report.frame=='program' and report.value.get('verified')),state=str(state),result_artifact=None if root['result'] is None else root['result'][0])
        evidence_runtime=runtime;evidence_scope=root
        if report.frame=='program' and report.status=='complete' and 'exploration' in config:
            choices=report.value['bindings']['candidates'][1]['candidates']
            selected=report.value['bindings']['selected'][1]['selected']
            result['candidates']=[dict(name=c['name'],verified=c['verified'],world=c['world'],
                inventory=c['inventory'],result_sha256=c['result'][0]) for c in choices]
            result['selection_rule']=config['exploration']['selection']
            result['selected']=None if selected is None else selected['name']
            if selected is not None:
                evidence_runtime=runtime.worlds[selected['world']]
                evidence_scope=kernel.frame(selected['scope'])
        # Return actual immutable capture artifacts from resumed canonical tool
        # results. They remain in the existing ledger, not an export/cache copy.
        artifacts=[]
        for frame,value in evidence_runtime._visible_tool_outcomes(evidence_scope):
            if value['tool'] not in ('capture_page','interact_page','inspect_cad','inspect_scene') or value['image'] is None:continue
            ref=Artifact(*value['image']);log.read_artifact(ref)
            artifacts.append(dict(media_type='image/png',sha256=ref.sha256,bytes=ref.size_bytes,path=str(log.artifacts/ref.sha256),
                source_path=value['observation'][1] if value['observation'] else 'CAD project',source_sha256=value['observation'][2] if value['observation'] else value['details']['source_id'],tool_frame=frame['id']))
        result['artifacts']=artifacts
        exports=_artifact_exports(log,evidence_runtime._visible_tool_outcomes(evidence_scope))
        if exports:result['exports']=exports
        code=0 if result['verified'] else (1 if report.frame=='program' and report.status=='complete' else 3)
        return code,result
