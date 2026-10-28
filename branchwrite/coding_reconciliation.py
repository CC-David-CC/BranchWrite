"""Recover one original model output without advancing the workflow ledger.

Hold the existing ledger read lease throughout recovery. A live interpreter
writer is refused. This is transport-output reconciliation, not an interpreter
migration, fresh model admission or a tool-effect reconciliation mechanism.
"""
import hashlib
from pathlib import Path
from .coding_cli import read_launch,_client,_bytes
from .records import RuntimeLog,Artifact,decode,WriterBusy
from .kernel import FrameKernel
from .language import parse,render
from .model_dispatch import ModelAdapter,ModelReconciliationRequired
from .cow_client import OperationIndeterminate


def _reconcile_bootstrap(state, launch, operation_id):
    from .run_cli import _retained_bootstrap, _coding_bootstrap
    cow = launch['config']['cow']
    seed = hashlib.sha256(_bytes(launch['config']) + launch['program'].encode('utf8')).hexdigest()[:40]
    if (launch['fork'] is not None or cow.get('bootstrap') != 'coding'
            or operation_id != 'bw-root-' + seed):
        raise ValueError('operation is not this saved setup bootstrap')
    client = _client(state, launch)
    if _retained_bootstrap(client, cow, seed) is None:
        raise ValueError('no original bootstrap intent was retained')
    try:
        result = client.reconcile_generation(operation_id)
    except OperationIndeterminate as exc:
        raise ModelReconciliationRequired(operation_id) from exc
    # Reuse the same receipt/profile/root checks as ordinary setup recovery.
    head = _coding_bootstrap(client, cow, launch['config'], seed, None,
                             task_bound=True, output_paths=(), command_requirements=())
    if result.receipt.snapshot != head.tip or result.answer.get('tokens') != []:
        raise ValueError('bootstrap reconciliation is not an idle root result')
    return 0, dict(status='reconciled', scope='bootstrap', operation_id=operation_id,
                   snapshot=head.tip, workflow_advanced=False, output_tokens=0)

def reconcile_saved(state,operation_id,*,diagnostic=False):
    state=Path(state)
    launch=read_launch(state)
    if not (state/'ledger').is_dir():
        raise ValueError('no admitted workflow ledger; nothing to reconcile')
    try:
        with RuntimeLog(state/'ledger',read_only=True) as log:
            kernel=FrameKernel(log)
            if not kernel.frames():
                if diagnostic:raise ValueError('diagnostics require an admitted model request')
                return _reconcile_bootstrap(state,launch,operation_id)
            root=kernel.frame('program')
            if root['contract']!=('ProgramResult','record'):
                raise ValueError('not a coding workflow')
            if log.read_artifact(Artifact(*root['definition']))!=render(parse(launch['program'])).encode():
                raise ValueError('saved launch differs from admitted program')
            inputs=decode(log.read_artifact(Artifact(*root['inputs'])))
            expected=('Text',hashlib.sha256(_bytes(launch['config'])).hexdigest())
            if inputs.get('bindings',{}).get('host-config-sha256')!=expected:
                raise ValueError('saved launch differs from admitted host configuration')
            matches=[f for f in kernel.frames() if f['state']!='Closed'
                     and f['contract']==('COWNativeReceipt','record')
                     and f['dispatch'] is not None and f['dispatch'][0]==operation_id]
            if len(matches)!=1:
                raise ValueError('operation is not one pending model request owned by this workflow')
            frame=matches[0]
            if frame['operation'] not in ('EXPAND','CONTINUE') or frame['dispatch'][1]!=frame['inputs']:
                raise ValueError('pending native dispatch differs from its admitted intent')
            parent=kernel.frame(frame['parent'])
            if parent['contract']!=('ModelOutput','record') or parent['state']=='Closed':
                raise ValueError('pending request has no open model owner')
            request=decode(log.read_artifact(Artifact(*frame['inputs'])))
            cow=launch['config']['cow'];key=request['frame_key']
            if (request.get('kind')!='bw.model-native-request'
                    or key['operation_id']!=operation_id or key['child_id']!=frame['id']
                    or key['run_id']!=launch['config']['run_id']
                    or request['endpoint_url']!=cow['endpoint_url']):
                raise ValueError('native intent belongs to a different workflow or endpoint')
            client=_client(state,launch)
            adapter=ModelAdapter(client,run_id=launch['config']['run_id'],
                model_contract_id=cow['model_contract_id'],execution_profile_id=cow['execution_profile_id'],
                eos_tokens=tuple(cow['eos_tokens']))
            adapter.check_journal(request)
            if diagnostic:
                observation=client.operation_diagnostic(operation_id)
                if observation['branch']!=cow['branch']:
                    raise ValueError('diagnostic belongs to a different COW branch')
                return 0,dict(status='diagnostic',operation_id=operation_id,
                    workflow_advanced=False,durable_claim_verified=False,diagnostic=observation)
            try:result=client.reconcile_generation(operation_id)
            except OperationIndeterminate as exc:
                raise ModelReconciliationRequired(operation_id) from exc
            payload=dict(operation_id=result.operation_id,receipt=dict(result.receipt.raw),
                answer=dict(result.answer),source_binding=None if result.source_binding is None else result.source_binding.to_json())
            adapter.validate_response(request,payload)
            return 0,dict(status='reconciled',operation_id=operation_id,frame=frame['id'],
                snapshot=result.receipt.snapshot,workflow_advanced=False,
                output_tokens=len(result.answer['tokens']))
    except WriterBusy as exc:
        raise ValueError('run is busy; stop its writer before explicit reconciliation') from exc
