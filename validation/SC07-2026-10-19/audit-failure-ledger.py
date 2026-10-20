"""Audit only a terminal client's copied workflow ledger."""
from pathlib import Path
import hashlib,json,shutil,sys,zipfile
b=Path(__file__).parent
assert (b/'command.exit').read_text().strip()=='1','expected terminal failure'
sys.path.insert(0,'/home/dflanag3/src/branchwrite-shell-admission-20261019')
from branchwrite.records import RuntimeLog,Artifact,decode
from branchwrite.kernel import FrameKernel
def hashes(root):
 return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
ledger=b/'state/ledger';before=hashes(ledger);copy=b/'offline-ledger-copy'
shutil.copytree(ledger,copy)
tools=[];models=[]
with RuntimeLog(copy) as log:
 for frame in FrameKernel(log).frames():
  if frame['state']!='Closed' or frame['contract'][0] not in ('ToolOutcome','ModelOutput'):continue
  value=decode(log.read_artifact(Artifact(*frame['result'])))
  inputs=decode(log.read_artifact(Artifact(*frame['inputs'])))
  result=value[2]
  if frame['contract'][0]=='ToolOutcome':
   tools.append(dict(tool=result['tool'],arguments=inputs[4],disposition=result['disposition'],exit_code=result['exit_code'],stdout=log.read_artifact(Artifact(*result['stdout'])).decode('utf8','replace'),stderr=log.read_artifact(Artifact(*result['stderr'])).decode('utf8','replace'),details=result['details']))
  else:models.append(dict(tokens=result['consumed_output_tokens'],grammar_state=inputs.get('config',{}).get('grammar_state')))
assert hashes(ledger)==before,'producer ledger changed'
print('tools',[(t['tool'],t['exit_code']) for t in tools])
fixture=json.loads((b/'workload.json').read_text())
launch=json.loads((b/'state/coding-launch.json').read_text())['launch']
assert launch['fork']==dict(source_branch='standalone-sc06a-q8-20261019-v1',snapshot='a1021cebd62f546ee8080e1fc2edcd802625e07b7615fa3914fee6525a8c46eb')
records=[json.loads(p.read_text()) for p in (b/'state/cow-operations').glob('*.json')]
registrations=[r for r in records if r['path']=='/cow/grammars']
assert len(registrations)==1 and registrations[0]['state']=='complete'
states=set(registrations[0]['receipt']['states'].values())
assert all(m['grammar_state'] in states for m in models)
proof=json.loads((b/'output/autonomous-cli-admission.json').read_text())
installed=Path('/home/dflanag3/spatial-artifacts/branchwrite-shell-admission-package-20261019-v1/installed-check/venv')
wheel=next((installed.parents[1]/'wheel').glob('*.whl'));modules=[]
with zipfile.ZipFile(wheel) as archive:
 for name,value in proof['branchwrite_modules'].items():
  path=Path(value);assert path.is_relative_to(installed)
  index=path.parts.index('branchwrite');member='/'.join(path.parts[index:])
  digest=hashlib.sha256(path.read_bytes()).hexdigest()
  assert digest==hashlib.sha256(archive.read(member)).hexdigest()
  modules.append(dict(name=name,sha256=digest))
assert modules and not any('/home/dflanag3/src/' in entry for entry in proof['sys_path'])
driver=json.loads((b/'output/result.json').read_text())
result=dict(status='SETTLED_FAILURE_FORENSICS',ledger_unchanged=True,model_calls=len(models),output_tokens=sum(m['tokens'] for m in models),whole_cli_seconds=driver['positive']['seconds'],installed_modules=modules,wheel_sha256=hashlib.sha256(wheel.read_bytes()).hexdigest(),tools=tools,model_requests=models,numerical_oracle='NOT_RUN')
(b/'failure-ledger-audit.json').write_text(json.dumps(result,indent=2)+chr(10))
print(json.dumps({k:v for k,v in result.items() if k not in ['tools','model_requests','installed_modules']}))
