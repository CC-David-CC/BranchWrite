import pathlib,subprocess,json,hashlib,sys,tempfile,random,argparse
from unittest.mock import patch
b=pathlib.Path(__file__).parent
before=json.loads((b/'baseline.json').read_text())['files']
original=b/'source';candidate=b/'state/world/workspace'
assert candidate.is_dir()
changed=[]
for name,digest in before.items():
 assert hashlib.sha256((original/name).read_bytes()).hexdigest()==digest,('original changed',name)
 p=candidate/name
 if p.exists() and hashlib.sha256(p.read_bytes()).hexdigest()!=digest:changed.append(name)
assert changed==['branchwrite/coding_cli.py'],changed
results=[]
for pattern in ['test_connection_admission.py','test_coding_launcher.py']:
 p=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','tests','-p',pattern,'-v'],cwd=candidate,capture_output=True,text=True,timeout=60)
 (b/('audit-'+pattern+'.stderr')).write_text(p.stderr)
 results.append(dict(pattern=pattern,returncode=p.returncode))
 assert p.returncode==0,p.stderr
sys.path.insert(0,str(candidate))
from branchwrite.coding_cli import start
seed=7417;rng=random.Random(seed);cases=0
for i in range(64):
 with tempfile.TemporaryDirectory() as t:
  root=pathlib.Path(t);project=root/'project';project.mkdir();(project/'app.py').write_text('pass'+chr(10))
  task=root/'task';task.write_text('Check project')
  config=dict(endpoint_url='http://127.0.0.1:1',endpoint_pin='owned',model_contract_id='model',execution_profile_id='profile',eos_tokens=[256])
  field=rng.choice(list(config));key=json.dumps(field)
  if i%2:key='"'+''.join(chr(92)+'u%04x'%ord(c) for c in field)+'"'
  path=root/'connection';path.write_text(json.dumps(config)[:-1]+','+key+':'+json.dumps(config[field])+'}')
  args=argparse.Namespace(max_steps=10,connection=str(path),project=str(project),task_file=str(task),branch='new',read=[],edit=['app.py'],create=[],test_command=['python3 -m unittest'],from_branch=None,from_snapshot=None,shell_timeout=120,state=str(root/'state'))
  with patch('branchwrite.coding_cli.run_saved') as run,patch('branchwrite.coding_cli._client') as client:
   try:start(args)
   except ValueError:pass
   else:raise AssertionError('duplicate accepted: '+field)
   run.assert_not_called();client.assert_not_called()
  assert not (root/'state').exists()
  cases+=1
report=dict(status='PASS',changed=changed,tests=results,seed=seed,generated_cases=cases,scope='Functional code audit, not a model numerical gate.')
(b/'audit-result.json').write_text(json.dumps(report,indent=2)+chr(10));print(json.dumps(report))
