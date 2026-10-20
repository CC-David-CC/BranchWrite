"""Strict syntax oracle for BW text; no authority, type resolution, or execution."""
from dataclasses import dataclass
import re

ATOM = re.compile(r"[A-Za-z0-9_./:@-]+\Z")
NAME = re.compile(r"[A-Za-z][A-Za-z0-9_.-]*\Z")
# One declaration drives syntax validation and grammar-record admission.
FIELDS = {
    'EXPAND': ('from task profile', ''), 'CONTINUE': ('from profile', ''),
    'PLAN': ('from against', ''), 'ACT': ('plan', ''),
    'OBSERVE': ('target', ''), 'TRANSFORM': ('input contract', 'profile'),
    'SAVE': ('input name', ''), 'VERIFY': ('input contract', 'profile'),
    'CHALLENGE': ('input contract', 'profile'), 'COMPARE': ('input criteria', 'profile'),
    'SELECT': ('input rule', ''), 'COMPOSE': ('input contract', ''),
    'COMMIT': ('input target evidence', ''), 'ABANDON': ('target reason', ''),
    'FLOW': ('', 'input output'), 'REPEAT': ('max until exhausted', ''),
    'BRANCH': ('base', 'world seed'), 'PARALLEL.PLAN': ('base budget', ''),
    'PARALLEL.DO': ('base budget', ''), 'ON': ('signal', ''),
    'VALUE': ('type ref', ''), 'TEXT': ('', ''),
}
BLOCKS = frozenset(('FLOW', 'REPEAT', 'BRANCH', 'PARALLEL.PLAN', 'PARALLEL.DO', 'ON'))
OPERATIONS = frozenset(FIELDS) - BLOCKS - {'VALUE', 'TEXT'}

@dataclass(frozen=True)
class Node:
    op: str
    name: str
    fields: tuple[tuple[str, str], ...] = ()
    result: str | None = None
    children: tuple['Node', ...] = ()
    text: str | None = None


def parse(source: str, *, max_bytes: int = 1_000_000, max_depth: int = 32,
          max_nodes: int = 10000) -> tuple[Node, ...]:
    if not isinstance(source, str) or len(source.encode('utf-8')) > max_bytes:
        raise ValueError('invalid text or byte limit')
    if '\r' in source or '\x00' in source or not source.endswith('\n'):
        raise ValueError('canonical LF-terminated text required')
    lines = [line + '\n' for line in source.split('\n')[:-1]]
    index = 0
    count = 0

    def sequence(depth: int, nested: bool) -> tuple[Node, ...]:
        nonlocal index, count
        if depth > max_depth:
            raise ValueError('depth limit')
        out = []
        while index < len(lines):
            raw = lines[index][:-1]  # final LF only
            index += 1
            if raw == 'END':
                if not nested:
                    raise ValueError('unexpected END')
                return tuple(out)
            if not raw or raw != raw.strip() or '\t' in raw or '  ' in raw:
                raise ValueError('noncanonical whitespace')
            words = raw.split(' ')
            if len(words) < 2 or words[0] not in FIELDS or not NAME.fullmatch(words[1]):
                raise ValueError('unknown operation or invalid name')
            op, name = words[:2]
            rest = words[2:]
            result = None
            if '->' in rest:
                at = rest.index('->')
                if len(rest) != at + 2 or not NAME.fullmatch(rest[-1]):
                    raise ValueError('invalid result binding')
                result = rest[-1]
                rest = rest[:at]
            fields = {}
            for word in rest:
                if word.count('=') != 1:
                    raise ValueError('field must be key=atom')
                key, value = word.split('=')
                if not NAME.fullmatch(key) or not ATOM.fullmatch(value) or key in fields:
                    raise ValueError('invalid or duplicate field')
                fields[key] = value
            required, optional = (set(x.split()) for x in FIELDS[op])
            if not required <= fields.keys() or not fields.keys() <= required | optional:
                raise ValueError('missing or unknown field')
            if op == 'REPEAT':
                value = fields['max']
                if not re.fullmatch(r'[1-9][0-9]*', value) or int(value) > 1000000:
                    raise ValueError('bounded positive repeat required')
            count += 1
            if count > max_nodes:
                raise ValueError('node limit')
            children = ()
            text = None
            if op == 'TEXT':
                if result is not None:
                    raise ValueError('TEXT binds its own name')
                payload = []
                while index < len(lines) and lines[index] != 'END\n':
                    line = lines[index]
                    index += 1
                    if not line.startswith('|'):
                        raise ValueError('literal lines need a prefix')
                    payload.append(line[1:])
                if index >= len(lines):
                    raise ValueError('unterminated TEXT')
                index += 1
                text = ''.join(payload)
            elif op in BLOCKS:
                children = sequence(depth + 1, True)
            out.append(Node(op, name, tuple(sorted(fields.items())), result, children, text))
        if nested:
            raise ValueError('unterminated block')
        return tuple(out)

    return sequence(0, False)


def render(nodes: tuple[Node, ...]) -> str:
    lines = []
    for node in nodes:
        line = ' '.join([node.op, node.name] + [f'{k}={v}' for k, v in node.fields])
        if node.result is not None:
            line += ' -> ' + node.result
        lines.append(line + '\n')
        if node.op == 'TEXT':
            if node.text:
                if not node.text.endswith('\n'):
                    raise ValueError('literal payload must have LF endings')
                lines.extend('|' + x for x in [line + '\n' for line in node.text.split('\n')[:-1]])
            lines.append('END\n')
        elif node.op in BLOCKS:
            lines.append(render(node.children))
            lines.append('END\n')
    result = ''.join(lines)
    if result and parse(result) != nodes:
        raise ValueError('invalid AST')
    return result
