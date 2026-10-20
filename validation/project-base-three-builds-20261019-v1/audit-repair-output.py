from pathlib import Path
import json,hashlib,shutil,sys
from branchwrite.execution import Executor,Grant
root=Path(__file__).parent;d=Path(sys.argv[1]).resolve(strict=True)
assert (d/'command.exit').read_text().strip()=='0'
manifest=json.loads((d/'source-manifest.json').read_text());source=d/'source';workspace=d/'state/world/workspace'
assert all(hashlib.sha256((source/n).read_bytes()).hexdigest()==r['sha256'] for n,r in manifest.items())
actual={str(q.relative_to(workspace)):hashlib.sha256(q.read_bytes()).hexdigest() for q in workspace.rglob('*') if q.is_file() and '__pycache__' not in q.parts}
assert set(actual)==set(manifest);changed=sorted(n for n in actual if actual[n]!=manifest[n]['sha256']);assert changed==['branchwrite/base_choice.py'],changed
isolated=d/'independent-source';shutil.copytree(workspace,isolated)
body=(root/'independent-review/check_candidate-v2.py').read_text().replace('path=Path(sys.argv[1]).resolve(strict=True)',"path=Path('/work/branchwrite/base_choice.py').resolve(strict=True)")
checks='import unittest,json\nclass Independent(unittest.TestCase):\n def test_host_boundary(self):\n'+''.join('  '+line+'\n' for line in body.splitlines())
checks+='\nclass IndependentShapes(unittest.TestCase):\n def test_mixed_nested_invalid_shapes(self):\n  from branchwrite.base_choice import resolve_base_proposal as f\n  row=dict(base_id=\'1\'*64,branch=\'base\',snapshot=\'2\'*64,source_revision=\'a\'*40,execution_profile_id=\'b\'*64,prefix_tokens=1,capacity=262144)\n  for depth in [3,17,63,127,511,1023,1499]:\n   value=\'0\'\n   for i in range(depth):value=\'[\'+value+\']\' if i%2 else \'{"x":\'+value+\'}\'\n   for text in [value,\'{"schema":1,"base_id":"\'+\'1\'*64+\'","reason":\'+value+\'}\']:\n    with self.subTest(depth=depth),self.assertRaises(ValueError):f(text,[row],required_revision=\'a\'*40,required_profile=\'b\'*64,reserve_tokens=8192)\n def test_valid_unicode_boundary_still_accepted(self):\n  from branchwrite.base_choice import resolve_base_proposal as f\n  row=dict(base_id=\'1\'*64,branch=\'α\'*64,snapshot=\'2\'*64,source_revision=\'a\'*40,execution_profile_id=\'b\'*64,prefix_tokens=1,capacity=262144)\n  reason=\'é\'*1024\n  result=f(json.dumps(dict(schema=1,base_id=\'1\'*64,reason=reason)),[row],required_revision=\'a\'*40,required_profile=\'b\'*64,reserve_tokens=8192)\n  self.assertEqual(result,dict(base=row,reason=reason))\n'
(isolated/'tests/test_independent.py').write_text(checks)
e=Executor.create(isolated,d/'independent-world');r=e.run_tests('repair-independent',Grant((),True),timeout=30)
(d/'independent.stdout').write_bytes(r.stdout.read_bytes());(d/'independent.stderr').write_bytes(r.stderr.read_bytes());result=dict(status='PASS' if r.exit_code==0 else 'FAIL',exit_code=r.exit_code,changed=changed,original_source_unchanged=True,protected_tests_unchanged=True,scope='Visible repair regression plus independent original checks and fresh mixed/Unicode cases in read-only OS sandbox; parent review still required')
(d/'audit-output-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));raise SystemExit(r.exit_code!=0)
