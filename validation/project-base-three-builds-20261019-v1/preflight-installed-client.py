import json,sys
from pathlib import Path
from branchwrite.coding_cli import build_launch
root=Path(sys.argv[1]);rows=[]
for label in ['A-all-product-source','B-compact-selected','C-compact-examples']:
 fixture=json.loads((root/('coding-'+label)/'workload.prepared.json').read_text())
 connection=dict(endpoint_url='http://127.0.0.1:12345',endpoint_pin='preflight-only-no-request',model_contract_id='a'*64,execution_profile_id='b'*64,eos_tokens=[1])
 launch=build_launch(fixture['source'],Path(fixture['task_file']).read_text(),connection,branch=fixture['branch'],read_paths=['branchwrite','tests'],create_paths=['branchwrite/base_choice.py'],test_commands=['python3 -m unittest discover -s tests -v'],from_prefix=fixture['base_branch'],from_snapshot='c'*64,sampler='greedy')
 assert launch is not None
 rows.append(dict(label=label,status='PASS',scope='installed CLI launch validation, placeholder identity only; no HTTP or inference'))
print(json.dumps(rows,indent=2))
