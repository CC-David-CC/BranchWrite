from pathlib import Path
import json,shutil,sys
from branchwrite.execution import Executor,Grant
root=Path(__file__).parent;label=sys.argv[1];d=root/label
source=d/'nested-input-source';shutil.copytree(d/'state/world/workspace',source)
(source/'tests/test_nested_invalid_input.py').write_text("""import unittest,json
from branchwrite.base_choice import resolve_base_proposal
class NestedInvalidInputs(unittest.TestCase):
 def test_nested_invalid_json_is_rejected_as_value_error(self):
  row=dict(base_id='1'*64,branch='base',snapshot='2'*64,source_revision='a'*40,execution_profile_id='b'*64,prefix_tokens=1,capacity=262144)
  for depth in range(1,1101):
   for text in ['['*depth+'0'+']'*depth,'{\"schema\":1,\"base_id\":\"'+'1'*64+'\",\"reason\":'+'['*depth+'0'+']'*depth+'}']:
    with self.subTest(depth=depth),self.assertRaises(ValueError):resolve_base_proposal(text,[row],required_revision='a'*40,required_profile='b'*64,reserve_tokens=8192)
""")
e=Executor.create(source,d/'nested-input-world');r=e.run_tests('nested-input-review',Grant((),True),timeout=30)
(d/'nested-input.stdout').write_bytes(r.stdout.read_bytes());(d/'nested-input.stderr').write_bytes(r.stderr.read_bytes());result=dict(status='PASS' if r.exit_code==0 else 'FAIL',exit_code=r.exit_code,scope='Targeted malformed-JSON recursion review, read-only OS sandbox',depths=1100,input_variants=2200)
(d/'nested-input-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));raise SystemExit(r.exit_code!=0)
