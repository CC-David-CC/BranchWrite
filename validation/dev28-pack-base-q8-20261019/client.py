from pathlib import Path
import ast,hashlib,json,os,subprocess,socket,time,sys,shutil,signal
D=Path(__file__).parent;ROOT=D.parent
PY='/home/dflanag3/spatial-artifacts/branchwrite-dev28-package-20261019-v1/installed-check/venv/bin/python'
def write(n,v):(D/n).write_text(json.dumps(v,indent=2)+'\n')
c=json.loads((D/'credentials.json').read_text());access=D/'access'
with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
forward=['ssh','-N','-o','BatchMode=yes','-o','ExitOnForwardFailure=yes','-o','IdentitiesOnly=yes','-o','StrictHostKeyChecking=yes','-o','HostKeyAlias=bw-llm60','-o','UserKnownHostsFile='+str(access/'known_hosts'),'-i',str(access/'id_ed25519'),'-L',f'127.0.0.1:{port}:127.0.0.1:{c["port"]}','dflanag3@llm-60']
with (D/'ssh.stderr').open('xb') as e:tunnel=subprocess.Popen(forward,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=e,start_new_session=True)
(D/'tunnel.pid').write_text(str(tunnel.pid))
try:
 deadline=time.monotonic()+20
 while True:
  if tunnel.poll() is not None:raise RuntimeError('tunnel exited')
  try:
   with socket.create_connection(('127.0.0.1',port),timeout=1):break
  except OSError:
   if time.monotonic()>deadline:raise TimeoutError('tunnel startup')
   time.sleep(.1)
 write('connection.json',dict(endpoint_url=f'http://127.0.0.1:{port}',endpoint_pin='ssh-owned-llm60-pack-base',model_contract_id=c['model_contract_id'],execution_profile_id=c['execution_profile_id'],eos_tokens=c['eos_tokens']))
 tree=ast.parse((ROOT/'choice-client-driver-dev21.py').read_text());guard=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='HOST_GUARD' for x in n.targets))
 g=D/'guard';g.mkdir();(g/'sitecustomize.py').write_text(guard+'\nBW_AUDIT_ACTIVE=True\n')
 env=dict(PATH='/usr/bin:/bin',HOME='/tmp',LANG='C.UTF-8',PYTHONPATH=str(g),PYTHONDONTWRITEBYTECODE='1',BW_COW_API_KEY=c['api_key'])
 entry="import sitecustomize,runpy;assert sitecustomize.BW_AUDIT_ACTIVE;runpy.run_module('branchwrite',run_name='__main__')"
 def run(label,argv):
  env['BW_CLIENT_PROOF']=str(D/(label+'-admission.json'));started=time.monotonic()
  with (D/(label+'.stdout')).open('xb') as o,(D/(label+'.stderr')).open('xb') as e:child=subprocess.Popen([PY,'-B','-c',entry,*argv],cwd=D,env=env,stdout=o,stderr=e,stdin=subprocess.DEVNULL,start_new_session=True)
  (D/(label+'.pid')).write_text(str(child.pid));last=started
  while child.poll() is None:
   if time.monotonic()-started>1800:
    os.killpg(child.pid,signal.SIGTERM);child.wait(10);raise TimeoutError('bounded client phase')
   if time.monotonic()-last>=30:print(json.dumps(dict(phase=label,pid=child.pid,elapsed=time.monotonic()-started)),flush=True);last=time.monotonic()
   time.sleep(.2)
  result=dict(exit=child.returncode,seconds=time.monotonic()-started);write(label+'-result.json',result)
  assert child.returncode==0,(label,child.returncode,(D/(label+'.stderr')).read_text()[-2000:])
  proof=json.loads((D/(label+'-admission.json')).read_text());assert not proof['native_modules_loaded'] and not proof['violations']
  return json.loads((D/(label+'.stdout')).read_text())
 def wait_for(name):
  deadline=time.monotonic()+600;last=0
  while not (D/name).exists():
   if time.monotonic()>deadline:raise TimeoutError('measurement handshake '+name)
   if time.monotonic()-last>=30:print(json.dumps(dict(phase='waiting-for-measurement',marker=name)),flush=True);last=time.monotonic()
   time.sleep(.2)
 project=D/'project'
 for q in [project/'__pycache__',project/'tests/__pycache__']:
  if q.exists():shutil.rmtree(q)
 from branchwrite.context_pack import build_pack
 pack=build_pack(root=project,examples=['reference/tooling.txt'],facts=['PROJECT.md','intervals.py'],output=D/'packs',as_of='2026-10-19T00:00:00Z');write('pack.json',pack)
 revision=(D/'source-revision').read_text().strip()
 prepare=['prepare-base','--connection',str(D/'connection.json'),'--state',str(D/'base-state'),'--branch','dev28-project-reference','--purpose','Support BranchWrite coding with the approved source and tool examples. Use one legal tool action at a time. Inspect files and run the actual requested checks. Do not invent observations or exit codes. Permissions and execution belong to the host.','--context-pack',pack['pack_path'],'--context-pack-id',pack['pack_id'],'--source-revision',revision,'--capacity','262144','--operation-id','dev28-reference-prepare']
 prepared=run('prepare',prepare);write('prepare-boundary.json',prepared);wait_for('ALLOW_REPEAT')
 repeated=run('repeat',prepare);assert repeated['snapshot']==prepared['snapshot'];write('repeat-boundary.json',repeated);wait_for('ALLOW_CODE')
 before={str(p.relative_to(project)):hashlib.sha256(p.read_bytes()).hexdigest() for p in project.rglob('*') if p.is_file() and '.git' not in p.parts};write('source-before.json',before)
 task='Repair merge_intervals according to PROJECT.md. Read intervals.py and tests/test_intervals.py. It must accept any finite iterable of closed integer interval pairs, return sorted tuples merging overlaps and shared endpoints, preserve the input and reject reversed bounds. Keep the tests and other project files unchanged. Run python3 -m unittest discover -s tests -v and finish only after actual success.'
 report=run('code',['code',str(project),'--connection',str(D/'connection.json'),'--state',str(D/'code-state'),'--branch','dev28-interval-repair','--task',task,'--project-bases',str(D/'base-state/base-catalog.json'),'--auto-base','--base-revision',revision,'--base-reserve-tokens','32768','--read','PROJECT.md','--read','intervals.py','--read','tests/test_intervals.py','--read','tests/__init__.py','--edit','intervals.py','--test-command','python3 -m unittest discover -s tests -v','--sampler','greedy','--max-steps','1024'])
 assert report['verified'] is True
 after={str(p.relative_to(project)):hashlib.sha256(p.read_bytes()).hexdigest() for p in project.rglob('*') if p.is_file() and '.git' not in p.parts};assert after==before
 write('result.json',dict(status='BOUNDED_CLI_VERIFIED',prepared=prepared,original_project_unchanged=True,independent_oracle='PENDING',numerical_oracle='NOT_RUN'))
except BaseException as exc:
 write('failure.json',dict(type=type(exc).__name__,message=str(exc)));raise
finally:
 tunnel.terminate();tunnel.wait(10)
 (D/'credentials.json').unlink(missing_ok=True)
 write('client-cleanup.json',dict(tunnel_exit=tunnel.returncode,credentials_removed=True))
