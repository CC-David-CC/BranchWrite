"""Finite-language byte-prefix oracle, NOT a general GBNF/tokenizer implementation."""
from dataclasses import dataclass, replace
from .language import parse, OPERATIONS

@dataclass(frozen=True)
class Matcher:
    choices: tuple[bytes, ...]
    prefix: bytes = b''

    def __post_init__(self):
        if not self.choices or len(set(self.choices)) != len(self.choices):
            raise ValueError('nonempty unique language required')
        for item in self.choices:
            item.decode('utf-8', errors='strict')
        if not any(x.startswith(self.prefix) for x in self.choices):
            raise ValueError('prefix outside language')

    @property
    def complete(self) -> bool:
        return self.prefix in self.choices

    def permits(self, piece: bytes) -> bool:
        if not isinstance(piece, bytes) or not piece:
            return False  # EOS is separate, not an empty token piece
        return any(x.startswith(self.prefix + piece) for x in self.choices)

    def advance(self, piece: bytes) -> 'Matcher':
        if not self.permits(piece):
            raise ValueError('illegal token piece')
        return replace(self, prefix=self.prefix + piece)

    def fork(self) -> 'Matcher':
        return replace(self)  # all referenced data immutable


def literal(value: str) -> str:
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t') + '"'


def choice_grammar(records: tuple[str, ...]) -> str:
    if not records or len(set(records)) != len(records):
        raise ValueError('nonempty unique records required')
    for record in records:
        nodes = parse(record)
        if len(nodes) != 1 or nodes[0].op not in OPERATIONS:
            raise ValueError('one operation per choice')
    return 'root ::= ' + ' | '.join(literal(x) for x in records) + '\n'
