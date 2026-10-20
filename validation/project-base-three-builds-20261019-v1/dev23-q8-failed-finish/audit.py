from pathlib import Path
import json,hashlib,shutil,stat
from branchwrite.execution import Executor,Grant
d=Path(__file__).parent
assert (d/'run.exit').read_text().strip()=='0'
result=json.loads((d/'run-result.json').read_text());assert result['verified'] is True
source=d/'project';workspace=d/'state/world/workspace'
original=json.loads((d/'source-before.json').read_text())
assert all(hashlib.sha256((source/name).read_bytes()).hexdigest()==digest for name,digest in original.items())
files={}
for p in workspace.rglob('*'):
 if '__pycache__' in p.parts:continue
 info=p.lstat()
 assert not stat.S_ISLNK(info.st_mode)
 if stat.S_ISREG(info.st_mode):
  assert info.st_nlink==1
  files[str(p.relative_to(workspace))]=hashlib.sha256(p.read_bytes()).hexdigest()
assert set(files)==set(original),(set(files)-set(original),set(original)-set(files))
changed=sorted(name for name in files if files[name]!=original[name]);assert changed==['calculator.py'],changed
isolated=d/'independent-source';shutil.copytree(workspace,isolated,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
(isolated/'tests/test_independent.py').write_text("import random,unittest\nfrom calculator import add\nclass Independent(unittest.TestCase):\n def test_seeded_integer_pairs(self):\n  rng=random.Random(20261019)\n  for i in range(1000):\n   a=rng.randint(-1000000,1000000);b=rng.randint(-1000000,1000000)\n   with self.subTest(i=i):self.assertEqual(add(a,b),a+b)\n def test_zero_and_large(self):\n  for a,b in [(0,0),(2**80,-2**80),(-1,-1),(2**100,1)]:\n   with self.subTest(a=a,b=b):self.assertEqual(add(a,b),a+b)\n")
executor=Executor.create(isolated,d/'independent-world')
r=executor.run_tests('independent-dev23-code-audit',Grant((),True),timeout=30)
(d/'independent.stdout').write_bytes(r.stdout.read_bytes());(d/'independent.stderr').write_bytes(r.stderr.read_bytes())
audit=dict(status='PASS' if r.exit_code==0 else 'FAIL',exit_code=r.exit_code,changed=changed,protected_tests_unchanged=True,original_source_unchanged=True,heldout_seed=20261019,heldout_integer_pairs=1000,edge_pairs=4,scope='Read-only OS sandbox; model never saw independent tests; parent code review separate')
(d/'audit-result.json').write_text(json.dumps(audit,indent=2)+'\n')
print(json.dumps(audit));raise SystemExit(r.exit_code!=0)
