from pathlib import Path
import json,hashlib,shutil
from branchwrite.execution import Executor,Grant
D=Path(__file__).parent
assert (D/'command.exit').read_text().strip()=='0'
base=json.loads((D/'baseline-inventory.json').read_text());source=D/'source';workspace=D/'state/world/workspace'
assert all(hashlib.sha256((source/n).read_bytes()).hexdigest()==sha for n,sha in base.items())
actual={str(p.relative_to(workspace)):hashlib.sha256(p.read_bytes()).hexdigest() for p in workspace.rglob('*') if p.is_file()}
assert set(actual)==set(base)
changed=[n for n in actual if actual[n]!=base[n]];assert changed==['dependencies.py'],changed
isolated=D/'independent-source';shutil.copytree(workspace,isolated)
body=(D/'audit-independent.py').read_text().replace("path=Path(sys.argv[1])", "path=Path('/work/dependencies.py')")
independent='import unittest\nclass Independent(unittest.TestCase):\n def test_generated(self):\n'+''.join('  '+line+'\n' for line in body.splitlines())
(isolated/'tests/test_independent.py').write_text(independent)
e=Executor.create(isolated,D/'independent-world');tested=e.run_tests('sc19-independent',Grant((),True),timeout=30)
(D/'independent.stdout').write_bytes(tested.stdout.read_bytes());(D/'independent.stderr').write_bytes(tested.stderr.read_bytes())
r=dict(status='PASS' if tested.exit_code==0 else 'FAIL',exit_code=tested.exit_code,changed=changed,original_source_unchanged=True,protected_tests_unchanged=True,generated_cases=400,seed=20261019,scope='Candidate and independent oracle executed in read-only OS sandbox; no package marker added')
(D/'audit-output-result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));raise SystemExit(tested.exit_code!=0)
