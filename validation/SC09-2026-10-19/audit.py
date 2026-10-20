"""Independent settled-output checks; this code never supplies model actions."""
import pathlib,json,hashlib,stat,subprocess,sys,tempfile,argparse,contextlib,io,random
from unittest.mock import patch
b=pathlib.Path(__file__).parent
assert (b/'command.exit').read_text().strip()=='0'
manifest=json.loads((b/'baseline.json').read_text())
source=b/'source';candidate=b/'state/world/workspace';changed=[]
for name,digest in manifest['files'].items():
 original=source/name;current=candidate/name
 assert hashlib.sha256(original.read_bytes()).hexdigest()==digest,('original changed',name)
 assert stat.S_IMODE(original.stat().st_mode)==manifest['modes'][name]
 assert current.is_file() and not current.is_symlink(),('candidate missing/link',name)
 assert stat.S_IMODE(current.stat().st_mode)==manifest['modes'][name]
 if hashlib.sha256(current.read_bytes()).hexdigest()!=digest:changed.append(name)
assert changed and set(changed)<={'branchwrite/__main__.py','branchwrite/coding_cli.py'},changed
for name,digest in manifest['git_admin'].items():
 assert hashlib.sha256((source/name).read_bytes()).hexdigest()==digest,('Git admin changed',name)
assert not (candidate/'.git').exists()
assert {str(p.relative_to(candidate)) for p in candidate.rglob('*') if p.is_file()}==set(manifest['files'])
tests=[]
for name in ['test_inline_task.py','test_coding_launcher.py','test_connection_admission.py']:
 p=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','tests','-p',name,'-v'],cwd=candidate,capture_output=True,text=True,timeout=60)
 (b/('operator-'+name+'.stderr')).write_text(p.stderr)
 tests.append(dict(pattern=name,exit_code=p.returncode))
 assert p.returncode==0,p.stderr
sys.path.insert(0,str(candidate))
from branchwrite.__main__ import main
from branchwrite.coding_cli import read_launch
seed=7419;rng=random.Random(seed)
words=['café','雪','λ','🙂',chr(34)+chr(39),'literal $HOME','$(echo untouched)','semi;colon']
for case in range(64):
 with tempfile.TemporaryDirectory() as t:
  root=pathlib.Path(t);project=root/'project';project.mkdir();(project/'app.py').write_text('pass'+chr(10))
  connection=root/'connection.json';connection.write_text(json.dumps(dict(endpoint_url='http://127.0.0.1:1',endpoint_pin='owned',model_contract_id='m',execution_profile_id='p',eos_tokens=[256])))
  text='case '+str(case)+': '+' '.join(rng.choices(words,k=rng.randrange(1,10)))+(' '+chr(10))*rng.randrange(1,4)
  if case%8==0:text='--literal '+text
  state=root/'state';args=['code',str(project),'--connection',str(connection),'--state',str(state),'--branch','case','--edit','app.py','--test-command','python3 -m unittest']
  if case%4==3:
   task=root/'task';task.write_text(text);args+=['--task-file',str(task)]
  else:args+=['--task='+text]
  out=io.StringIO();err=io.StringIO()
  with patch('branchwrite.coding_cli.run_saved',return_value=(0,{'verified':True})) as run,contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
   code=main(args)
  assert code==0,(case,err.getvalue());run.assert_called_once()
  assert read_launch(state)['config']['bindings']['task']['value']==text,case
result=dict(status='PASS',changed=changed,original_source_unchanged=True,original_git_admin_unchanged=True,git_admin_absent_from_workspace=True,protected_tests=tests,generated_cases=64,seed=seed,scope='Functional coding/client result, not numerical certification')
(b/'audit-result.json').write_text(json.dumps(result,indent=2)+chr(10));print(json.dumps(result))
