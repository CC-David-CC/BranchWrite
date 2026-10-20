"""One journaled COW planning-fork call on the existing workflow kernel.

This owns no model history and does not decide whether a task failed. The
interpreter's retry integration admits this call only after its host verdict.
Unknown effects never become a new fork operation or a guessed branch head.
"""
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
import re
from .records import Artifact,encode,decode
from .kernel import CallSpec,ResultContract,TransitionError
from .cow_client import BranchHead,FrameKey,COWSourceBinding,OperationIndeterminate,ReceiptError

class ForkContractError(TransitionError):pass
class ForkReconciliationRequired(RuntimeError):
    def __init__(self,operation_id):
        self.operation_id=operation_id
        super().__init__('original planning fork is unresolved;reconcile it without resend')

def _definition(adapter):
    return encode(('bw.planning-fork.v1',adapter.identity,sha256(Path(__file__).read_bytes()).hexdigest()))

def _plan(adapter,value):
    try:
        if (type(value) is not dict or set(value)!={'schema','adapter','source','snapshot','name'}
                or value['schema']!=1 or value['adapter']!=adapter.identity):
            raise ForkContractError('planning fork definition changed')
        source=BranchHead.parse(value['source'])
        if (type(value['snapshot']) is not str or re.fullmatch('[0-9a-f]{64}',value['snapshot']) is None
                or type(value['name']) is not str or re.fullmatch('[A-Za-z][A-Za-z0-9_-]{0,127}',value['name']) is None
                or value['name']==source.name):
            raise ForkContractError('explicit distinct planning branch and snapshot required')
    except (KeyError,TypeError,ValueError) as error:
        raise ForkContractError('invalid planning-fork source') from error
    return value

def fork_call(kernel,adapter,*,child_id,attempt_id,slot,source,snapshot,name):
    if not isinstance(source,BranchHead):raise ForkContractError('observed COW source head required')
    value=_plan(adapter,dict(schema=1,adapter=adapter.identity,source=asdict(source),snapshot=snapshot,name=name))
    return CallSpec(child_id,attempt_id,slot,'TRANSFORM',kernel.log.put_artifact(_definition(adapter)),
        kernel.log.put_artifact(encode(value)),ResultContract('COWForkReceipt','record'))

def fork_operation_id(frame):
    return 'bwfork-'+sha256(encode(('bw.planning-fork-operation.v1',frame['id'],frame['attempt'],
        frame['definition'],frame['inputs']))).hexdigest()[:48]

def _key(adapter,frame,plan,operation_id):
    return FrameKey(adapter.run_id,frame['id'],frame['parent'],frame['attempt'],frame['id'],
        frame['slot'],frame['parent_epoch'],operation_id,plan['name'])

def _validate_value(adapter,frame,plan,value):
    operation=fork_operation_id(frame)
    if (type(value) is not dict or set(value)!={'schema','operation_id','plan_sha256','branch','source_binding','frame_key'}
            or type(value['schema']) is not int or value['schema']!=1 or value['operation_id']!=operation
            or frame['dispatch']!=(operation,frame['inputs']) or value['plan_sha256']!=frame['inputs'][0]
            or value['frame_key']!=_key(adapter,frame,plan,operation).to_json()):
        raise ForkContractError('fork return has a different workflow owner')
    try:
        head=BranchHead.parse(value['branch']);binding=COWSourceBinding.from_json(value['source_binding'])
    except (ValueError,ReceiptError) as error:raise ForkContractError('invalid fork return') from error
    if (head.name!=plan['name'] or head.revision!=0 or head.tip!=plan['snapshot']
            or head.root!=plan['source']['root']
            or binding.operation_id!=operation or binding.branch!=plan['name']
            or binding.source_branch!=plan['source']['name'] or binding.snapshot!=plan['snapshot']
            or binding.endpoint_pin!=adapter.client.endpoint_pin):
        raise ForkContractError('fork return changed branch,snapshot,root or source')
    return value

def dispatch_fork(kernel,adapter,identifier):
    frame=kernel.frame(identifier)
    if frame['operation']!='TRANSFORM' or frame['contract']!=('COWForkReceipt','record'):
        raise ForkContractError('frame is not a planning fork')
    if kernel.log.read_artifact(Artifact(*frame['definition']))!=_definition(adapter):
        raise ForkContractError('planning fork implementation changed')
    plan=_plan(adapter,decode(kernel.log.read_artifact(Artifact(*frame['inputs']))))
    if frame['state']=='Closed':
        return _validate_value(adapter,frame,plan,decode(kernel.log.read_artifact(Artifact(*frame['result'])))[2])
    if frame['state'] not in ('Ready','Waiting'):raise ForkContractError('fork frame is not executable')
    operation=fork_operation_id(frame);key=_key(adapter,frame,plan,operation)
    if frame['dispatch'] is None:
        kernel.dispatch(identifier,operation,Artifact(*frame['inputs']))
        # CowClient journals exact bytes/endpoint/frame before the one send.
        # Failure after this boundary is not an untouched pre-admission reject.
        head=adapter.client.fork(plan['source']['name'],plan['snapshot'],plan['name'],operation,frame_key=key)
    else:
        if frame['dispatch']!=(operation,frame['inputs']):raise ForkContractError('fork dispatch identity changed')
        try:head=adapter.client.read_completed_fork(operation)
        except OperationIndeterminate as error:raise ForkReconciliationRequired(operation) from error
    record=adapter.client.journal.read(operation)
    if record is None or record.get('state')!='complete':raise ForkReconciliationRequired(operation)
    # The client validates receipt/intent;the kernel also binds this exact slot.
    value=dict(schema=1,operation_id=operation,plan_sha256=frame['inputs'][0],branch=asdict(head),
        source_binding=record.get('source_binding'),frame_key=record.get('frame_key'))
    frame=kernel.frame(identifier)
    _validate_value(adapter,frame,plan,value)
    kernel.record_result(identifier,operation,value,settled=True)
    return value
