"""Synthetic-candidate arithmetic, NOT native implementations or quality claims."""
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class Candidate:
    token: int
    logit: float


def checked(candidates):
    cs = tuple(candidates)
    if not cs or len({x.token for x in cs}) != len(cs):
        raise ValueError('nonempty unique candidates required')
    if any(type(x.token) is not int or not math.isfinite(x.logit) for x in cs):
        raise ValueError('finite legal logits required')
    return cs


def mask(logits, legal):
    if any(math.isnan(v) or v == math.inf for v in logits.values()):
        raise ValueError('invalid model logits')
    return checked(Candidate(k, float(v)) for k,v in sorted(logits.items()) if k in legal and v != -math.inf)


def probabilities(candidates):
    cs = checked(candidates)
    maximum = max(c.logit for c in cs)
    weights = [math.exp(c.logit - maximum) for c in cs]
    total = math.fsum(weights)
    return tuple((c.token, w/total) for c,w in zip(cs, weights))


def probability(value, *, positive=False):
    if not math.isfinite(value) or value < 0 or value > 1 or (positive and value == 0):
        raise ValueError('invalid probability parameter')


def greedy(candidates):
    return min(checked(candidates), key=lambda c: (-c.logit, c.token)).token


def min_p(candidates, threshold):
    probability(threshold)
    cs = checked(candidates)
    if threshold == 0:
        return cs
    limit = max(c.logit for c in cs) + math.log(threshold)
    return checked(c for c in cs if c.logit >= limit)


def typical(candidates, mass):
    probability(mass, positive=True)
    cs = checked(candidates)
    if mass == 1:
        return cs
    probs = dict(probabilities(cs))
    entropy = -math.fsum(p*math.log(p) for p in probs.values() if p > 0)
    ranked = sorted((c for c in cs if probs[c.token] > 0),
                    key=lambda c: (abs(-math.log(probs[c.token])-entropy), c.token))
    keep, total = [], 0.0
    for c in ranked:
        keep.append(c)
        total += probs[c.token]
        if total >= mass:
            break
    return checked(keep)


def temperature(candidates, value):
    cs = checked(candidates)
    if not math.isfinite(value) or value <= 0:
        raise ValueError('positive finite temperature required; greedy is explicit')
    return checked(Candidate(c.token, c.logit/value) for c in cs)


def dynatemp(candidates, base, span, exponent):
    cs = checked(candidates)
    if any(not math.isfinite(x) for x in (base,span,exponent)) or span < 0 or base-span <= 0 or exponent <= 0:
        raise ValueError('invalid dynamic temperature bounds')
    low, high = base-span, base+span
    if len(cs) == 1:
        return cs, low
    probs = probabilities(cs)
    entropy = -math.fsum(p*math.log(p) for _,p in probs if p > 0)
    h = min(1.0, max(0.0, entropy/math.log(len(cs))))
    t = low + (high-low)*h**exponent
    return temperature(cs, t), t


def xtc(candidates, activation, threshold, draw, *, min_keep=1):
    probability(activation)
    probability(threshold, positive=True)
    if type(min_keep) is not int or min_keep < 1:
        raise ValueError('positive minimum required')
    cs = checked(candidates)
    if activation == 0 or len(cs) <= min_keep:
        return cs  # no RNG draw needed by this reference contract
    if draw is None or not math.isfinite(draw) or not 0 <= draw < 1:
        raise ValueError('explicit uniform draw required')
    if draw >= activation:
        return cs
    p = dict(probabilities(cs))
    ranked = sorted(cs, key=lambda c: (-p[c.token], c.token))
    high = [c for c in ranked if p[c.token] >= threshold]
    if len(high) < 2:
        return cs
    remove = {c.token for c in high[:-1]}
    remaining = tuple(c for c in cs if c.token not in remove)
    return checked(remaining) if len(remaining) >= min_keep else cs


def distribution_select(candidates, draw):
    if not math.isfinite(draw) or not 0 <= draw < 1:
        raise ValueError('explicit uniform draw required')
    probs = probabilities(sorted(checked(candidates), key=lambda c: c.token))
    acc = 0.0
    last_positive = None
    for token,p in probs:
        if p > 0: last_positive = token
        acc += p
        if draw < acc: return token
    return last_positive  # rounding at the final bin, never a zero-probability token
