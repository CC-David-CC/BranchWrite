"""Read-only summaries of the existing canonical workflow ledger.

A recorded verification result describes the original completion boundary.
It never certifies the present workspace or replaces execution/reconciliation.
No inference client, executor or configuration loader is used by this module.
"""
from collections import Counter
from pathlib import Path
from .records import RuntimeLog,Artifact,decode,CorruptLog
from .kernel import FrameKernel

def _activity_summary(sequence, event):
    kind=event['kind']
    row={'sequence':sequence,'kind':kind}
    if kind=='root':
        row['frame']=event['frame']
        row['step']='FLOW'
    elif kind=='spawn':
        row['frame']=event['parent']
        row['steps']=[call[3] for call in event['calls']]
    elif kind in ('dispatched','returned','settled','finished'):
        row['frame']=event['frame']
        if 'operation_id' in event:row['operation_id']=event['operation_id']
        if kind=='returned':row['settled']=event['settled']
    elif kind=='resumed':
        row['frame']=event['parent']
        row['epoch']=event['epoch']
    return row

def inspect_run(state,*,recent_limit=12):
    if type(recent_limit) is not int or not 0<=recent_limit<=64:
        raise ValueError('activity tail must be between 0 and 64 events')
    with RuntimeLog(Path(state)/'ledger',read_only=True) as log:
        kernel=FrameKernel(log);frames=kernel.frames()
        roots=[f for f in frames if f['parent'] is None]
        if len(roots)!=1:raise ValueError('run has no unique program root')
        root=roots[0]
        if root['contract']!=('ProgramResult','record'):
            raise ValueError('status requires a coding program result contract')
        verified=None
        exploration=None
        if root['state']=='Closed':
            payload=decode(log.read_artifact(Artifact(*root['result'])))[2]
            verified=payload.get('verified')
            if type(verified) is not bool:
                raise CorruptLog('program result has no recorded verification boolean')
            joined=[v[1] for v in payload.get('bindings',{}).values() if v[0]=='ParallelResult']
            selected=[v[1] for v in payload.get('bindings',{}).values() if v[0]=='Selection']
            if joined:
                exploration=dict(candidates=[dict(name=c['name'],verified=c['verified'],world=c['world'])
                    for c in joined[-1]['candidates']],selected=None if not selected or selected[-1]['selected'] is None
                    else selected[-1]['selected']['name'])
        pending=[]
        for frame in frames:
            if frame['dispatch'] is not None and frame['state']!='Closed':
                pending.append(dict(frame=frame['id'],operation_id=frame['dispatch'][0],state=frame['state']))
        # Describe only canonical pending tool frames. This is not evidence that
        # an effect happened, failed, or can be repeated; no tool owner is opened.
        tool_recovery=[dict(frame=f['id'],operation_id=f['dispatch'][0],state=f['state'],
            effect_status='awaiting_settlement' if f['state']=='Settling' else 'outcome_unknown',
            automatic_replay=False) for f in frames
            if f['dispatch'] is not None and f['state']!='Closed'
            and f['contract']==('ToolOutcome','record')]
        by_id={frame['id']:frame for frame in frames}
        model_recovery=[]
        for frame in frames:
            parent=by_id.get(frame['parent'])
            if (frame['state']=='Closed' or frame['dispatch'] is None
                    or frame['contract']!=('COWNativeReceipt','record')
                    or parent is None or parent['contract']!=('ModelOutput','record')
                    or parent['state']=='Closed'):
                continue
            operation=frame['dispatch'][0]
            model_recovery.append(dict(frame=frame['id'],operation_id=operation,
                reconcile_argv=['branchwrite','reconcile',str(Path(state).absolute()),'--operation-id',operation],
                receipt_argv=['branchwrite','receipt',str(Path(state).absolute()),'--operation-id',operation],
                resume_argv=['branchwrite','resume',str(Path(state).absolute())]))
        all_events=log.events
        selected=all_events[-recent_limit:] if recent_limit else ()
        recent_activity=[_activity_summary(log.event_count-len(selected)+index,
            entry['event']) for index,entry in enumerate(selected)]
        return dict(schema=1,state=root['state'],recorded_verified=verified,
                    workspace_rechecked=False,events=log.event_count,
                    recent_activity=recent_activity,
                    program_sha256=root['definition'][0],
                    frame_states=dict(sorted(Counter(f['state'] for f in frames).items())),
                    frame_operations=dict(sorted(Counter(f['operation'] for f in frames).items())),
                    pending_operations=sorted(pending,key=lambda x:x['frame']),
                    pending_model_recovery=sorted(model_recovery,key=lambda x:x['frame']),
                    pending_tool_recovery=sorted(tool_recovery,key=lambda x:x['frame']),
                    **({} if exploration is None else dict(exploration=exploration)))

def command(state,*,as_json=False,tail=12):
    import json,sys
    from .records import WriterBusy
    try:result=inspect_run(state,recent_limit=tail)
    except WriterBusy:
        print('branchwrite: run is busy; retry status after the current writer exits',file=sys.stderr)
        return 2
    except (OSError,ValueError,RuntimeError) as exc:
        print('branchwrite: '+ascii(str(exc)),file=sys.stderr);return 2
    if as_json:print(json.dumps(result,sort_keys=True))
    else:
        print('Run: '+result['state'])
        label={None:'not completed',True:'passed',False:'failed'}[result['recorded_verified']]
        print('Verification recorded at completion: '+label+'; current workspace not rechecked.')
        print('Frames: '+', '.join(k+'='+str(v) for k,v in result['frame_states'].items()))
        if 'exploration' in result:
            for candidate in result['exploration']['candidates']:
                print('Candidate '+candidate['name']+': checks '+('passed' if candidate['verified'] else 'failed'))
            print('Selected: '+str(result['exploration']['selected']))
        print('Recent activity (last '+str(len(result['recent_activity']))+' of '+str(result['events'])+' events):')
        for row in result['recent_activity']:
            detail=row['kind']
            if 'step' in row:detail+=' step='+ascii(row['step'])
            if 'steps' in row:detail+=' steps='+','.join(ascii(step) for step in row['steps'])
            if 'frame' in row:detail+=' frame='+ascii(row['frame'])
            if 'operation_id' in row:detail+=' operation='+ascii(row['operation_id'])
            if 'settled' in row:detail+=' settled='+str(row['settled'])
            print('  '+str(row['sequence'])+': '+detail)
        print('Pending external operations: '+str(len(result['pending_operations'])))
        for row in result['pending_operations']:
            print('  '+row['operation_id']+' ('+row['state']+')')
        if result['pending_tool_recovery']:
            print('Tool effects: do not repeat pending operations; model-reply reconciliation does not recover tool effects.')
            for row in result['pending_tool_recovery']:
                print('  '+row['operation_id']+': '+row['effect_status'])
            print('Inspect the original tool-owner receipt; matching file contents alone do not prove the outcome.')
        if result['pending_model_recovery']:
            print('Model replies: reconcile retrieves only proven durable output; unknown work stays unresolved.')
            for row in result['pending_model_recovery']:
                print('  Inspect saved result: branchwrite receipt RUN_DIRECTORY --operation-id '+row['operation_id'])
                print('  Reconcile: branchwrite reconcile RUN_DIRECTORY --operation-id '+row['operation_id'])
            print('  Then: branchwrite resume RUN_DIRECTORY')
            print('Tool effects require separate reconciliation; these commands do not authorize repeating them.')
    return 0
