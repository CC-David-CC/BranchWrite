"""Parallel child scopes on the existing kernel, with explicit isolated worlds.

This module never runs a second agent loop. The owning Interpreter steps each
context, collects observations and joins only settled child results.
"""
from dataclasses import asdict
from hashlib import sha256
from .records import Artifact, encode, decode
from .kernel import CallSpec, ResultContract
from .language import Statement, render
from .cow_client import BranchHead
from .cow_fork import fork_call, dispatch_fork


def budget(value):
    if (type(value) is not dict or set(value) != {'max_parallel','max_requests','max_output_tokens'}
            or any(type(v) is not int or v <= 0 for v in value.values())
            or value['max_parallel'] > 8 or value['max_requests'] > 65536
            or value['max_output_tokens'] > 16777216):
        raise ValueError('Finite host parallel/request/token budget required')
    return dict(value)


def cost(body, profiles):
    requests = tokens = 0
    for node in body:
        fields = dict(node.attributes)
        if node.opcode == 'EXPAND':
            profile = profiles[fields['profile']]
            requests += profile.get('max_requests', 8)
            tokens += profile.get('max_output_tokens', 12288)
        elif node.opcode == 'REPEAT':
            r, t = cost(node.body, profiles)
            requests += int(fields['max']) * r
            tokens += int(fields['max']) * t
    return requests, tokens


def preflight(runtime, node, env):
    from .interpreter import AdmissionError
    fields = dict(node.attributes)
    if fields['budget'] not in runtime.parallel_budgets:
        raise AdmissionError('Registered host parallel budget required')
    limits = budget(runtime.parallel_budgets[fields['budget']])
    if not 2 <= len(node.body) <= 8:
        raise AdmissionError('Parallel exploration requires 2..8 independent branches')
    if runtime.dispatcher is None or runtime.dispatcher.slots > limits['max_parallel']:
        raise AdmissionError('Parallel dispatch slots exceed the admitted host budget')
    names = set(); worlds = set(); requests = tokens = 0
    for arm in node.body:
        a = dict(arm.attributes)
        if (arm.opcode != 'BRANCH' or set(a) != {'base','world'}
                or a['base'] != fields['base'] or arm.label in names
                or arm.output is not None or a['world'] in worlds):
            raise AdmissionError('Distinct named branches and isolated worlds sharing the pinned base required')
        if a['world'] not in runtime.worlds:
            raise AdmissionError('Branch world must be registered by the host')
        context = runtime.worlds[a['world']]
        if context.registry._grant.remote_targets:
            raise AdmissionError('Parallel candidates cannot mutate shared remote targets')
        if context.registry.world == runtime.registry.world:
            raise AdmissionError('Candidate world must be isolated from the parent')
        names.add(arm.label);worlds.add(a['world'])
        context.preflight(render((Statement('FLOW',arm.label,body=arm.body),)),env)
        r, t = cost(arm.body,context.profiles);requests += r;tokens += t
    if len({runtime.worlds[name].registry.world for name in worlds}) != len(worlds):
        raise AdmissionError('Candidate world aliases overlap')
    if requests > limits['max_requests'] or tokens > limits['max_output_tokens']:
        raise AdmissionError('Frozen candidate bounds exceed the shared exploration budget')


def call(runtime, frame, node, env, identifier):
    from .interpreter import AdmissionError
    a = dict(node.attributes)
    base = env[a['base']]
    inventory = runtime.registry._inventory()
    for arm in node.body:
        context = runtime.worlds[dict(arm.attributes)['world']]
        if context.registry._inventory() != inventory:
            raise AdmissionError('Candidate input differs from the frozen parent project')
    value = dict(schema=1,identity=runtime.identity,bindings={k:v.wire for k,v in env.items()},
        source=base.data,inventory=inventory,budget=runtime.parallel_budgets[a['budget']])
    return CallSpec(identifier,'attempt-'+identifier[5:],'result','FLOW',
        runtime.kernel.log.put_artifact(render((node,)).encode()),
        runtime.kernel.log.put_artifact(encode(value)),ResultContract('ParallelResult','record'))


def _load(runtime, frame):
    from .interpreter import AdmissionError
    from .language import parse
    inputs=decode(runtime.kernel.log.read_artifact(Artifact(*frame['inputs'])))
    if inputs.get('identity') != runtime.identity:
        raise AdmissionError('Parallel source or world identity changed')
    node,=parse(runtime.kernel.log.read_artifact(Artifact(*frame['definition'])).decode())
    return node,inputs


def step_parallel(runtime, identifier):
    from .interpreter import Step, _returned
    kernel=runtime.kernel;frame=kernel.frame(identifier);node,inputs=_load(runtime,frame)
    if frame['state']=='Closed':return Step('complete',identifier,_returned(kernel,frame))
    if frame['state']=='Ready' and frame['pc']==0:
        calls=[]
        for arm in node.body:
            name='arm-'+sha256(encode((runtime.identity,identifier,arm.label))).hexdigest()[:48]
            plan=dict(inputs,world=dict(arm.attributes)['world'],label=arm.label)
            calls.append(CallSpec(name,'attempt-'+name[4:],arm.label,'FLOW',
                kernel.log.put_artifact(render((Statement('FLOW',arm.label,body=arm.body),)).encode()),
                kernel.log.put_artifact(encode(plan)),ResultContract('BranchResult','record')))
        kernel.spawn(identifier,expected_epoch=0,calls=tuple(calls),next_pc=1)
        return Step('parallel_admitted',identifier)
    children=[f for f in kernel.frames() if f['parent']==identifier]
    if frame['state']=='Waiting':
        reports=[step_branch(runtime,child['id']) for child in children if child['state']!='Closed']
        if all(kernel.frame(child['id'])['state']=='Closed' for child in children):
            kernel.resume(identifier,frame['epoch'])
            return Step('parallel_joined',identifier)
        for report in reports:
            if report.status in ('model_budget_exhausted','thinking_ladder_exhausted'):return report
        waiting=reports and all(r.status in ('model_waiting','tool_waiting','parallel_waiting') for r in reports)
        return Step('parallel_waiting' if waiting else 'parallel_progress',identifier)
    # Preserve declaration order, never completion order, for stable selection.
    values={child['slot']:(child,_returned(kernel,child)) for child in children}
    candidates=[];proof=[]
    for arm in node.body:
        child,value=values[arm.label]
        candidates.append(dict(name=arm.label,frame=child['id'],result=child['result'],
            world=value['world'],inventory=value['inventory'],verified=value['verified'],
            scope=value['scope'],bindings=value['bindings']))
        proof.append(Artifact(*child['result']))
    value=dict(schema=1,base=inputs['source'],base_inventory=inputs['inventory'],
        budget=inputs['budget'],candidates=tuple(candidates))
    kernel.finish(identifier,value,provenance=tuple(proof))
    return Step('complete',identifier,value)


def step_branch(runtime, identifier):
    from .interpreter import Step, _returned
    kernel=runtime.kernel;frame=kernel.frame(identifier);node,plan=_load(runtime,frame)
    context=runtime.worlds[plan['world']]
    if frame['state']=='Closed':return Step('complete',identifier,_returned(kernel,frame))
    source=BranchHead.parse(plan['source']['head'])
    fork=fork_call(kernel,context.adapter,child_id=identifier+'-fork',attempt_id=identifier+'-fork-attempt',
        slot='fork',source=source,snapshot=source.tip,name='bw-arm-'+identifier[4:])
    if frame['state']=='Ready' and frame['pc']==0:
        kernel.spawn(identifier,expected_epoch=0,calls=(fork,),next_pc=1)
        return Step('branch_admitted',identifier)
    if frame['state']=='Waiting':
        if frame['pc']==0:dispatch_fork(kernel,context.adapter,fork.child_id)
        else:
            report=context._scope(identifier+'-scope')
            # A nested FLOW/REPEAT may report its own completion while the
            # branch's direct scope still has work. Only its canonical return
            # fills this branch's wait slot.
            if kernel.frame(identifier+'-scope')['state']!='Closed':return report
        kernel.resume(identifier,frame['epoch'])
        return Step('branch_resumed',identifier)
    if frame['pc']==1:
        head=kernel.slot_value(identifier,1,'fork')['branch']
        bindings=dict(plan['bindings'],world=('World',context.registry.world),
            current=('COWSource',dict(head=head,mode=plan['source']['mode'])))
        inputs=dict(schema=1,identity=context.identity,bindings=bindings)
        call=CallSpec(identifier+'-scope',identifier+'-scope-attempt','scope','FLOW',
            kernel.log.put_artifact(render((node,)).encode()),kernel.log.put_artifact(encode(inputs)),
            ResultContract('ProgramResult','record'))
        kernel.spawn(identifier,expected_epoch=1,calls=(call,),next_pc=2)
        return Step('branch_scope_admitted',identifier)
    child=kernel.frame(identifier+'-scope');result=_returned(kernel,child)
    value=dict(schema=1,world=plan['world'],scope=child['id'],bindings=result['bindings'],
        verified=result['verified'] and checked_scope(context,child,result['bindings']),
        inventory=context.registry._inventory())
    kernel.finish(identifier,value,provenance=(Artifact(*child['result']),))
    return Step('complete',identifier,value)


def checked_scope(context,scope,bindings):
    """Revalidate actual finish/check receipts against current candidate bytes."""
    finishes=[v[1] for v in bindings.values() if v[0]=='ToolOutcome' and v[1].get('requested_finish') is True]
    if not finishes:return False
    return any(context._verification(finishes[-1],policy=v[1]['policy'],frame=scope)['status']=='pass'
        for v in bindings.values() if v[0]=='Verification' and v[1].get('status')=='pass')


def selection_current(runtime,value):
    from .interpreter import AdmissionError
    selected=value['selected']
    if selected is None:return False
    context=runtime.worlds[selected['world']]
    if (runtime.registry._inventory()!=value['base_inventory']
            or context.registry._inventory()!=selected['inventory']):
        raise AdmissionError('Selected project changed after verification')
    return checked_scope(context,runtime.kernel.frame(selected['scope']),selected['bindings'])


def select(runtime, value, rule, frame):
    from .interpreter import AdmissionError, Value, _returned
    # Only the joined, original ParallelResult in this lexical history can
    # authorize selection; a model cannot submit a fabricated verdict mapping.
    matches=[(f,v) for f,v in runtime._visible_results(frame,('ParallelResult','record')) if v==value]
    if len(matches)!=1:raise AdmissionError('Selection requires one original joined candidate result')
    chosen=None
    for candidate in value['candidates']:
        child=runtime.kernel.frame(candidate['frame'])
        original=_returned(runtime.kernel,child)
        if (child['result']!=candidate['result'] or original['verified']!=candidate['verified']
                or original['inventory']!=candidate['inventory']):
            raise AdmissionError('Candidate evidence changed after joining')
        context=runtime.worlds[candidate['world']]
        if context.registry._inventory()!=candidate['inventory']:
            raise AdmissionError('Candidate changed after verification')
        verified=candidate['verified'] and checked_scope(context,runtime.kernel.frame(candidate['scope']),candidate['bindings'])
        if verified and (rule=='verified-first' or rule==candidate['name']):
            if chosen is None:chosen=candidate
    if rule!='verified-first' and rule not in {c['name'] for c in value['candidates']}:
        raise AdmissionError('Unknown candidate selection rule')
    if runtime.registry._inventory()!=value['base_inventory']:
        raise AdmissionError('Parent project changed while candidates were running')
    return Value('Selection',dict(schema=1,rule=rule,selected=chosen,verified=chosen is not None,
        base_inventory=value['base_inventory'],parallel_frame=matches[0][0]['id'])), (Artifact(*matches[0][0]['result']),)
