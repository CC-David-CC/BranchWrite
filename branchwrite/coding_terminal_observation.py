"""Read-only terminal workflow failure evidence, never a correction or lesson.

This observes a closed false BW result with supported settled effects. It does
not infer current files from tool plans or reconstruct unchecked world history.
"""
from hashlib import sha256
from pathlib import Path
import json,re


def _pins():
    from .lesson_capture import _implementation
    return dict(bw_sources=_implementation(),terminal_observer_sha256=sha256(Path(__file__).read_bytes()).hexdigest())


def observe_unverified_workflow(state):
    from .coding_cli import read_launch,_bytes
    from .records import RuntimeLog,Artifact,decode
    from .kernel import FrameKernel
    from .lesson_capture import _native,_LOCAL,_TERMINAL,CaptureRefused
    from .language import parse,render
    from .project_baseline import BINDING,load,parse_reference
    state=Path(state);launch=read_launch(state);cow=launch['config']['cow']
    with RuntimeLog(state/'ledger',read_only=True)as log:
        frames=FrameKernel(log).frames();roots=[v for v in frames if v['parent']is None]
        if len(roots)!=1 or roots[0]['id']!='program' or roots[0]['contract']!=('ProgramResult','record'):
            raise CaptureRefused('One actual coding program root required')
        root=roots[0]
        if root['state']!='Closed':raise CaptureRefused('Workflow is not terminal')
        result=decode(log.read_artifact(Artifact(*root['result'])))[2]
        if result.get('verified')is not False:raise CaptureRefused('Explicit terminal false workflow verdict required')
        inputs=decode(log.read_artifact(Artifact(*root['inputs'])))
        if inputs.get('bindings',{}).get('host-config-sha256')!=('Text',sha256(_bytes(launch['config'])).hexdigest()):
            raise CaptureRefused('Original host configuration changed')
        if log.read_artifact(Artifact(*root['definition']))!=render(parse(launch['program'])).encode():
            raise CaptureRefused('Original coding program changed')
        if any(v['dispatch']is not None and v['state']!='Closed'for v in frames):
            raise CaptureRefused('Unsettled dispatched effect')
        if any(v['contract']==('ModelOutput','record')and v['state']!='Closed'for v in frames):
            raise CaptureRefused('Unsettled logical model output')
        world=inputs['bindings'].get('world');reference=inputs['bindings'].get(BINDING)
        if not isinstance(world,tuple)or len(world)!=2 or world[0]!='World' or not isinstance(reference,tuple)or reference[0]!='Text':
            raise CaptureRefused('Original world and project baseline required')
        baseline=load(log,parse_reference(reference[1]));tools=[]
        expected={'read_file':'read','replace':'applied','replace_text_file':'applied','create_file':'created','create_text_file':'created','set_mode':'mode_changed','finish':'completion_requested'}
        for frame in frames:
            if frame['contract']!=('ToolOutcome','record'):continue
            if frame['state']!='Closed':
                if frame['dispatch']is None:continue
                raise CaptureRefused('Unsettled tool outcome')
            plan=decode(log.read_artifact(Artifact(*frame['inputs'])))
            value=decode(log.read_artifact(Artifact(*frame['result'])))[2]
            if (not isinstance(plan,tuple)or len(plan)!=8 or plan[0]!='bw.tool-plan.v2'
                    or plan[2]!=world[1]or frame['dispatch']is None
                    or value.get('operation_id')!=frame['dispatch'][0]
                    or value.get('plan_sha256')!=frame['inputs'][0]or value.get('tool')!=plan[3]):
                raise CaptureRefused('Tool outcome differs from admitted plan')
            tool=plan[3]
            for stream in ['stdout','stderr']:log.read_artifact(Artifact(*value[stream]))
            if tool in _LOCAL:
                if value.get('disposition')!=expected[tool]or value.get('exit_code')!=0:
                    raise CaptureRefused('Unsupported local outcome; cannot score infrastructure uncertainty')
                if tool=='finish'and value.get('requested_finish')is not True:raise CaptureRefused('Invalid finish request')
            elif tool in _TERMINAL:
                witness=value.get('details',{}).get('isolation',{})
                if (value.get('disposition')!='exited'or type(value.get('exit_code'))is not int
                        or not 0<=value['exit_code']<126 or witness.get('kind')!='bubblewrap-terminal-v1'
                        or witness.get('worker_exited')is not True or witness.get('namespace_members_after')!=[]
                        or not re.fullmatch(r'pid:\[[0-9]+\]',str(witness.get('pid_ns')))):
                    raise CaptureRefused('Terminal outcome lacks settled isolation evidence')
            else:raise CaptureRefused('Unsupported external effect')
            tools.append(dict(frame=frame['id'],tool=tool,result_sha256=frame['result'][0]))
        native=_native(log,frames,launch,state/'cow-operations')
        return dict(schema=1,kind='bw.terminal-unverified-observation.v1',status='terminal_unverified',
            launch_sha256=sha256(_bytes(launch)).hexdigest(),model_contract_id=cow['model_contract_id'],
            execution_profile_id=cow['execution_profile_id'],root_result_sha256=root['result'][0],
            baseline_inventory=baseline['inventory'],tool_outcomes=tools,native=native,
            dispatched_operations_settled=True,workflow_finished=False,
            artifact_correctness='unassessed',world_artifacts_captured=False,training_eligible=False,
            model_calls=0,tool_calls=0)


def archive_unverified_workflow(state,output):
    from .records import RuntimeLog
    from .coding_cli import read_launch
    from .coding_observation import _budget_files
    from .lesson_capture import _real_path,_write,_sync,_implementation,_canonical,CaptureRefused
    state=_real_path(state);parent=_real_path(Path(output).absolute().parent);output=parent/Path(output).name
    if output.exists()or output.is_symlink():raise CaptureRefused('Terminal archive output must be new')
    source=Path(read_launch(state)['config']['source']).absolute()
    if any(output==p or output.is_relative_to(p)or p.is_relative_to(output)for p in(state,source)):
        raise CaptureRefused('Terminal archive overlaps workflow/source')
    with RuntimeLog(state/'ledger',read_only=True):
        observation=observe_unverified_workflow(state);files=_budget_files(state)
        output.mkdir(mode=0o700);target=output/'state';target.mkdir(mode=0o700)
        for name,raw in files.items():
            path=target/name;path.parent.mkdir(mode=0o700,parents=True,exist_ok=True);_write(path,raw)
            if name=='coding-launch.json':path.chmod(0o600)
        if _budget_files(state)!=files or observe_unverified_workflow(state)!=observation:
            raise CaptureRefused('Terminal evidence changed during archival')
        value=dict(schema=1,kind='bw.terminal-unverified-archive.v1',original_state=str(state),
            observation=observation,implementation_sha256=_pins(),
            files=[dict(path=name,bytes=len(raw),sha256=sha256(raw).hexdigest())for name,raw in files.items()],
            training_eligible=False,world_artifacts_captured=False)
        value['archive_id']=sha256(_canonical(value)).hexdigest();_write(output/'terminal.json',_canonical(value)+b'\n')
        for directory in sorted((p for p in target.rglob('*')if p.is_dir()),key=lambda p:len(p.parts),reverse=True):_sync(directory)
        _sync(target);_sync(output);_sync(parent)
    return read_unverified_archive(output)


def read_unverified_archive(directory):
    from .coding_observation import _budget_files
    from .lesson_capture import _real_path,_read,_json,_implementation,_canonical,CaptureRefused
    directory=_real_path(directory);value=_json(_read(directory/'terminal.json'))
    keys={'schema','kind','original_state','observation','implementation_sha256','files','training_eligible','world_artifacts_captured','archive_id'}
    if (set(value)!=keys or value['schema']!=1 or value['kind']!='bw.terminal-unverified-archive.v1'
            or value['training_eligible']is not False or value['world_artifacts_captured']is not False
            or value['implementation_sha256']!=_pins()
            or value['archive_id']!=sha256(_canonical({k:v for k,v in value.items()if k!='archive_id'})).hexdigest()):
        raise CaptureRefused('Terminal archive identity/implementation changed')
    files=_budget_files(directory/'state')
    expected=[dict(path=name,bytes=len(raw),sha256=sha256(raw).hexdigest())for name,raw in files.items()]
    if value['files']!=expected or value['observation']!=observe_unverified_workflow(directory/'state'):
        raise CaptureRefused('Terminal archive evidence changed')
    return value
