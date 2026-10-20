"""Pure typed-return event reducer. Does not claim durable storage or native recovery."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Projection:
    slots: tuple
    resumed: frozenset
    history: tuple
    quarantined: tuple


def reduce(events):
    waits, slots, current, resumed = {}, {}, {}, set()
    history, quarantine = [], []
    for event in events:
        history.append(event)
        if event[0] == 'wait':
            _, parent, epoch, slot, child, result_type = event
            if type(epoch) is not int or epoch < current.get(parent, -1):
                raise ValueError('invalid wait epoch')
            key = (parent,epoch,slot)
            expected = (child,result_type)
            if key in waits and waits[key] != expected:
                raise ValueError('conflicting wait')
            waits[key] = expected
            current[parent] = epoch
        elif event[0] == 'return':
            _, parent, epoch, slot, child, result_type, digest, settled = event
            key = (parent,epoch,slot)
            if epoch < current.get(parent,-1):
                quarantine.append(event)
                continue
            if key not in waits or waits[key] != (child,result_type):
                raise ValueError('wrong child, type, epoch or slot')
            if settled is not True:
                raise ValueError('unsettled resource obligations')
            if key in slots and slots[key] != digest:
                raise ValueError('conflicting return')
            slots[key] = digest
        elif event[0] == 'resume':
            _,parent,epoch = event
            keys = [k for k in waits if k[:2] == (parent,epoch)]
            if current.get(parent) != epoch or not keys or any(k not in slots for k in keys):
                raise ValueError('wait not satisfied')
            resumed.add((parent,epoch))
        else:
            raise ValueError('unknown event')
    return Projection(tuple(sorted(slots.items())),frozenset(resumed),tuple(history),tuple(quarantine))
