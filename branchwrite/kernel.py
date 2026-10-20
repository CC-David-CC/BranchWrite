"""One production frame/return controller on the canonical RuntimeLog.

This owns durable state transitions, not model tokens, world grants or an
alternative agent loop. Dispatch adapters and the general CLI are next.
"""
from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal
import hashlib
import re
from .records import Artifact, CorruptLog, decode, encode


class TransitionError(ValueError): pass


def _name(value):
    if type(value) is not str or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_.:-]{0,127}',value):
        raise TransitionError('invalid host-owned identity')
    return value


def _integer(value):
    if type(value) is not int or value<0: raise TransitionError('nonnegative exact integer required')
    return value


def _ref(value):
    if type(value) is not tuple or len(value)!=2: raise TransitionError('invalid artifact binding')
    return Artifact(*value)


def _wire(ref):
    if not isinstance(ref,Artifact): raise TransitionError('typed artifact required')
    return (ref.sha256,ref.size_bytes)


@dataclass(frozen=True)
class ResultContract:
    name: str
    shape: str
    def __post_init__(self):
        _name(self.name)
        if self.shape not in ('bool','int','float','decimal','text','bytes','record','list','tuple','none'):
            raise TransitionError('unsupported result shape')
    @property
    def wire(self): return (self.name,self.shape)
    @property
    def digest(self):return hashlib.sha256(encode(('bw.result-contract.v1',*self.wire))).hexdigest()
    def check(self,value):
        typ={'bool':bool,'int':int,'float':float,'decimal':Decimal,'text':str,'bytes':bytes,
             'record':dict,'list':list,'tuple':tuple,'none':type(None)}[self.shape]
        if type(value) is not typ: raise TransitionError('result does not match the frozen contract')
        encode(value)


@dataclass(frozen=True)
class CallSpec:
    child_id: str
    attempt_id: str
    slot: str
    operation: str
    definition: Artifact
    inputs: Artifact
    result_contract: ResultContract
    def __post_init__(self):
        for value in (self.child_id,self.attempt_id,self.slot,self.operation):_name(value)
        _wire(self.definition);_wire(self.inputs)
        if not isinstance(self.result_contract,ResultContract):raise TransitionError('result contract required')
    @property
    def wire(self):
        return (self.child_id,self.attempt_id,self.slot,self.operation,
                _wire(self.definition),_wire(self.inputs),self.result_contract.wire)


_FIELDS={
 'root':{'frame','attempt','definition','inputs','contract'},
 'spawn':{'parent','source_epoch','calls','next_pc'},
 'dispatched':{'frame','operation_id','request'},
 'returned':{'frame','operation_id','result','provenance','settled'},
 'settled':{'frame','operation_id','receipt'},
 'resumed':{'parent','epoch'},
 'finished':{'frame','result','provenance'},
}


class FrameKernel:
    def __init__(self,log):
        self.log=log;self._seen=0;self._state=dict(frames={},groups={},operations={})
        try:
            for row in log.events:
                expected=self._references(row['event'])
                if set(row['artifacts'])!={_wire(a) for a in expected}:
                    raise TransitionError('event artifact roots do not match its bindings')
                self._apply(self._state,row['event']);self._seen+=1
        except (ValueError,TypeError,KeyError,IndexError) as exc:
            raise CorruptLog('invalid production frame transition') from exc

    def _check(self):
        if self.log.event_count!=self._seen:raise TransitionError('stale controller projection; reopen/replay')

    def _references(self,event):
        if (type(event) is not dict or type(event.get('schema')) is not int or event['schema']!=1
                or event.get('kind') not in _FIELDS
                or set(event)!=_FIELDS[event['kind']]|{'schema','kind'}):
            raise TransitionError('invalid frame event schema')
        kind=event['kind'];refs=[]
        if kind=='root':refs=[event['definition'],event['inputs']]
        elif kind=='spawn':
            if type(event['calls']) is not tuple or not 1<=len(event['calls'])<=256:
                raise TransitionError('bounded nonempty call tuple required')
            for call in event['calls']:
                if type(call) is not tuple or len(call)!=7:raise TransitionError('invalid call binding')
                refs.extend(call[4:6])
        elif kind=='dispatched':refs=[event['request']]
        elif kind in ('returned','finished'):
            if type(event['provenance']) is not tuple:raise TransitionError('provenance tuple required')
            refs=[event['result'],*event['provenance']]
        elif kind=='settled':refs=[event['receipt']]
        result=tuple(_ref(r) for r in refs)
        for ref in result:self.log.read_artifact(ref)
        return tuple(dict.fromkeys(result))

    @staticmethod
    def _frame(identifier,attempt,parent,parent_epoch,slot,operation,definition,inputs,contract):
        _name(identifier);_name(attempt);_name(operation)
        contract=ResultContract(*contract)
        return dict(id=identifier,attempt=attempt,parent=parent,parent_epoch=parent_epoch,slot=slot,
            operation=operation,definition=definition,inputs=inputs,contract=contract.wire,
            contract_id=contract.digest,state='Ready',pc=0,epoch=0,dispatch=None,result=None,
            result_settled=False,settlement_receipt=None)

    def _apply(self,state,event):
        kind=event['kind'];frames=state['frames'];groups=state['groups'];operations=state['operations']
        if kind=='root':
            candidate=self._frame(event['frame'],event['attempt'],None,None,None,'FLOW',
                                  event['definition'],event['inputs'],event['contract'])
            if candidate['id'] in frames:
                prior=frames[candidate['id']]
                if any(prior[k]!=candidate[k] for k in ('attempt','parent','operation','definition','inputs','contract')):
                    raise TransitionError('root identity reused for different work')
                return False
            if frames:raise TransitionError('one root per run; use child scopes')
            frames[candidate['id']]=candidate
        elif kind=='spawn':
            parent=frames[event['parent']];old=_integer(event['source_epoch']);epoch=old+1
            key=(event['parent'],epoch)
            if key in groups:
                if groups[key]['admission']!=event:raise TransitionError('changed wait admission')
                return False
            if parent['state']!='Ready' or parent['epoch']!=old:raise TransitionError('parent is not ready at this epoch')
            _integer(event['next_pc']);children=[];slots=set();ids=set()
            for call in event['calls']:
                child,attempt,slot,op,definition,inputs,contract=call;_name(slot)
                if slot in slots or child in ids or child in frames:raise TransitionError('duplicate slot/child')
                slots.add(slot);ids.add(child)
                children.append(self._frame(child,attempt,parent['id'],epoch,slot,op,definition,inputs,contract))
            for child in children:frames[child['id']]=child
            groups[key]=dict(admission=deepcopy(event),expected={c['slot']:c['id'] for c in children},filled={},resumed=False)
            parent.update(state='Waiting',epoch=epoch)
        elif kind=='dispatched':
            frame=frames[event['frame']];op=_name(event['operation_id']);binding=(op,event['request'])
            if frame['dispatch'] is not None:
                if frame['dispatch']!=binding:raise TransitionError('unresolved/dispatched operation cannot be replaced')
                return False
            if frame['state']!='Ready' or op in operations:raise TransitionError('dispatch identity/state conflict')
            operations[op]=frame['id'];frame.update(state='Waiting',dispatch=binding)
        elif kind=='returned':
            frame=frames[event['frame']]
            if frame['dispatch'] is None or event['operation_id']!=frame['dispatch'][0]:
                raise TransitionError('return has no matching dispatched operation')
            if type(event['settled']) is not bool:raise TransitionError('settlement is a host boolean')
            payload=decode(self.log.read_artifact(_ref(event['result'])))
            if (type(payload) is not tuple or len(payload)!=4 or payload[0]!='bw.result.v1'
                    or payload[1]!=frame['contract'] or payload[3]!=event['provenance']):
                raise TransitionError('result artifact has a different contract/provenance')
            ResultContract(*frame['contract']).check(payload[2])
            if frame['result'] is not None:
                if frame['result']!=event['result']:raise TransitionError('conflicting return')
                if frame['state']=='Settling' and event['settled']:
                    raise TransitionError('explicit resource settlement receipt required')
                return False
            if frame['state']!='Waiting':raise TransitionError('frame cannot return now')
            frame.update(result=event['result'],result_settled=event['settled'],
                         state='Closed' if event['settled'] else 'Settling')
            if event['settled']:self._deliver(state,frame)
        elif kind=='finished':
            frame=frames[event['frame']]
            if frame['operation']!='FLOW':raise TransitionError('only a FLOW may return without external dispatch')
            payload=decode(self.log.read_artifact(_ref(event['result'])))
            if (type(payload) is not tuple or len(payload)!=4 or payload[0]!='bw.result.v1'
                    or payload[1]!=frame['contract'] or payload[3]!=event['provenance']):
                raise TransitionError('FLOW result contract/provenance mismatch')
            ResultContract(*frame['contract']).check(payload[2])
            if frame['state']=='Closed':
                if frame['result']!=event['result']:raise TransitionError('conflicting FLOW return')
                return False
            if frame['state']!='Ready':raise TransitionError('FLOW has unresolved waits/effects')
            frame.update(state='Closed',result=event['result'],result_settled=True);self._deliver(state,frame)
        elif kind=='settled':
            frame=frames[event['frame']]
            if frame['dispatch'] is None or event['operation_id']!=frame['dispatch'][0]:
                raise TransitionError('settlement owner mismatch')
            if frame['settlement_receipt'] is not None:
                if frame['settlement_receipt']!=event['receipt']:raise TransitionError('changed settlement proof')
                return False
            if frame['state']!='Settling' or frame['result'] is None:raise TransitionError('no result awaiting settlement')
            frame.update(state='Closed',result_settled=True,settlement_receipt=event['receipt']);self._deliver(state,frame)
        elif kind=='resumed':
            parent=frames[event['parent']];epoch=_integer(event['epoch']);group=groups[(parent['id'],epoch)]
            if group['resumed']:return False
            if (parent['state']!='Waiting' or parent['epoch']!=epoch
                    or set(group['filled'])!=set(group['expected'])):raise TransitionError('wait is not completely settled')
            group['resumed']=True;parent.update(state='Ready',pc=group['admission']['next_pc'])
        return True

    @staticmethod
    def _deliver(state,frame):
        if frame['parent'] is None:return
        group=state['groups'][(frame['parent'],frame['parent_epoch'])]
        if group['expected'].get(frame['slot'])!=frame['id']:raise TransitionError('return slot owner mismatch')
        existing=group['filled'].get(frame['slot'])
        if existing is not None and existing!=frame['result']:raise TransitionError('conflicting slot delivery')
        group['filled'][frame['slot']]=frame['result']

    def _commit(self,kind,**fields):
        self._check();event=dict(schema=1,kind=kind,**fields)
        try:
            refs=self._references(event);candidate=deepcopy(self._state)
            changed=self._apply(candidate,event)
        except (KeyError,TypeError,IndexError) as exc:raise TransitionError('unknown/malformed frame binding') from exc
        if changed:
            self.log.append(event,artifacts=refs);self._state=candidate;self._seen+=1
        return changed

    def create_root(self,frame_id,attempt_id,definition,inputs,contract):
        self._commit('root',frame=frame_id,attempt=attempt_id,definition=_wire(definition),
                     inputs=_wire(inputs),contract=contract.wire)
        return self.frame(frame_id)

    def spawn(self,parent,*,expected_epoch,calls,next_pc):
        if type(calls) is not tuple or any(not isinstance(c,CallSpec) for c in calls):
            raise TransitionError('host call specifications required')
        self._commit('spawn',parent=parent,source_epoch=expected_epoch,calls=tuple(c.wire for c in calls),next_pc=next_pc)
        return expected_epoch+1

    def dispatch(self,frame,operation_id,request):
        return self._commit('dispatched',frame=frame,operation_id=operation_id,request=_wire(request))

    def record_result(self,frame,operation_id,value,*,provenance=(),settled=True):
        self._check();current=self.frame(frame);ResultContract(*current['contract']).check(value)
        refs=tuple(_wire(a) for a in provenance)
        result=self.log.put_artifact(encode(('bw.result.v1',current['contract'],value,refs)))
        self._commit('returned',frame=frame,operation_id=operation_id,result=_wire(result),provenance=refs,settled=settled)
        return result

    def finish(self,frame,value,*,provenance=()):
        self._check();current=self.frame(frame);ResultContract(*current['contract']).check(value)
        refs=tuple(_wire(a) for a in provenance)
        result=self.log.put_artifact(encode(('bw.result.v1',current['contract'],value,refs)))
        self._commit('finished',frame=frame,result=_wire(result),provenance=refs)
        return result

    def settle(self,frame,operation_id,receipt):
        return self._commit('settled',frame=frame,operation_id=operation_id,receipt=_wire(receipt))

    def resume(self,parent,epoch):return self._commit('resumed',parent=parent,epoch=epoch)

    def frame(self,identifier):
        self._check();return deepcopy(self._state['frames'][identifier])

    def frames(self):
        """Detached inventory for the owning interpreter, never worker authority."""
        self._check();return tuple(deepcopy(v) for v in self._state['frames'].values())

    def ready(self):
        self._check();return tuple(k for k,v in self._state['frames'].items() if v['state']=='Ready')

    def slot_value(self,parent,epoch,slot):
        self._check();ref=self._state['groups'][(parent,epoch)]['filled'][slot]
        return decode(self.log.read_artifact(_ref(ref)))[2]

    def visible_results(self,frame,contract):
        # A rejected proposal must not erase a read the model already saw. Derive
        # witnesses from resumed predecessor subtrees on this lexical ancestry;
        # never from an unsettled/unjoined sibling or another run. No read cache
        # or second history is persisted. Freshness is still checked at dispatch.
        frames={f['id']:f for f in self.frames()};children={}
        for value in frames.values():children.setdefault(value['parent'],[]).append(value)
        outcomes=[]
        def collect(value):
            pending=[value]
            while pending:
                current=pending.pop()
                if current['state']!='Closed':raise TransitionError('visible predecessor is not closed')
                if current['contract']==contract:
                    outcomes.append((current,decode(self.log.read_artifact(_ref(current['result'])))[2]))
                pending.extend(reversed(children.get(current['id'],())))
        cursor=frame
        while True:
            for prior in children.get(cursor['id'],()):
                if prior['parent_epoch']<=cursor['pc']:collect(prior)
            if cursor['parent'] is None:break
            cursor=frames[cursor['parent']]
        completed={entry['event']['frame']:index for index,entry in enumerate(self.log.events)
            if entry['event']['kind'] in ('returned','finished')}
        return tuple(sorted(outcomes,key=lambda item:completed[item[0]['id']]))

