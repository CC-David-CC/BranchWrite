from pathlib import Path
import ast,hashlib,json,os,subprocess,socket,time,sys,shutil,signal
D=Path(__file__).parent;ROOT=D.parent
PY='/home/dflanag3/spatial-artifacts/branchwrite-dev27-package-20261019-v1/installed-check/venv/bin/python'
def write(n,v):(D/n).write_text(json.dumps(v,indent=2)+'\n')
c=json.loads((D/'credentials.json').read_text());access=D/'access'
with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
args=['ssh','-N','-o','BatchMode=yes','-o','ExitOnForwardFailure=yes','-o','IdentitiesOnly=yes','-o','StrictHostKeyChecking=yes','-o','HostKeyAlias=bw-llm60','-o','UserKnownHostsFile='+str(access/'known_hosts'),'-i',str(access/'id_ed25519'),'-L',f'127.0.0.1:{port}:127.0.0.1:{c["port"]}','dflanag3@llm-60']
with (D/'ssh.stderr').open('xb') as e:tunnel=subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=e,start_new_session=True)
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
 connection=dict(endpoint_url=f'http://127.0.0.1:{port}',endpoint_pin='ssh-pinned-owned-llm60-api',model_contract_id=c['model_contract_id'],execution_profile_id=c['execution_profile_id'],eos_tokens=c['eos_tokens']);write('connection.json',connection)
 tree=ast.parse((ROOT/'choice-client-driver-dev21.py').read_text());guard=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='HOST_GUARD' for x in n.targets))
 g=D/'guard';g.mkdir();(g/'sitecustomize.py').write_text(guard+'\nBW_AUDIT_ACTIVE=True\n')
 env=dict(PATH='/usr/bin:/bin',HOME='/tmp',LANG='C.UTF-8',PYTHONPATH=str(g),PYTHONDONTWRITEBYTECODE='1',BW_COW_API_KEY=c['api_key'])
 entry="import sitecustomize,runpy;assert sitecustomize.BW_AUDIT_ACTIVE;runpy.run_module('branchwrite',run_name='__main__')"
 def run(label,source,task,extra=()):
  env['BW_CLIENT_PROOF']=str(D/(label+'-admission.json'))
  argv=['code',str(source),'--connection',str(D/'connection.json'),'--state',str(D/('state-'+label)),'--branch','dev27-site-'+label,'--task',task,'--read','check_site.py','--read','index.html','--read','style.css','--create','index.html','--create','style.css','--edit','index.html','--edit','style.css','--test-command','python3 check_site.py','--sampler','greedy','--max-steps','1024',*extra]
  started=time.monotonic()
  with (D/(label+'.stdout')).open('xb') as o,(D/(label+'.stderr')).open('xb') as e:child=subprocess.Popen([PY,'-B','-c',entry,*argv],cwd=D,env=env,stdout=o,stderr=e,stdin=subprocess.DEVNULL,start_new_session=True)
  (D/(label+'.pid')).write_text(str(child.pid));last=started
  while child.poll() is None:
   if time.monotonic()-started>1800:
    os.killpg(child.pid,signal.SIGTERM);child.wait(10);raise TimeoutError('bounded client task')
   if time.monotonic()-last>=30:print(json.dumps(dict(task=label,pid=child.pid,elapsed=time.monotonic()-started)),flush=True);last=time.monotonic()
   time.sleep(.2)
  result=dict(exit=child.returncode,seconds=time.monotonic()-started);write(label+'-result.json',result)
  assert child.returncode==0,(label,child.returncode,(D/(label+'.stderr')).read_text()[-2000:])
  report=json.loads((D/(label+'.stdout')).read_text());assert report['verified'] is True
  proof=json.loads((D/(label+'-admission.json')).read_text());assert not proof['native_modules_loaded'] and not proof['violations']
  return report
 source=D/'source-first';source.mkdir();shutil.copy2(Path('/home/dflanag3/src/branchwrite-model-reconciliation-20261019/docs/manual/examples/check_site.py'),source/'check_site.py')
 task='Create a simple attractive static garden club website in index.html and style.css. Include welcome, upcoming activities and contact sections, a descriptive title, semantic HTML and responsive CSS. Link style.css. No remote fonts, external libraries, backend or JavaScript. Read check_site.py and keep it unchanged. Run python3 check_site.py and finish only after actual success.'
 run('first',source,task)
 from branchwrite.cow_client import CowClient,OperationJournal
 client=CowClient.http(connection['endpoint_url'],journal=OperationJournal(D/'catalog-journal'),api_key=c['api_key'],endpoint_pin=connection['endpoint_pin'])
 head=client.head('dev27-site-first');write('base-before.json',head.__dict__)
 source2=D/'source-second';shutil.copytree(D/'state-first/world/workspace',source2)
 # Catalog revision pins the shared BranchWrite tooling prefix, not website freshness.
 revision='29f7bb25d3c9f9d62efde61f7afb3e5708abadfb'
 write('await-root-measurement.json',dict(root=head.root,phase='first-task-complete'))
 deadline=time.monotonic()+600
 while not (D/'root-measurement.json').exists():
  if time.monotonic()>deadline:raise TimeoutError('await authoritative root token measurement')
  time.sleep(.2)
 root_measurement=json.loads((D/'root-measurement.json').read_text());assert root_measurement['consumed']>0
 offer=dict(base_id='1'*64,branch=head.name,snapshot=head.root,source_revision=revision,execution_profile_id=c['execution_profile_id'],prefix_tokens=root_measurement['consumed'],capacity=262144)
 write('catalog.json',[offer]);write('catalog-scope.json',dict(prefix_tokens='Measured first native prefix capture; receipt retained',source_revision='Shared tooling source revision, not website working-tree freshness'))
 before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in source2.iterdir() if p.is_file()};write('source-second-before.json',before)
 run('second',source2,'Read the existing garden club site. Add a clearly labelled Meeting times section with Saturday at 10 AM. Preserve its existing content and responsive layout. Read check_site.py and keep it unchanged. Run python3 check_site.py and finish only after actual success.',['--project-bases',str(D/'catalog.json'),'--auto-base','--base-revision',revision,'--base-reserve-tokens','8192'])
 after=client.head('dev27-site-first');assert after==head
 assert {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in source2.iterdir() if p.is_file()}==before
 write('result.json',dict(status='PASS',scope='Two installed CLI Q8 tasks; second selected exact common tooling prefix automatically; numerical oracle NOT_RUN',first_branch_unchanged=True,second_original_unchanged=True))
except BaseException as exc:
 write('failure.json',dict(type=type(exc).__name__,message=str(exc)));raise
finally:
 tunnel.terminate();tunnel.wait(10)
 (D/'credentials.json').unlink(missing_ok=True)
 write('client-cleanup.json',dict(tunnel_exit=tunnel.returncode,credentials_removed=True))
