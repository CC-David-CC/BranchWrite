"""Read-only model-budget evidence from BW's actual frames and native receipts."""
from hashlib import sha256
import json
from pathlib import Path

def observe_model_budget(state):
    from .coding_cli import read_launch,_bytes
    from .records import RuntimeLog,Artifact,decode
    from .kernel import FrameKernel
    from .cow_client import CowClient,OperationJournal,OperationIntent
    from .model_dispatch import ModelAdapter,_flow,_prior
    class NoNetwork:
        name='read-only-model-budget-observation'
        def request(self,*args,**kwargs):raise RuntimeError('Budget observation cannot dispatch requests')
    state=Path(state);launch=read_launch(state);cow=launch['config']['cow']
    client=CowClient(NoNetwork(),journal=OperationJournal(state/'cow-operations'),
        endpoint_url=cow['endpoint_url'],endpoint_pin=cow['endpoint_pin'])
    mapping={}
    for path in client.journal.directory.iterdir():
        record=json.loads(path.read_bytes());record=client.journal.read(record['operation_id'])
        if record['state']!='complete':raise ValueError('Unsettled native request; not a proven budget failure')
        if record['path']=='/cow/grammars':
            intent=OperationIntent(record['operation_id'],'POST',record['path'],client.journal.decode_body(record),
                None,None,None,cow['endpoint_pin'])
            receipt=client._validate_nonstream(intent,record['receipt'])
            if mapping:raise ValueError('Ambiguous original grammar registration')
            mapping=receipt['states']
    adapter=ModelAdapter(client,run_id=launch['config']['run_id'],model_contract_id=cow['model_contract_id'],
        execution_profile_id=cow['execution_profile_id'],eos_tokens=tuple(cow['eos_tokens']),grammar_mapping=mapping)
    with RuntimeLog(state/'ledger',read_only=True)as log:
        kernel=FrameKernel(log);root=kernel.frame('program');frames=kernel.frames()
        if root['state']=='Closed':raise ValueError('Workflow has already completed')
        inputs=decode(log.read_artifact(Artifact(*root['inputs'])))
        if inputs['bindings'].get('host-config-sha256')!=('Text',sha256(_bytes(launch['config'])).hexdigest()):
            raise ValueError('Original host configuration changed')
        if any(f['dispatch']is not None and f['state']!='Closed'for f in frames):
            raise ValueError('Unsettled dispatch; not a proven budget failure')
        rows=[]
        for frame in frames:
            if frame['contract']!=('ModelOutput','record')or frame['state']=='Closed':continue
            if frame['state']!='Ready':raise ValueError('Model flow is not at a settled budget boundary')
            frame,plan=_flow(kernel,adapter,frame['id'])
            values,source,used=_prior(kernel,adapter,frame,plan,frame['epoch'])
            limit=plan['config']
            if (not values or values[-1][1].answer['tokens'][-1]in adapter.eos_tokens
                    or not(len(values)>=limit['max_requests']or used>=limit['max_output_tokens'])):
                raise ValueError('Open model output has not exhausted its frozen budget')
            rows.append(dict(frame=frame['id'],model_plan_sha256=frame['inputs'][0],
                native_requests=len(values),maximum_requests=limit['max_requests'],
                output_tokens=used,maximum_output_tokens=limit['max_output_tokens'],
                final_snapshot=source['tip'],output_complete=False))
        if not rows:raise ValueError('No exhausted logical model flow exists')
        return dict(schema=1,kind='bw.model-budget-observation.v1',status='model_budget_exhausted',
            launch_sha256=sha256(_bytes(launch)).hexdigest(),model_contract_id=cow['model_contract_id'],
            execution_profile_id=cow['execution_profile_id'],flows=rows,
            dispatched_operations_settled=True,workflow_finished=False,
            model_calls=0,tool_calls=0,training_eligible=False)


def _budget_files(state):
    """Bounded ledger/request bytes only; no mutable world or numerical cache."""
    from .lesson_capture import _read,_real_path,MAX_CAPTURE_BYTES,MAX_ENTRIES,CaptureRefused
    state=_real_path(state);ledger=_real_path(state/'ledger')
    artifacts=_real_path(ledger/'artifacts');journal=_real_path(state/'cow-operations')
    paths=[state/'coding-launch.json',ledger/'events.bwl',ledger/'writer.lock',
        *sorted(artifacts.iterdir()),*sorted(journal.iterdir())]
    if len(paths)>MAX_ENTRIES:raise CaptureRefused('Budget archive entry limit exceeded')
    files={};total=0
    for path in paths:
        raw=_read(path);total+=len(raw)
        if total>MAX_CAPTURE_BYTES:raise CaptureRefused('Budget archive byte limit exceeded')
        files[path.relative_to(state).as_posix()]=raw
    return files


def archive_model_budget(state,output):
    """Freeze a proven failed boundary for assessment, never as a lesson.

    The existing BW read lease excludes workflow writers throughout the copy.
    No world, native cache, model call, tool call or workflow mutation is needed.
    """
    from .records import RuntimeLog
    from .coding_cli import read_launch
    from .lesson_capture import _real_path,_write,_sync,_implementation,_canonical,CaptureRefused
    state=_real_path(state);parent=_real_path(Path(output).absolute().parent)
    output=parent/Path(output).name
    if output.exists()or output.is_symlink():raise CaptureRefused('Budget archive output must be new')
    source=Path(read_launch(state)['config']['source']).absolute()
    if any(output==p or output.is_relative_to(p)or p.is_relative_to(output)for p in(state,source)):
        raise CaptureRefused('Budget archive overlaps workflow/source')
    with RuntimeLog(state/'ledger',read_only=True):
        observation=observe_model_budget(state);files=_budget_files(state)
        output.mkdir(mode=0o700);target=output/'state';target.mkdir(mode=0o700)
        for name,raw in files.items():
            path=target/name;path.parent.mkdir(mode=0o700,parents=True,exist_ok=True);_write(path,raw)
            # read_launch's original private-file contract requires mode0600.
            if name=='coding-launch.json':path.chmod(0o600)
        if _budget_files(state)!=files or observe_model_budget(state)!=observation:
            raise CaptureRefused('Budget evidence changed during archival')
        value=dict(schema=1,kind='bw.model-budget-archive.v1',original_state=str(state),
            observation=observation,implementation_sha256=_implementation(),
            files=[dict(path=name,bytes=len(raw),sha256=sha256(raw).hexdigest())for name,raw in files.items()],
            training_eligible=False,world_artifacts_captured=False)
        value['archive_id']=sha256(_canonical(value)).hexdigest()
        _write(output/'budget.json',_canonical(value)+b'\n')
        for directory in sorted((p for p in target.rglob('*')if p.is_dir()),key=lambda p:len(p.parts),reverse=True):_sync(directory)
        _sync(target);_sync(output);_sync(parent)
    return read_budget_archive(output)


def read_budget_archive(directory):
    """Reverify an immutable failure without the original world or server."""
    from .lesson_capture import _real_path,_read,_json,_implementation,_canonical,CaptureRefused
    directory=_real_path(directory);value=_json(_read(directory/'budget.json'))
    keys={'schema','kind','original_state','observation','implementation_sha256','files',
        'training_eligible','world_artifacts_captured','archive_id'}
    if (set(value)!=keys or value['schema']!=1 or value['kind']!='bw.model-budget-archive.v1'
            or value['training_eligible']is not False or value['world_artifacts_captured']is not False
            or value['implementation_sha256']!=_implementation()
            or value['archive_id']!=sha256(_canonical({k:v for k,v in value.items()if k!='archive_id'})).hexdigest()):
        raise CaptureRefused('Budget archive identity/implementation changed')
    files=_budget_files(directory/'state')
    expected=[dict(path=name,bytes=len(raw),sha256=sha256(raw).hexdigest())for name,raw in files.items()]
    if value['files']!=expected or value['observation']!=observe_model_budget(directory/'state'):
        raise CaptureRefused('Budget archive evidence changed')
    return value
