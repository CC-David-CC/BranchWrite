from pathlib import Path
import json,hashlib,shutil,os
from branchwrite.execution import Executor,Grant
from branchwrite.terminal import ShellConfig
D=Path(__file__).parent
assert (D/'result.json').exists()
assert not Path('/proc',(D/'code.pid').read_text()).exists()
workspace=D/'code-state/world/workspace';candidate=D/'independent-source';candidate.mkdir()
shutil.copy2(workspace/'intervals.py',candidate/'intervals.py');shutil.copy2(D/'oracle.py',candidate/'oracle.py')
e=Executor.create(candidate,D/'independent-world',shell=ShellConfig(timeout=10))
g=Grant((),False,read_paths=('intervals.py','oracle.py'),allow_shell=True)
r=e.run_shell('independent-interval-oracle',g,'python3 oracle.py')
result=dict(status='PASS' if r.exit_code==0 else 'FAIL',exit_code=r.exit_code,stdout=r.stdout.read_bytes().decode(),stderr=r.stderr.read_bytes().decode(),candidate_sha256=hashlib.sha256((candidate/'intervals.py').read_bytes()).hexdigest(),isolation=r.details['isolation'],seed=47031,random_cases=1000,additional_probes=2,scope='Independent discrete half-step interval occupancy oracle; no numerical model oracle')
(D/'independent-audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));assert r.exit_code==0
