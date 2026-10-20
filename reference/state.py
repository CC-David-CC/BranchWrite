"""Immutable branch-state oracle. The RNG is local to this oracle, not a native RNG."""
from dataclasses import dataclass, replace
from hashlib import sha256
import math
from .codec import encode, decode

@dataclass(frozen=True)
class DecodeState:
    native_ref: str
    grammar_ref: str
    prefix: bytes
    profile_ref: str
    rng_key: bytes
    counters: tuple[tuple[str, int], ...] = ()
    dry_history: tuple[int, ...] = ()
    mirostat_mu: float = 8.0
    adaptive_ema: float = 0.55
    stop_state: str = 'active'

    def __post_init__(self):
        if any(type(x) is not str or not x for x in (self.native_ref,self.grammar_ref,self.profile_ref)) or type(self.prefix) is not bytes or type(self.rng_key) is not bytes:
            raise ValueError('invalid snapshot field type')
        if type(self.counters) is not tuple or any(type(x) is not tuple or len(x) != 2 or type(x[0]) is not str or not x[0] for x in self.counters):
            raise ValueError('invalid counter shape')
        if type(self.dry_history) is not tuple or any(type(x) is not int for x in self.dry_history):
            raise ValueError('invalid DRY history')
        if any(type(x) is not float for x in (self.mirostat_mu,self.adaptive_ema)):
            raise ValueError('invalid feedback type')
        if self.counters != tuple(sorted(self.counters)):
            raise ValueError('noncanonical counters')
        if not self.rng_key or self.stop_state not in ('active','stopped'):
            raise ValueError('invalid state')
        if len(dict(self.counters)) != len(self.counters) or any(type(n) is not int or n < 0 for _,n in self.counters):
            raise ValueError('invalid RNG counters')
        if any(not math.isfinite(x) for x in (self.mirostat_mu, self.adaptive_ema)):
            raise ValueError('nonfinite feedback')

    def payload(self):
        return ('bw.reference.decode.v1', self.native_ref, self.grammar_ref, self.prefix,
                self.profile_ref, self.rng_key, self.counters, self.dry_history,
                self.mirostat_mu, self.adaptive_ema, self.stop_state)

    def packed(self):
        return encode(self.payload())

    @classmethod
    def unpack(cls, data):
        p = decode(data)
        if type(p) is not tuple or len(p) != 11 or p[0] != 'bw.reference.decode.v1':
            raise ValueError('unsupported snapshot')
        return cls(*p[1:])

    def clone(self):
        return replace(self)

    def explore(self, child_label, *, profile=None):
        if not child_label:
            raise ValueError('stable child identity required')
        key = sha256(encode(('bw.reference.split.v1', self.rng_key, child_label))).digest()
        return replace(self, rng_key=key, counters=(), profile_ref=profile or self.profile_ref)


def draw(state: DecodeState, component: str):
    if state.stop_state != 'active' or not component:
        raise ValueError('invalid draw boundary')
    counters = dict(state.counters)
    n = counters.get(component, 0)
    digest = sha256(encode(('bw.reference.draw.v1', state.rng_key, component, n))).digest()
    # 53 bits map exactly to [0,1); fixed algorithm for this offline oracle only.
    uniform = (int.from_bytes(digest[:8], 'big') >> 11) / 2**53
    counters[component] = n + 1
    return uniform, replace(state, counters=tuple(sorted(counters.items())))
