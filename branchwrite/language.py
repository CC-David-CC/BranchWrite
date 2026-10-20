"""Production .bw syntax: one definition table, immutable statements, explicit stack.

Parsing is not name resolution, authority, execution or product qualification.
The reference package remains an independent test oracle and is never imported.
"""
from dataclasses import dataclass
from types import MappingProxyType
import re

MAX_SOURCE_BYTES=1000000
MAX_DEPTH=32
MAX_NODES=10000
_NAME=re.compile(r'[A-Za-z][A-Za-z0-9_.-]*\Z')
_ATOM=re.compile(r'[A-Za-z0-9_./:@-]+\Z')

class ProgramSyntaxError(ValueError):pass

@dataclass(frozen=True,slots=True)
class Definition:
    required:tuple=()
    optional:tuple=()
    block:bool=False
    operation:bool=True

# This table drives production parsing/rendering and control-grammar admission.
# Required field names are language data; they never grant the named capability.
DEFINITIONS=MappingProxyType({
 'EXPAND':Definition(('from','task','profile')),
 'CONTINUE':Definition(('from','profile')),
 'PLAN':Definition(('from','against')),
 'ACT':Definition(('plan',)),
 'OBSERVE':Definition(('target',)),
 'TRANSFORM':Definition(('input','contract'),('profile','evidence')),
 'SAVE':Definition(('input','name')),
 'VERIFY':Definition(('input','contract'),('profile',)),
 'CHALLENGE':Definition(('input','contract'),('profile',)),
 'COMPARE':Definition(('input','criteria'),('profile',)),
 'SELECT':Definition(('input','rule')),
 'COMPOSE':Definition(('input','contract')),
 'COMMIT':Definition(('input','target','evidence')),
 'ABANDON':Definition(('target','reason')),
 'FLOW':Definition((),('input','output'),True,False),
 'REPEAT':Definition(('max','until','exhausted'),(),True,False),
 'BRANCH':Definition(('base',),('world','seed'),True,False),
 'PARALLEL.PLAN':Definition(('base','budget'),(),True,False),
 'PARALLEL.DO':Definition(('base','budget'),(),True,False),
 'ON':Definition(('signal',),(),True,False),
 'VALUE':Definition(('type','ref'),(),False,False),
 'TEXT':Definition((),(),False,False),
})
OPERATIONS=frozenset(k for k,v in DEFINITIONS.items() if v.operation)

def _limit(value):
    if type(value) is not int or value<=0:raise ProgramSyntaxError('limits must be positive exact integers')
    return value

def _header(opcode,label,attributes,output):
    if type(opcode) is not str or opcode not in DEFINITIONS:raise ProgramSyntaxError('unknown instruction')
    if type(label) is not str or not _NAME.fullmatch(label):raise ProgramSyntaxError('invalid local label')
    if output is not None and (type(output) is not str or not _NAME.fullmatch(output)):
        raise ProgramSyntaxError('invalid result label')
    if type(attributes) is not tuple:raise ProgramSyntaxError('immutable field tuple required')
    fields={}
    for item in attributes:
        if type(item) is not tuple or len(item)!=2:raise ProgramSyntaxError('invalid field pair')
        k,v=item
        if type(k) is not str or type(v) is not str or not _ATOM.fullmatch(v) or k in fields:
            raise ProgramSyntaxError('invalid or duplicate field')
        fields[k]=v
    definition=DEFINITIONS[opcode]
    if not set(definition.required)<=set(fields) or not set(fields)<=set(definition.required+definition.optional):
        raise ProgramSyntaxError('missing or unknown field')
    if opcode=='TEXT' and output is not None:raise ProgramSyntaxError('TEXT cannot redirect a result')
    if opcode=='REPEAT':
        count=fields['max']
        if not re.fullmatch(r'[1-9][0-9]*',count) or len(count)>7 or int(count)>1000000:
            raise ProgramSyntaxError('bounded canonical positive repeat required')
    return definition,tuple(sorted(fields.items()))

@dataclass(frozen=True,slots=True)
class Statement:
    opcode:str
    label:str
    attributes:tuple=()
    output:str|None=None
    body:tuple=()
    literal:str|None=None
    def __post_init__(self):
        definition,fields=_header(self.opcode,self.label,self.attributes,self.output)
        object.__setattr__(self,'attributes',fields)
        if type(self.body) is not tuple or any(type(n) is not Statement for n in self.body):
            raise ProgramSyntaxError('immutable statement body required')
        if not definition.block and self.body:raise ProgramSyntaxError('leaf instruction cannot contain executable children')
        if self.opcode=='TEXT':
            if type(self.literal) is not str or (self.literal and not self.literal.endswith('\n')) or '\r' in self.literal or '\x00' in self.literal:
                raise ProgramSyntaxError('TEXT requires exact LF-terminated literal data')
            try:self.literal.encode('utf8')
            except UnicodeError as exc:raise ProgramSyntaxError('literal is not valid UTF-8') from exc
        elif self.literal is not None:raise ProgramSyntaxError('literal belongs only to TEXT')

def _read_header(line):
    parts=line.split(' ')
    if any(not x for x in parts) or '\t' in line:raise ProgramSyntaxError('noncanonical control whitespace')
    output=None
    arrows=[i for i,x in enumerate(parts) if x=='->']
    if arrows:
        if len(arrows)!=1 or arrows[0]!=len(parts)-2:raise ProgramSyntaxError('invalid result arrow')
        output=parts[-1];parts=parts[:-2]
    if len(parts)<2:raise ProgramSyntaxError('instruction needs an operation and local label')
    fields=[]
    for part in parts[2:]:
        pair=part.split('=')
        if len(pair)!=2:raise ProgramSyntaxError('field must be key=atom')
        fields.append(tuple(pair))
    definition,fields=_header(parts[0],parts[1],tuple(fields),output)
    return (parts[0],parts[1],fields,output),definition

def parse(source,*,max_bytes=MAX_SOURCE_BYTES,max_depth=MAX_DEPTH,max_nodes=MAX_NODES):
    """Consume complete strict LF text. TEXT is opaque data, never parsed again."""
    _limit(max_bytes);_limit(max_depth);_limit(max_nodes)
    if type(source) is not str:raise ProgramSyntaxError('program must be UTF-8 text')
    try:size=len(source.encode('utf8'))
    except UnicodeError as exc:raise ProgramSyntaxError('program is not valid UTF-8') from exc
    if not source or size>max_bytes or not source.endswith('\n') or '\r' in source or '\x00' in source:
        raise ProgramSyntaxError('bounded nonempty LF-terminated program required')
    lines=source.split('\n')[:-1];stack=[(None,[])];at=0;count=0
    while at<len(lines):
        line=lines[at];at+=1
        try:
            if line=='END':
                if len(stack)==1:raise ProgramSyntaxError('unmatched END')
                header,children=stack.pop();stack[-1][1].append(Statement(*header,body=tuple(children)));continue
            header,definition=_read_header(line);count+=1
            if count>max_nodes:raise ProgramSyntaxError('program node limit exceeded')
            if header[0]=='TEXT':
                data=[]
                while at<len(lines) and lines[at]!='END':
                    payload=lines[at];at+=1
                    if not payload.startswith('|'):raise ProgramSyntaxError('TEXT payload line must start with a literal prefix')
                    data.append(payload[1:]+'\n')
                if at==len(lines):raise ProgramSyntaxError('unfinished TEXT block')
                at+=1;stack[-1][1].append(Statement(*header,literal=''.join(data)))
            elif definition.block:
                if len(stack)>max_depth:raise ProgramSyntaxError('program block depth limit exceeded')
                stack.append((header,[]))
            else:stack[-1][1].append(Statement(*header))
        except ProgramSyntaxError as exc:
            raise ProgramSyntaxError('line '+str(at)+': '+str(exc)) from exc
    if len(stack)!=1:raise ProgramSyntaxError('unfinished structural block')
    return tuple(stack[0][1])

def render(statements,*,max_bytes=MAX_SOURCE_BYTES,max_depth=MAX_DEPTH,max_nodes=MAX_NODES):
    """Canonical fields/spacing, exact literal LF bytes; no source execution."""
    _limit(max_bytes);_limit(max_depth);_limit(max_nodes)
    if type(statements) is not tuple or not statements:raise ProgramSyntaxError('nonempty immutable program required')
    stack=[(node,0) for node in reversed(statements)];parts=[];size=0;count=0
    def emit(text):
        nonlocal size
        size+=len(text.encode('utf8'))
        if size>max_bytes:raise ProgramSyntaxError('rendered program byte limit exceeded')
        parts.append(text)
    while stack:
        item,depth=stack.pop()
        if item is None:emit('END\n');continue
        if type(item) is not Statement:raise ProgramSyntaxError('typed statement required')
        count+=1
        if count>max_nodes:raise ProgramSyntaxError('rendered program node limit exceeded')
        definition,_=_header(item.opcode,item.label,item.attributes,item.output)
        line=item.opcode+' '+item.label+''.join(' '+k+'='+v for k,v in item.attributes)
        if item.output is not None:line+=' -> '+item.output
        emit(line+'\n')
        if item.opcode=='TEXT':
            if item.literal:
                for payload in item.literal.split('\n')[:-1]:emit('|'+payload+'\n')
            emit('END\n')
        elif definition.block:
            if depth+1>max_depth:raise ProgramSyntaxError('rendered program block depth limit exceeded')
            stack.append((None,depth))
            stack.extend((child,depth+1) for child in reversed(item.body))
    return ''.join(parts)
