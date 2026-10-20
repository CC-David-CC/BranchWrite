"""Run only after CLI settlement; protected independent reference, not model input."""
import importlib.util,itertools,random,sys,json,copy
from pathlib import Path
path=Path(sys.argv[1]);spec=importlib.util.spec_from_file_location('candidate',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
rng=random.Random(20261019)
for case in range(400):
 names=list('abcdefg'[:rng.randrange(0,8)]);g={n:[d for d in names if rng.random()<.15] for n in names if rng.random()<.85}
 nodes=sorted(set(g).union(*(set(v) for v in g.values())))
 expected=next((list(p) for p in itertools.permutations(nodes) if all(p.index(d)<p.index(n) for n,ds in g.items() for d in ds)),None)
 before=copy.deepcopy(g)
 try:actual=module.build_order(g)
 except ValueError:
  assert expected is None,(case,g,expected)
 else:assert actual==expected,(case,g,actual,expected)
 assert g==before,(case,'mutated input')
print(json.dumps(dict(status='PASS',cases=400,seed=20261019,oracle='exhaustive permutations; smallest valid ordering')))
