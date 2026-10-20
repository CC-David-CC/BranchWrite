#!/usr/bin/env python3
"""Offline illustration. No model, executor, external service or GPU is contacted."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from reference.grammar import Matcher, choice_grammar
from reference.language import parse
from reference.state import DecodeState, draw

records=('ACT run-a plan=plan-a -> outcome-a\n','ABANDON reject-a target=attempt-a reason=declined\n')
base=Matcher(tuple(x.encode() for x in records)).advance(b'A')
a=base.fork().advance(records[0].encode()[1:]);b=base.fork()
state=DecodeState('native-reference','grammar-reference',b'A','explore',b'stable-run')
xa,_=draw(state.explore('child-a'),'dist');xb,_=draw(state.explore('child-b'),'dist')
for path in sorted((ROOT/'examples').glob('*.bw')):
    ast=parse(path.read_text());print(f'Parsed {path.name}: {len(ast)} top-level definitions')
print('')
print(choice_grammar(records),end='')
print(f'Branch A complete: {a.complete}; Branch B complete: {b.complete}; B prefix: {b.prefix!r}')
print(f'Explicit child seed splits, oracle draws: A={xa:.8f}, B={xb:.8f}')
print('These are offline oracle values, not native trace or performance measurements.')
