from pathlib import Path
import json,sys,hashlib,shutil
from branchwrite.execution import Executor,Grant
b=Path(__file__).parent
assert (b/'command.exit').read_text().strip()=='0'
baseline=json.loads((b/'baseline.json').read_text());source=b/'source';workspace=b/'state/world/workspace'
for name,sha in baseline['files'].items():
 assert hashlib.sha256((source/name).read_bytes()).hexdigest()==sha,('original changed',name)
files={str(p.relative_to(workspace)):hashlib.sha256(p.read_bytes()).hexdigest() for p in workspace.rglob('*') if p.is_file()}
expected={n:s for n,s in baseline['files'].items() if not n.startswith('.git/')}
assert set(files)==set(expected)
changed=sorted(n for n in files if files[n]!=expected[n])
assert changed==baseline['expected_changes'],changed
audit=b/'independent-source';audit.mkdir();shutil.copytree(workspace/'taskboard',audit/'taskboard')
(audit/'tests').mkdir();(audit/'tests/__init__.py').touch()
shutil.copyfile(source/'tests/test_taskboard.py',audit/'tests/test_original.py')
shutil.copyfile(b/'independent-tests.py.txt',audit/'tests/test_generated.py')
executor=Executor.create(audit,b/'independent-world')
result=executor.run_tests('sc12-independent',Grant((),True),timeout=30)
out=result.stdout.read_bytes();err=result.stderr.read_bytes()
(b/'independent.stdout').write_bytes(out);(b/'independent.stderr').write_bytes(err)
value=dict(status='PASS' if result.exit_code==0 else 'FAIL',exit_code=result.exit_code,changed=changed,independent_generated_cases=200,invalid_classes=5,seed=12419,original_source_and_git_unchanged=True,protected_tests_unchanged=True,isolated_executor=True)
(b/'audit-output-result.json').write_text(json.dumps(value,indent=2));print(json.dumps(value))
raise SystemExit(result.exit_code!=0)
