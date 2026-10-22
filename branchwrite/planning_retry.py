"""Fork a retained planning point, then run one ordinary model FLOW.

The Interpreter decides whether a host-verified task failure merits this call.
This module neither invents a verdict nor owns another retry/history journal.
Unknown fork or generation effects retain their original operation identities.
"""
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
import re
from .records import Artifact,encode,decode
from .kernel import CallSpec,ResultContract,TransitionError
from .cow_client import BranchHead
from .cow_fork import fork_call,dispatch_fork,_definition as fork_definition
from .model_dispatch import FrozenModelCall,ModelStep,model_call,step_model
from .model_inputs import model_content

def retry_definition(adapter):
    return encode(('bw.planning-retry.v1',adapter.identity,
        sha256(Path(__file__).read_bytes()).hexdigest(),fork_definition(adapter)))

def retry_model_call(kernel,adapter,*,child_id,attempt_id,slot,source,snapshot,
                     mode,content,profile,provenance=()):
    """Freeze host-selected branch/input/profile before any native effect."""
    if not isinstance(source,BranchHead):raise TransitionError('observed failed branch required')
    BranchHead.parse(asdict(source))
    if type(snapshot) is not str or re.fullmatch('[0-9a-f]{64}',snapshot) is None:
        raise TransitionError('exact prior planning snapshot required')
    if type(profile) is not dict or type(provenance) is not tuple or any(not isinstance(v,Artifact) for v in provenance):
        raise TransitionError('frozen host profile and artifact provenance required')
    if mode not in ('ask','append_user'):raise TransitionError('retry preserves explicit ask or append_user boundary')
    content=model_content(content)
    name='bw-plan-'+sha256(encode((adapter.identity,child_id,attempt_id,asdict(source),snapshot))).hexdigest()[:40]
    head=BranchHead(name,0,snapshot,source.root)
    plan=adapter.freeze(head,mode=mode,content=content,**profile)
    for ref in provenance:kernel.log.read_artifact(ref)
    value=dict(schema=1,adapter=adapter.identity,source=asdict(source),snapshot=snapshot,name=name,
        model_plan=plan.data,provenance=tuple((r.sha256,r.size_bytes) for r in provenance))
    return CallSpec(child_id,attempt_id,slot,'FLOW',kernel.log.put_artifact(retry_definition(adapter)),
        kernel.log.put_artifact(encode(value)),ResultContract('ModelOutput','record'))

def _input(kernel,adapter,frame):
    if (frame['operation']!='FLOW' or frame['contract']!=('ModelOutput','record')
            or kernel.log.read_artifact(Artifact(*frame['definition']))!=retry_definition(adapter)):
        raise TransitionError('not this registered planning retry FLOW')
    value=decode(kernel.log.read_artifact(Artifact(*frame['inputs'])))
    if (type(value) is not dict or set(value)!={'schema','adapter','source','snapshot','name','model_plan','provenance'}
            or type(value['schema']) is not int or value['schema']!=1 or value['adapter']!=adapter.identity):
        raise TransitionError('planning retry input identity changed')
    source=BranchHead.parse(value['source'])
    expected_name='bw-plan-'+sha256(encode((adapter.identity,frame['id'],frame['attempt'],asdict(source),value['snapshot']))).hexdigest()[:40]
    if value['name']!=expected_name:raise TransitionError('planning retry destination changed')
    plan=adapter.plan(FrozenModelCall(value['model_plan']))
    expected=asdict(BranchHead(value['name'],0,value['snapshot'],source.root))
    if plan['source']!=expected or plan['config']['mode'] not in ('ask','append_user'):
        raise TransitionError('model plan changed fork source or input boundary')
    if type(value['provenance']) is not tuple:raise TransitionError('immutable planning provenance required')
    for ref in value['provenance']:kernel.log.read_artifact(Artifact(*ref))
    return value,source

def _calls(kernel,adapter,frame,value,source):
    fork=fork_call(kernel,adapter,child_id=frame['id']+'-fork',attempt_id=frame['attempt']+'-fork',
        slot='fork',source=source,snapshot=value['snapshot'],name=value['name'])
    model=model_call(kernel,adapter,child_id=frame['id']+'-model',attempt_id=frame['attempt']+'-model',
        slot='model',plan=FrozenModelCall(value['model_plan']))
    return fork,model

def _child(kernel,frame,call,*,epoch=None):
    child=kernel.frame(call.child_id)
    expected=(frame['id'],frame['epoch'] if epoch is None else epoch,call.slot,call.operation,
        (call.definition.sha256,call.definition.size_bytes),(call.inputs.sha256,call.inputs.size_bytes),call.result_contract.wire,call.attempt_id)
    actual=tuple(child[k] for k in ('parent','parent_epoch','slot','operation','definition','inputs','contract','attempt'))
    if actual!=expected:raise TransitionError('planning retry child differs from frozen call')
    return child

def _output(kernel,adapter,frame,value,fork,model):
    # A wrapper may publish only its original two settled child calls, even
    # after reopening. Reading a completed wrapper cannot perform new work.
    for call,epoch in ((fork,1),(model,2)):
        if _child(kernel,frame,call,epoch=epoch)['state']!='Closed':
            raise TransitionError('planning retry children are not settled')
    fork_value=dispatch_fork(kernel,adapter,fork.child_id)
    result=step_model(kernel,adapter,model.child_id)
    if result.status!='complete':raise TransitionError('incomplete model output cannot finish planning retry')
    if (result.value.get('model_frame')!=model.child_id
            or result.value.get('source_snapshot')!=value['snapshot']
            or result.value.get('plan_sha256')!=model.inputs.sha256):
        raise TransitionError('planning retry result changed model owner or source')
    return dict(result.value,planning_fork=fork_value)

def step_retry_model(kernel,adapter,identifier,*,dispatcher=None):
    """One existing-kernel step; no outer agent loop or uncertain resend."""
    frame=kernel.frame(identifier);value,source=_input(kernel,adapter,frame)
    fork,model=_calls(kernel,adapter,frame,value,source)
    if frame['state']=='Closed':
        expected=_output(kernel,adapter,frame,value,fork,model)
        actual=decode(kernel.log.read_artifact(Artifact(*frame['result'])))[2]
        if actual!=expected:raise TransitionError('planning retry return differs from committed children')
        return ModelStep('complete',identifier,value=actual)
    if frame['state'] not in ('Ready','Waiting') or frame['pc'] not in (0,1,2):
        raise TransitionError('planning retry has unresolved or invalid state')
    if frame['state']=='Waiting':
        call=fork if frame['pc']==0 else model
        child=_child(kernel,frame,call)
        if child['state']!='Closed':
            if call==fork:dispatch_fork(kernel,adapter,call.child_id)
            else:
                report=step_model(kernel,adapter,call.child_id,dispatcher=dispatcher)
                if report.status!='complete':
                    return ModelStep(report.status,identifier,report.native_operation)
        kernel.resume(identifier,frame['epoch'])
        return ModelStep('forked' if call==fork else 'model_returned',identifier)
    if frame['pc']<2:
        call=fork if frame['pc']==0 else model
        kernel.spawn(identifier,expected_epoch=frame['epoch'],calls=(call,),next_pc=frame['pc']+1)
        return ModelStep('admitted',identifier)
    result=_output(kernel,adapter,frame,value,fork,model)
    provenance=tuple(Artifact(*ref) for ref in value['provenance'])+tuple(Artifact(*kernel.frame(call.child_id)['result']) for call in (fork,model))
    kernel.finish(identifier,result,provenance=provenance)
    return ModelStep('complete',identifier,value=result)
