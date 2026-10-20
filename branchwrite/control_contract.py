"""Finite model control choices from the single production language definition.

A complete allowed statement is still only a proposal. Host eligibility, grants
and actual relevant state must be checked again at dispatch.
"""
from dataclasses import dataclass
from hashlib import sha256
import json,re
from pathlib import Path
from . import language
from .language import parse,render,OPERATIONS,ProgramSyntaxError
from .records import encode

@dataclass(frozen=True,slots=True)
class ControlContract:
    frontier_sha256:str
    identity:str
    choices:tuple
    grammar:str
    @property
    def inference_required(self):return len(self.choices)>1
    def accept(self,text):
        nodes=parse(text)
        if len(nodes)!=1 or nodes[0] not in self.choices:raise ProgramSyntaxError('control proposal is not one of the frozen eligible choices')
        return nodes[0]

def control_contract(choices,*,frontier_sha256):
    if type(frontier_sha256) is not str or not re.fullmatch(r'[0-9a-f]{64}',frontier_sha256):
        raise ProgramSyntaxError('exact host eligibility frontier digest required')
    if type(choices) not in (tuple,list) or not 1<=len(choices)<=256:raise ProgramSyntaxError('bounded nonempty control choices required')
    unique={};total=0
    for source in choices:
        nodes=parse(source)
        if len(nodes)!=1 or nodes[0].opcode not in OPERATIONS:raise ProgramSyntaxError('each control choice must be one operation, never a block or data declaration')
        canonical=render(nodes);total+=len(canonical.encode('utf8'))
        if total>262144:raise ProgramSyntaxError('control choice byte limit exceeded')
        unique[canonical]=nodes[0]
    rows=tuple(sorted(unique))
    grammar='root ::= '+' | '.join(json.dumps(row,ensure_ascii=False) for row in rows)+'\n'
    implementations=(sha256(Path(language.__file__).read_bytes()).hexdigest(),sha256(Path(__file__).read_bytes()).hexdigest())
    identity=sha256(encode(('bw.control-contract.v1',implementations,frontier_sha256,rows))).hexdigest()
    return ControlContract(frontier_sha256,identity,tuple(unique[row] for row in rows),grammar)
