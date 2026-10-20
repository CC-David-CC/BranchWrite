from pathlib import Path
import json,hashlib,shutil,sys
from branchwrite.execution import Executor,Grant
root=Path(__file__).parent;d=Path(sys.argv[1]).resolve(strict=True)
assert (d/'command.exit').read_text().strip()=='0'
manifest=json.loads((root/'coding-input-manifest.json').read_text())['files']
source=Path('/home/dflanag3/src/branchwrite-q8-base-choice-candidate-20261019/candidate_project')
assert all(hashlib.sha256((source/n).read_bytes()).hexdigest()==row['sha256'] for n,row in manifest.items())
workspace=d/'state/world/workspace'
actual={str(q.relative_to(workspace)):hashlib.sha256(q.read_bytes()).hexdigest() for q in workspace.rglob('*') if q.is_file() and '__pycache__' not in q.parts}
assert set(actual)==set(manifest)|{'branchwrite/base_choice.py'},sorted(set(actual)^set(manifest))
assert all(actual[n]==row['sha256'] for n,row in manifest.items())
isolated=d/'independent-source';shutil.copytree(workspace,isolated)
body=(root/'independent-review/check_candidate.py').read_text().replace('path=Path(sys.argv[1]).resolve(strict=True)',"path=Path('/work/branchwrite/base_choice.py').resolve(strict=True)")
independent='import unittest\nclass Independent(unittest.TestCase):\n def test_host_boundary(self):\n'+''.join('  '+line+'\n' for line in body.splitlines())
(isolated/'tests/test_independent.py').write_text(independent)
e=Executor.create(isolated,d/'independent-world');tested=e.run_tests('base-choice-independent',Grant((),True),timeout=30)
(d/'independent.stdout').write_bytes(tested.stdout.read_bytes());(d/'independent.stderr').write_bytes(tested.stderr.read_bytes())
r=dict(status='PASS' if tested.exit_code==0 else 'FAIL',exit_code=tested.exit_code,added=['branchwrite/base_choice.py'],original_source_unchanged=True,protected_tests_unchanged=True,scope='Visible and independent tests in read-only OS sandbox; human code review still required')
(d/'audit-output-result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));raise SystemExit(tested.exit_code!=0)
