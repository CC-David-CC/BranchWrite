#!/usr/bin/env python3
"""Read-only offline bundle validation. It does not issue product acceptance."""
import ast
import csv
import hashlib
import sys
import tomllib
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from reference.language import parse


def load(path):
    with (ROOT/path).open('rb') as f:return tomllib.load(f)


def validate():
    cases=load('acceptance/cases.toml')['case']
    tickets=load('acceptance/tickets.toml')['ticket']
    ids={c['id'] for c in cases};tids={t['id'] for t in tickets}
    if len(ids)!=len(cases) or len(tids)!=len(tickets):raise ValueError('duplicate catalogue identity')
    if any(c['status']!='not_run' for c in cases):raise ValueError('product status must remain not_run in this handoff')
    if any(t['status']!='not_started' for t in tickets):raise ValueError('ticket status misrepresented')
    if len([c for c in cases if c['id'].startswith('BW-')])!=211:raise ValueError('lost inherited case')
    if any(c['ticket'] not in tids for c in cases):raise ValueError('missing owner')
    expected={t['id']:{c['id'] for c in cases if c['ticket']==t['id']} for t in tickets}
    if any(set(t['case_ids'])!=expected[t['id']] for t in tickets):raise ValueError('coverage mapping mismatch')
    deps={t['id']:set(t['depends_on']) for t in tickets}
    if any(not ds<=tids for ds in deps.values()):raise ValueError('unknown dependency')
    seen=set()
    while len(seen)<len(tids):
        ready={t for t,ds in deps.items() if t not in seen and ds<=seen}
        if not ready:raise ValueError('cyclic tickets')
        seen.update(ready)
    spec=hashlib.sha256((ROOT/'spec/BW_FIRST_PRINCIPLES_v0.6.md').read_bytes()).hexdigest()
    if load('acceptance/cases.toml')['spec_sha256']!=spec:raise ValueError('stale active spec binding')
    migration=list(csv.DictReader((ROOT/'acceptance/migration.tsv').open(),delimiter='\t'))
    if {m['case_id'] for m in migration}!={c['id'] for c in cases if c['id'].startswith('BW-')}:raise ValueError('migration lost source case')
    for path in (ROOT/'examples').glob('*.bw'):parse(path.read_text(encoding='utf-8'))
    selectors={'greedy','dist','mirostat2','adaptive_p'}
    for profile in load('configs/profiles.toml')['profile']:
        stages=profile['stages']
        if sum(x in selectors for x in stages)!=1 or stages[-1]!=profile['selector'] or stages[-1] not in selectors:
            raise ValueError('invalid final selector')
        if 'temperature' in stages and 'dynatemp' in stages:raise ValueError('two temperature laws')
    for path in ROOT.rglob('*.toml'):
        with path.open('rb') as f:tomllib.load(f)
    for path in ROOT.rglob('*.py'):
        if 'provenance' in path.parts:continue
        tree=ast.parse(path.read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node,ast.Import) and any(x.name.split('.')[0] in {'json','pickle'} for x in node.names):
                raise ValueError('active JSON/pickle dependency')
            if isinstance(node,ast.ImportFrom) and (node.module or '').split('.')[0] in {'json','pickle'}:
                raise ValueError('active JSON/pickle dependency')
    if any(ROOT.rglob('*.json')) or any(ROOT.rglob('*.jsonl')):raise ValueError('unexpected active JSON file')
    manifest=ROOT/'MANIFEST.sha256'
    entries={}
    for line in manifest.read_text().splitlines():
        digest,name=line.split('  ',1)
        if name in entries:raise ValueError('duplicate manifest entry')
        p=(ROOT/name).resolve()
        if not p.is_relative_to(ROOT.resolve()):raise ValueError('manifest escape')
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=digest:raise ValueError('manifest mismatch: '+name)
        entries[name]=digest
    actual={str(p.relative_to(ROOT)) for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='MANIFEST.sha256' and p.suffix!='.pyc'}
    if set(entries)!=actual:raise ValueError('manifest coverage mismatch')
    return len(cases),len(tickets),len(entries)

if __name__=='__main__':
    try:
        cases,tickets,files=validate()
    except (ValueError,OSError,KeyError,tomllib.TOMLDecodeError) as exc:
        print('HANDOFF_INVALID: '+str(exc),file=sys.stderr);sys.exit(1)
    print(f'HANDOFF_VALID: {cases} not-run product cases; {tickets} planned tickets; {files} hashed payload files')
    print('This checks the handoff, not a BranchWrite/native/GPU implementation.')
