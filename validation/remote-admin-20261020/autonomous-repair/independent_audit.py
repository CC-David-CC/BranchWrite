from pathlib import Path
import json,hashlib,subprocess,random
from branchwrite.records import RuntimeLog,Artifact,decode
from branchwrite.kernel import FrameKernel
r=Path(__file__).parent;project=Path('/home/dflanag3/projects/bw-autorepair-dev54-20261020');state=r/'session/turns/turn-1-ebdc02ffe06c75bf'
expected_tests=b'import unittest\nfrom calculator import total\n\nclass TotalTests(unittest.TestCase):\n    def test_empty(self): self.assertEqual(total([]), 0)\n    def test_one(self): self.assertEqual(total([7]), 7)\n    def test_many(self): self.assertEqual(total([2, 3, 4]), 9)\n\nif __name__ == "__main__": unittest.main()\n'
expected_source=b'def total(prices):\n    """Return the total price, including every item."""\n    return sum(prices)\n'
assert (project/'test_calculator.py').read_bytes()==expected_tests
assert (project/'calculator.py').read_bytes()==expected_source
# Execute only after matching both files to these known, independently held bytes.
p=subprocess.run(['python3','-B','-m','unittest','-v'],cwd=project,capture_output=True,text=True,timeout=20);(r/'independent-unit-tests.txt').write_text(p.stdout+p.stderr);assert p.returncode==0
scope={};exec(compile(expected_source,'<audited-known-fixture>','exec'),scope)
rng=random.Random(20261020)
for _ in range(100):
 xs=[rng.randrange(-10000,10000) for _ in range(rng.randrange(50))];ref=0
 for x in xs:ref+=x
 assert scope['total'](xs)==ref
with RuntimeLog(state/'ledger',read_only=True) as log:
 kernel=FrameKernel(log);tools=[];feedback=[];commands=[]
 for frame in kernel.frames():
  if not frame['result']:continue
  v=decode(log.read_artifact(Artifact(*frame['result'])))[2]
  if frame['contract'][0]=='ToolOutcome':
   tools.append({k:v[k] for k in ['tool','operation_id','exit_code','disposition']})
   if v['tool'] in ('run_shell','run_check'):
    isolation=v['details']['isolation'];assert isolation['worker_exited'];assert not isolation['namespace_members_after']
    assert v['details']['argv'][-1]=='python3 -m unittest test_calculator -v'
    inputs={item['path']:item for item in v['details']['inputs']}
    assert inputs['test_calculator.py']['sha256']==hashlib.sha256(expected_tests).hexdigest()
    commands.append(tools[-1])
   if v['tool']=='replace':
    plan=decode(log.read_artifact(Artifact(*frame['inputs'])))
    assert 'test_calculator.py' not in str(plan)
  if frame['contract'][0]=='BindingResult' and type(v) is dict and 'value' in v and v['value'][0]=='Text':
   try:data=json.loads(v['value'][1])
   except (ValueError,TypeError):continue
   if type(data) is dict and 'verification' in data:feedback.append(data)
 assert [(v['tool'],v['exit_code']) for v in commands]==[('run_shell',1),('run_check',0)]
 for check in commands:
  matches=[v for v in feedback if v.get('operation_id')==check['operation_id']];assert len(matches)==1
  assert matches[0]['exit_code']==check['exit_code'];assert matches[0]['verification']['outcome_operation_id']==check['operation_id']
 assert tools[0]['tool']=='run_shell';assert tools[-1]['tool']=='finish'
 report=dict(status='PASS',scope='one autonomous real-Q4 repair of a small Python function; not broad coding qualification',seconds=json.loads((r/'result.json').read_text())['seconds'],source_sha256=hashlib.sha256(expected_source).hexdigest(),tests_sha256=hashlib.sha256(expected_tests).hexdigest(),tests_unchanged=True,independent_existing_tests=3,independent_seeded_cases=100,seed=20261020,tool_sequence=tools,recorded_verdict_feedback_bound_to_exact_operations=True,operator_interventions=0)
(r/'independent-acceptance.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
