"""Pure dependency/conflict predicates, not a scheduler, grant issuer, or sandbox."""
from dataclasses import dataclass
from hashlib import sha256
from .codec import encode

@dataclass(frozen=True)
class Plan:
    operation: str
    scope: str
    profile: str
    dependencies: tuple[tuple[str, str], ...]
    claims: tuple[tuple[str, str], ...]
    slots: int

    @property
    def digest(self):
        return sha256(encode(('bw.reference.plan.v1', self.operation, self.scope, self.profile,
                              self.dependencies, self.claims, self.slots))).hexdigest()

    def fresh(self, versions):
        return all(k in versions and versions[k] == v for k,v in self.dependencies)


def freeze(operation, scope, profile, versions, reads, claims=(), slots=1):
    if not reads or len(set(reads)) != len(reads) or any(k not in versions for k in reads):
        raise ValueError('exact known dependency keys required')
    if type(slots) is not int or slots < 0:
        raise ValueError('invalid slot requirement')
    if len({key for key,_ in claims}) != len(claims) or any(mode not in ('read','write') for _,mode in claims):
        raise ValueError('invalid resource claims')
    return Plan(operation, scope, profile, tuple(sorted((k,versions[k]) for k in reads)),
                tuple(sorted(claims)), slots)


def compatible(a, b):
    for ra,ma in a.claims:
        for rb,mb in b.claims:
            if ra == rb and (ma == 'write' or mb == 'write'):
                return False
    return True


def eligible_together(plans, versions, granted_digests, qualified_scopes, capacity, reserved=0):
    ps = tuple(plans)
    if type(capacity) is not int or type(reserved) is not int or min(capacity,reserved) < 0:
        raise ValueError('invalid capacity')
    if not ps or len({p.digest for p in ps}) != len(ps):
        return False
    if any(not p.fresh(versions) or p.digest not in granted_digests or p.scope not in qualified_scopes for p in ps):
        return False
    if reserved + sum(p.slots for p in ps) > capacity:
        return False
    return all(compatible(a,b) for i,a in enumerate(ps) for b in ps[i+1:])
