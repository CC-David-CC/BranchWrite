"""Canonical typed framing oracle. No JSON, pickle, eval, or native-state serialization."""
from decimal import Decimal
import math
import re

MAX_BYTES = 4_000_000
MAX_DEPTH = 40


def encode(value, depth=0) -> bytes:
    if depth > MAX_DEPTH:
        raise ValueError('depth limit')
    typ = type(value)
    if value is None:
        tag, payload = b'n', b''
    elif typ is bool:
        tag, payload = b'b', b'1' if value else b'0'
    elif typ is int:
        tag, payload = b'i', str(value).encode('ascii')
    elif typ is float:
        if not math.isfinite(value):
            raise ValueError('non-finite float')
        tag, payload = b'f', value.hex().encode('ascii')
    elif typ is Decimal:
        if not value.is_finite():
            raise ValueError('non-finite decimal')
        tag, payload = b'd', str(value).encode('ascii')
    elif typ is str:
        tag, payload = b'u', value.encode('utf-8')
    elif typ is bytes:
        tag, payload = b'x', value
    elif typ in (tuple, list):
        tag = b't' if typ is tuple else b'l'
        payload = b''.join(encode(x, depth + 1) for x in value)
    elif typ is dict:
        if any(type(k) is not str for k in value):
            raise ValueError('record keys must be text')
        tag = b'm'
        payload = b''.join(encode(k, depth + 1) + encode(value[k], depth + 1) for k in sorted(value))
    else:
        raise ValueError('unsupported canonical type')
    result = tag + str(len(payload)).encode('ascii') + b':' + payload
    if len(result) > MAX_BYTES:
        raise ValueError('byte limit')
    return result


def decode(data: bytes):
    if type(data) is not bytes or len(data) > MAX_BYTES:
        raise ValueError('invalid bytes')
    def item(start, limit, depth):
        if depth > MAX_DEPTH or start >= limit:
            raise ValueError('truncated/deep record')
        tag = data[start:start+1]
        colon = data.find(b':', start+1, min(limit, start+20))
        if colon < 0:
            raise ValueError('missing length')
        length = data[start+1:colon]
        if not re.fullmatch(rb'0|[1-9][0-9]*', length):
            raise ValueError('noncanonical length')
        end = colon + 1 + int(length)
        if end > limit:
            raise ValueError('truncated payload')
        p = data[colon+1:end]
        if tag == b'n':
            if p: raise ValueError('bad null')
            value = None
        elif tag == b'b':
            if p not in (b'0', b'1'): raise ValueError('bad boolean')
            value = p == b'1'
        elif tag == b'i':
            if not re.fullmatch(rb'0|-?[1-9][0-9]*', p): raise ValueError('bad integer')
            value = int(p)
        elif tag == b'f':
            value = float.fromhex(p.decode('ascii'))
        elif tag == b'd':
            value = Decimal(p.decode('ascii'))
        elif tag == b'u':
            value = p.decode('utf-8', errors='strict')
        elif tag == b'x':
            value = p
        elif tag in (b't', b'l', b'm'):
            elements = []
            cursor = colon + 1
            while cursor < end:
                v, cursor = item(cursor, end, depth+1)
                elements.append(v)
            if tag == b't': value = tuple(elements)
            elif tag == b'l': value = elements
            else:
                if len(elements) % 2: raise ValueError('unpaired record')
                keys = elements[::2]
                if any(type(k) is not str for k in keys) or len(set(keys)) != len(keys) or keys != sorted(keys):
                    raise ValueError('invalid or duplicate keys')
                value = dict(zip(keys, elements[1::2]))
        else:
            raise ValueError('unknown tag')
        if encode(value, depth) != data[start:end]:
            raise ValueError('noncanonical encoding')
        return value, end
    try:
        value, end = item(0, len(data), 0)
    except (UnicodeError, OverflowError, ArithmeticError) as exc:
        raise ValueError('invalid typed payload') from exc
    if end != len(data):
        raise ValueError('trailing bytes')
    return value
