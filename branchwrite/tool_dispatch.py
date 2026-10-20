"""One interpreter dispatch step; workers return observations, not transitions.

No polling/agent loop or second workflow state is here. The future CLI invokes
this on the Kernel owner thread; Executor/registry execute only the frozen tool.
"""
from hashlib import sha256
from .records import Artifact,decode,encode
from .kernel import CallSpec,ResultContract,TransitionError
from .execution import ToolRejected
from .tool_registry import FrozenToolPlan,ToolOutcome,EffectIndeterminate


class ReconciliationRequired(RuntimeError):
    def __init__(self,operation_id,plan_sha256):
        self.operation_id=operation_id;self.plan_sha256=plan_sha256
        super().__init__('original tool operation is unresolved; no automatic resend')


def tool_call(kernel,registry,*,child_id,attempt_id,slot,plan):
    """Admit the exact PLAN bytes, never silently freeze a newer filesystem."""
    if not isinstance(plan,FrozenToolPlan):raise TransitionError('frozen tool plan required')
    data=decode(plan.data)
    if type(data) is not tuple or len(data)!=8 or data[:3]!=('bw.tool-plan.v2',registry.identity,registry.world):
        raise TransitionError('tool plan belongs to another registry/world')
    tool=data[3]
    return CallSpec(child_id,attempt_id,slot,registry.operation_kind(tool),
        kernel.log.put_artifact(registry.definition_bytes(tool)),kernel.log.put_artifact(plan.data),
        ResultContract('ToolOutcome','record'))


def admit_tool(kernel,registry,parent,*,expected_epoch,child_id,attempt_id,slot,next_pc,proposal,observations=()):
    plan=registry.freeze(proposal,observations=observations)
    call=tool_call(kernel,registry,child_id=child_id,attempt_id=attempt_id,slot=slot,plan=plan)
    return kernel.spawn(parent,expected_epoch=expected_epoch,calls=(call,),next_pc=next_pc)


def _bound_value(frame,value):
    if (type(value) is not dict or value.get('schema')!=1
            or frame['dispatch'] is None or value.get('operation_id')!=frame['dispatch'][0]
            or value.get('plan_sha256')!=frame['inputs'][0]):
        raise TransitionError('tool return does not bind the original operation and plan')
    return value


def _retirement_bytes(kernel,registry,frame,value,provenance):
    # Registry.execute returns only after the existing Executor has retired
    # resources and validated its receipt. This records that host observation,
    # not an inference from matching current file contents.
    return encode(('bw.tool-retirement.v2',str(kernel.log.root),registry.identity,registry.world,
        frame['id'],frame['attempt'],frame['parent'],frame['parent_epoch'],frame['slot'],
        frame['definition'],frame['inputs'],
        frame['dispatch'],sha256(encode(value)).hexdigest(),provenance))


def _settle_return(kernel,registry,frame):
    """Close a proven returned effect; never execute or recheck old preimages."""
    payload=decode(kernel.log.read_artifact(Artifact(*frame['result'])))
    value=_bound_value(frame,payload[2]);refs=payload[3]
    if not refs:
        raise ReconciliationRequired(frame['dispatch'][0],frame['inputs'][0])
    proof=Artifact(*refs[-1])
    actual=kernel.log.read_artifact(proof)
    try:marker=decode(actual)
    except ValueError:
        raise ReconciliationRequired(frame['dispatch'][0],frame['inputs'][0]) from None
    if type(marker) is not tuple or not marker or marker[0]!='bw.tool-retirement.v2':
        raise ReconciliationRequired(frame['dispatch'][0],frame['inputs'][0])
    expected=_retirement_bytes(kernel,registry,frame,value,refs[:-1])
    if actual!=expected:
        raise TransitionError('tool return lacks its exact resource-retirement proof')
    for ref in refs[:-1]:kernel.log.read_artifact(Artifact(*ref))
    try:kernel.settle(frame['id'],frame['dispatch'][0],proof)
    except Exception as exc:
        raise EffectIndeterminate(frame['dispatch'][0],frame['inputs'][0]) from exc
    return value


def dispatch_tool(kernel,registry,identifier):
    frame=kernel.frame(identifier)
    if frame['contract']!=('ToolOutcome','record') or frame['operation'] not in ('ACT','OBSERVE','TRANSFORM'):
        raise TransitionError('frame is not a registered tool call')
    if frame['state']=='Closed':
        payload=decode(kernel.log.read_artifact(Artifact(*frame['result'])))
        return _bound_value(frame,payload[2])
    pending=frame['dispatch'] is not None and frame['state']!='Settling'
    if pending:
        try:original=decode(kernel.log.read_artifact(Artifact(*frame['inputs'])))
        except Exception:raise ReconciliationRequired(frame['dispatch'][0],frame['inputs'][0]) from None
        if type(original) is not tuple or len(original)!=8 or original[3] not in ('remote_command','check_remote','upload_file'):
            raise ReconciliationRequired(frame['dispatch'][0],frame['inputs'][0])
    if frame['state'] not in ('Ready','Settling') and not pending:raise TransitionError('tool frame is not ready')
    plan=FrozenToolPlan(kernel.log.read_artifact(Artifact(*frame['inputs'])))
    data=decode(plan.data)
    if type(data) is not tuple or len(data)!=8:raise TransitionError('invalid tool input binding')
    tool=data[3]
    definition=kernel.log.read_artifact(Artifact(*frame['definition']))
    if definition!=registry.definition_bytes(tool) or frame['operation']!=registry.operation_kind(tool):
        raise TransitionError('registered operation/definition changed')
    if frame['state']=='Settling':
        return _settle_return(kernel,registry,frame)
    if pending:
        operation_id=frame['dispatch'][0]
        try:outcome=registry.reconcile(plan,operation_id)
        except EffectIndeterminate as error:raise ReconciliationRequired(operation_id,plan.sha256) from error
    else:
        operation_id='bwtool-'+sha256(encode(('bw.tool-operation.v1',frame['id'],frame['attempt'],frame['definition'],frame['inputs']))).hexdigest()[:48]
        if not kernel.dispatch(identifier,operation_id,Artifact(*frame['inputs'])):
            raise ReconciliationRequired(operation_id,plan.sha256)
        try:outcome=registry.execute(plan,operation_id)
        except ToolRejected as exc:
            # Registry raises ToolRejected only before external execution starts.
            # Exceptions after that boundary use EffectIndeterminate and propagate;
            # the retained intent stays Waiting for explicit reconciliation.
            outcome=ToolOutcome('rejected_before_execution',None,0.0,b'',str(exc).encode('utf8'),
                                operation_id,plan.sha256,tool)
    try:
        value,provenance=outcome.publish(kernel.log)
        current=kernel.frame(identifier);_bound_value(current,value)
        wires=tuple((ref.sha256,ref.size_bytes) for ref in provenance)
        proof=kernel.log.put_artifact(_retirement_bytes(kernel,registry,current,value,wires))
        # Both the result and retirement proof become canonical before delivery.
        # A crash here leaves a resumable Settling frame, not another tool call.
        kernel.record_result(identifier,operation_id,value,
                             provenance=(*provenance,proof),settled=False)
        return _settle_return(kernel,registry,kernel.frame(identifier))
    except Exception as exc:
        # Output/ledger publication can fail after an effect. Do not report a
        # pre-execution rejection or authorize a resend. Reopen the exact run.
        raise EffectIndeterminate(operation_id,plan.sha256) from exc
