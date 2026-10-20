from pathlib import Path
import ast,hashlib,json,os,signal,socket,subprocess,sys,time,shutil
from branchwrite.context_pack import build_pack
from branchwrite.execution import Executor,Grant
d=Path(__file__).parent;root=d.parent;python=sys.executable
creds=json.loads((d/'credentials.json').read_text())
def write(name,value): (d/name).write_text(json.dumps(value,indent=2)+'\n')
def hashes(p):return {str(f.relative_to(p)):hashlib.sha256(f.read_bytes()).hexdigest() for f in p.rglob('*') if f.is_file() and '__pycache__' not in f.parts}
guard=d/'guard';guard.mkdir()
tree=ast.parse((root/'choice-client-driver-dev21.py').read_text())
base=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='HOST_GUARD' for x in n.targets))
hook=base+'\nBW_AUDIT_ACTIVE=True\n';compile(hook,str(guard/'sitecustomize.py'),'exec');(guard/'sitecustomize.py').write_text(hook)
with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
access=root/'client-access'
forward=['ssh','-N','-o','BatchMode=yes','-o','ExitOnForwardFailure=yes','-o','IdentitiesOnly=yes','-o','StrictHostKeyChecking=yes','-o','HostKeyAlias=bw-llm60','-o','UserKnownHostsFile='+str(access/'known_hosts'),'-i',str(access/'id_ed25519'),'-L',f'127.0.0.1:{port}:127.0.0.1:{creds["port"]}','dflanag3@llm-60']
with (d/'ssh.stderr').open('xb') as e:tunnel=subprocess.Popen(forward,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=e,start_new_session=True)
(d/'tunnel.pid').write_text(str(tunnel.pid))
deadline=time.monotonic()+20
while True:
 if tunnel.poll() is not None:raise RuntimeError('tunnel exited')
 try:
  with socket.create_connection(('127.0.0.1',port),timeout=1):break
 except OSError:
  if time.monotonic()>deadline:raise TimeoutError('SSH startup')
  time.sleep(.1)
connection=dict(endpoint_url=f'http://127.0.0.1:{port}',endpoint_pin='ssh-pinned-owned-llm60-api',model_contract_id=creds['model_contract_id'],execution_profile_id=creds['execution_profile_id'],eos_tokens=creds['eos_tokens'])
write('connection.json',connection)
entry="import sitecustomize,runpy;assert sitecustomize.BW_AUDIT_ACTIVE is True;runpy.run_module('branchwrite',run_name='__main__')"
def cli(label,args,expected=0,timeout=1800):
 env=dict(PATH='/usr/bin:/bin',HOME='/tmp',LANG='C.UTF-8',PYTHONPATH=str(guard),PYTHONDONTWRITEBYTECODE='1',BW_COW_API_KEY=creds['api_key'],BW_CLIENT_PROOF=str(d/(label+'-admission.json')))
 started=time.monotonic()
 with (d/(label+'.stdout')).open('xb') as o,(d/(label+'.stderr')).open('xb') as e:
  p=subprocess.Popen([python,'-B','-c',entry,*map(str,args)],stdin=subprocess.DEVNULL,stdout=o,stderr=e,env=env,cwd=d,start_new_session=True)
  (d/(label+'.pid')).write_text(str(p.pid));last=started
  while p.poll() is None:
   elapsed=time.monotonic()-started
   if elapsed>timeout:
    os.killpg(p.pid,signal.SIGTERM);p.wait(10);raise TimeoutError(label+' bounded timeout')
   if time.monotonic()-last>=30:print(json.dumps(dict(phase=label,pid=p.pid,elapsed_seconds=elapsed)),flush=True);last=time.monotonic()
   time.sleep(.2)
 elapsed=time.monotonic()-started;(d/(label+'.exit')).write_text(str(p.returncode))
 proof=json.loads((d/(label+'-admission.json')).read_text());assert not proof['native_modules_loaded'] and not proof['violations']
 assert p.returncode==expected,(label,p.returncode,(d/(label+'.stderr')).read_text()[-4000:])
 result=json.loads((d/(label+'.stdout')).read_text());write(label+'-result.json',dict(result=result,seconds=elapsed,parent_interventions_after_start=0))
 print(json.dumps(dict(phase=label,status='COMPLETE',seconds=elapsed)),flush=True)
 return result
specA='''PROJECT REQUIREMENTS, version A:
Implement outcomes.summarize(records) and formatter.render_summary(records).
records must be a list; each item must be a dict whose exit_code is an int, excluding bool. Extra fields are allowed. Otherwise raise ValueError. Do not mutate the list or records.
An exit code of zero passes; every other integer, including negative codes, fails.
summarize returns exactly {"total":N,"passed":P,"failed":F}.
render_summary returns exactly "N runs: P passed, F failed" using integer values.
Read current project files before editing. These facts are not tool grants.
'''
specB=specA+'''
VERSION B EXTENSION:
Both functions accept keyword-only include_cancelled=False.
False preserves all version A behavior.
If include_cancelled=True, an optional cancelled field must be bool when present. A true cancelled value requires exit_code=None; count that record as cancelled, not passed or failed. Other records still require non-bool integer exit_code.
summarize then includes cancelled (including zero); total includes every record.
render_summary then returns exactly "N runs: P passed, F failed, C cancelled".
Malformed cancellation records raise ValueError. Inputs remain unmodified.
'''
visibleA='''import unittest
from outcomes import summarize
from formatter import render_summary
class Reports(unittest.TestCase):
 def test_mixed(self):self.assertEqual(summarize([{"exit_code":0},{"exit_code":2},{"exit_code":-9}]),dict(total=3,passed=1,failed=2))
 def test_empty(self):self.assertEqual(summarize([]),dict(total=0,passed=0,failed=0))
 def test_render(self):self.assertEqual(render_summary([{"exit_code":0}]),"1 runs: 1 passed, 0 failed")
 def test_invalid(self):
  for x in [None,{},[{}],[{"exit_code":True}],[{"exit_code":"0"}]]:
   with self.subTest(x=x),self.assertRaises(ValueError):summarize(x)
 def test_no_mutation(self):
  x=[{"exit_code":1,"extra":[4]}];self.assertEqual(summarize(x),dict(total=1,passed=0,failed=1));self.assertEqual(x,[{"exit_code":1,"extra":[4]}])
'''
visibleB='''import unittest
from outcomes import summarize
from formatter import render_summary
class Cancellation(unittest.TestCase):
 def test_mixed_cancel(self):
  x=[{"exit_code":0},{"exit_code":2},{"exit_code":None,"cancelled":True}]
  self.assertEqual(summarize(x,include_cancelled=True),dict(total=3,passed=1,failed=1,cancelled=1))
  self.assertEqual(render_summary(x,include_cancelled=True),"3 runs: 1 passed, 1 failed, 1 cancelled")
 def test_empty(self):self.assertEqual(summarize([],include_cancelled=True),dict(total=0,passed=0,failed=0,cancelled=0))
 def test_bad_cancel(self):
  for x in [[{"exit_code":0,"cancelled":True}],[{"exit_code":None}],[{"exit_code":0,"cancelled":1}]]:
   with self.subTest(x=x),self.assertRaises(ValueError):summarize(x,include_cancelled=True)
'''
independent='''import unittest,random,copy
from outcomes import summarize
from formatter import render_summary
class Independent(unittest.TestCase):
 def test_seeded(self):
  rng=random.Random(20261019)
  for i in range(400):
   codes=[rng.randint(-3,3) for _ in range(rng.randint(0,60))]
   records=[{"exit_code":n,"extra":str(j)} for j,n in enumerate(codes)];original=copy.deepcopy(records)
   passed=codes.count(0);failed=len(codes)-passed
   self.assertEqual(summarize(records),dict(total=len(codes),passed=passed,failed=failed))
   self.assertEqual(render_summary(records),f"{len(codes)} runs: {passed} passed, {failed} failed")
   self.assertEqual(records,original)
'''
independentB=''' def test_cancelled_seeded(self):
  rng=random.Random(20261020)
  for i in range(400):
   records=[];passed=failed=cancelled=0
   for j in range(rng.randint(0,60)):
    if rng.randrange(4)==0:records.append({"exit_code":None,"cancelled":True});cancelled+=1
    else:
     code=rng.randint(-3,3);records.append({"exit_code":code,"cancelled":False});passed+=code==0;failed+=code!=0
   original=copy.deepcopy(records);n=len(records)
   self.assertEqual(summarize(records,include_cancelled=True),dict(total=n,passed=passed,failed=failed,cancelled=cancelled))
   self.assertEqual(render_summary(records,include_cancelled=True),f"{n} runs: {passed} passed, {failed} failed, {cancelled} cancelled")
   self.assertEqual(records,original)
'''
refs=d/'reference-source';refs.mkdir();facts=refs/'requirements.txt';facts.write_text('Project run-reporting library. Detailed requirements are pending review.\n')
pack=build_pack(root=refs,facts=['requirements.txt'],output=d/'packs',as_of='2026-10-19T00:00:00Z');write('original-pack.json',pack)
project=d/'project-A';project.mkdir();(project/'tests').mkdir()
(project/'outcomes.py').write_text('def summarize(records):\n    return {"total":len(records),"passed":len(records),"failed":0}\n')
(project/'formatter.py').write_text('from outcomes import summarize\n\ndef render_summary(records):\n    return str(summarize(records))\n')
(project/'tests/test_reports.py').write_text(visibleA);(project/'tests/__init__.py').write_text('')
def audit(label,source):
 state=d/('state-'+label);workspace=state/'world/workspace'
 original=json.loads((d/(label+'-source-before.json')).read_text());assert hashes(source)==original
 current=hashes(workspace);assert set(current)==set(original)
 changed=sorted(k for k in current if current[k]!=original[k]);assert changed and set(changed)<= {'outcomes.py','formatter.py'}
 target=d/(label+'-independent-source');shutil.copytree(workspace,target,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
 (target/'tests/test_independent.py').write_text(independent+(independentB if label=='B' else ''))
 e=Executor.create(target,d/(label+'-independent-world'));r=e.run_tests('independent-'+label,Grant((),True),timeout=30)
 (d/(label+'-independent.stdout')).write_bytes(r.stdout.read_bytes());(d/(label+'-independent.stderr')).write_bytes(r.stderr.read_bytes())
 assert r.exit_code==0,(label,r.stderr.read_bytes()[-4000:])
 write(label+'-audit.json',dict(status='PASS',changed=changed,protected_tests_unchanged=True,source_unchanged=True,heldout_sequences=800 if label=='B' else 400,scope='Independent read-only OS sandbox; model never saw these checks.'))
def run(label,source,oldpack):
 write(label+'-source-before.json',hashes(source))
 args=['code',source,'--task','Implement the current version of the run-reporting requirements in the pinned reference material. Read the actual files, preserve existing behavior where required, change only outcomes.py and formatter.py, and run python3 -m unittest discover -s tests -v. Finish only with actual successful command evidence.','--connection',d/'connection.json','--state',d/('state-'+label),'--branch','dev24-reports-'+label,'--read','outcomes.py','--read','formatter.py','--read-dir','tests','--edit','outcomes.py','--edit','formatter.py','--test-command','python3 -m unittest discover -s tests -v','--context-pack',oldpack['pack_path'],'--context-pack-id',oldpack['pack_id'],'--refresh-context-pack','--max-steps','1024']
 result=cli(label,args);assert result['verified'] is True
 audit(label,source)
 cli(label+'-status',['status',d/('state-'+label),'--json'],timeout=30)
 cli(label+'-review',['review',d/('state-'+label),'--json'],timeout=30)
 return json.loads((d/('state-'+label)/'coding-launch.json').read_text())['launch']['config']['context_pack']
try:
 facts.write_text(specA);pinA=run('A',project,pack);write('A-admitted-pack.json',pinA)
 export=cli('A-export',['export',d/'state-A',d/'A-export.zip'],timeout=30);write('export-fields.json',export)
 # Explicit exact export, never direct mutation of the original checkout.
 digest=hashlib.sha256((d/'A-export.zip').read_bytes()).hexdigest()
 nextproject=d/'project-B'
 cli('A-apply',['apply',d/'A-export.zip','--source',project,'--destination',nextproject,'--sha256',digest,'--operation-id','dev24-report-A-apply'],timeout=30)
 (nextproject/'tests/test_cancelled.py').write_text(visibleB)
 facts.write_text(specB);pinB=run('B',nextproject,dict(pack_path=pinA['path'],pack_id=pinA['pack_id']));write('B-admitted-pack.json',pinB)
 assert pinA['pack_id']!=pinB['pack_id']
 # Completed first task reopens with its old immutable launch, despite newer references.
 before=hashes(d/'state-A')
 cli('A-offline-ready-reopen',['resume',d/'state-A','--max-steps','1024'],timeout=30)
 assert hashes(d/'state-A')==before
 write('campaign-result.json',dict(status='BOUNDED_Q8_TWO_TASK_REFRESH_PASS',sampler='greedy',thinking_default=4096,parent_interventions_during_model_loops=0,old_pack=pack['pack_id'],A_pack=pinA['pack_id'],B_pack=pinB['pack_id'],numerical_oracle='NOT_RUN',limits='Two bounded library tasks; not broad coding or full gate qualification.'))
 print((d/'campaign-result.json').read_text(),flush=True)
except BaseException as exc:
 write('campaign-result.json',dict(status='FAIL',error=dict(type=type(exc).__name__,message=str(exc))));raise
