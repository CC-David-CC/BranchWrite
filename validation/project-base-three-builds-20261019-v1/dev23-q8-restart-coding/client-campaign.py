from pathlib import Path
import ast,hashlib,json,os,signal,socket,subprocess,sys,time
from branchwrite.context_pack import build_pack
from branchwrite.cow_client import OperationJournal
d=Path(__file__).parent;root=d.parent;phase=sys.argv[1]
creds=json.loads((d/'credentials.json').read_text())
python=str(Path(sys.executable));state=d/'state'
guard=d/'guard'
if phase=='prepare':
 guard.mkdir()
 tree=ast.parse((root/'choice-client-driver-dev21.py').read_text())
 base=next(ast.literal_eval(node.value) for node in tree.body if isinstance(node,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='HOST_GUARD' for x in node.targets))
 fault=r"""
if os.environ.get('BW_ROOT_REPLY_FAULT')=='1':
 from branchwrite.cow_client import HTTPTransport
 original_request=HTTPTransport.request
 def lose_root(self,method,path,body=None,**kw):
  response=original_request(self,method,path,body,**kw)
  if method=='POST' and path=='/cow/text/context':
   events=list(response.events);complete=[e for e in events if e.get('event')=='complete']
   assert len(complete)==1
   Path(os.environ['BW_ROOT_OBSERVED']).write_text(json.dumps(complete[0],indent=2)+'\n')
   done()
   os._exit(92)
  return response
 HTTPTransport.request=lose_root
"""
 guard_source=base+'\nBW_AUDIT_ACTIVE=True\n'+fault
 compile(guard_source,str(guard/'sitecustomize.py'),'exec')
 (guard/'sitecustomize.py').write_text(guard_source)
 with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
 access=root/'client-access'
 forward=['ssh','-N','-o','BatchMode=yes','-o','ExitOnForwardFailure=yes','-o','IdentitiesOnly=yes','-o','StrictHostKeyChecking=yes','-o','HostKeyAlias=bw-llm60','-o','UserKnownHostsFile='+str(access/'known_hosts'),'-i',str(access/'id_ed25519'),'-L','127.0.0.1:'+str(port)+':127.0.0.1:'+str(creds['port']),'dflanag3@llm-60']
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
 endpoint='http://127.0.0.1:'+str(port)
 connection=dict(endpoint_url=endpoint,endpoint_pin='ssh-pinned-owned-llm60-api',model_contract_id=creds['model_contract_id'],execution_profile_id=creds['execution_profile_id'],eos_tokens=creds['eos_tokens'])
 (d/'connection.json').write_text(json.dumps(connection,indent=2)+'\n')
 project=d/'project';project.mkdir();(project/'tests').mkdir()
 (project/'calculator.py').write_text('def add(a, b):\n    return a - b\n')
 (project/'tests/__init__.py').write_text('')
 (project/'tests/test_calculator.py').write_text('import unittest\nfrom calculator import add\nclass CalculatorTests(unittest.TestCase):\n def test_positive(self):self.assertEqual(add(7,4),11)\n def test_negative(self):self.assertEqual(add(-7,4),-3)\n')
 source_hashes={str(p.relative_to(project)):hashlib.sha256(p.read_bytes()).hexdigest() for p in project.rglob('*') if p.is_file()}
 (d/'source-before.json').write_text(json.dumps(source_hashes,indent=2)+'\n')
 refs=d/'reference-source';refs.mkdir()
 (refs/'project.txt').write_text('This owned project has calculator.py and unittest tests under tests/. The host requires actual test receipts. Read current files before editing. This recorded reference is not a tool grant.\n')
 pack=build_pack(root=refs,facts=['project.txt'],output=d/'packs',as_of='2026-10-19T22:00:00Z')
 (d/'pack.json').write_text(json.dumps(pack,indent=2)+'\n')
 argv=[python,'-B','-m','branchwrite','code',str(project),'--task','Inspect calculator.py and its tests. Repair add so it returns the sum for positive and negative inputs. Keep changes limited to calculator.py. Run python3 -m unittest discover -s tests -v and finish only after its actual success.','--connection',str(d/'connection.json'),'--state',str(state),'--branch','dev23-bootstrap-code-v3','--read','calculator.py','--read','tests/test_calculator.py','--edit','calculator.py','--test-command','python3 -m unittest discover -s tests -v','--context-pack',pack['pack_path'],'--context-pack-id',pack['pack_id'],'--max-steps','512']
elif phase=='reconcile':
 argv=[python,'-B','-m','branchwrite','reconcile',str(state),'--operation-id',(d/'operation').read_text()]
elif phase=='resume':
 argv=[python,'-B','-m','branchwrite','resume',str(state),'--max-steps','512']
else:raise ValueError('unknown phase')
entry="import sitecustomize,runpy;assert sitecustomize.BW_AUDIT_ACTIVE is True;runpy.run_module('branchwrite',run_name='__main__')"
argv=[argv[0],'-B','-c',entry,*argv[4:]]
env=dict(PATH='/usr/bin:/bin',HOME='/tmp',LANG='C.UTF-8',PYTHONPATH=str(guard),PYTHONDONTWRITEBYTECODE='1',BW_COW_API_KEY=creds['api_key'],BW_CLIENT_PROOF=str(d/(phase+'-admission.json')))
if phase=='prepare':env.update(BW_ROOT_REPLY_FAULT='1',BW_ROOT_OBSERVED=str(d/'original-root-complete.json'))
started=time.monotonic()
with (d/(phase+'.stdout')).open('xb') as o,(d/(phase+'.stderr')).open('xb') as e:
 child=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=o,stderr=e,env=env,cwd=d,start_new_session=True)
 (d/(phase+'.pid')).write_text(str(child.pid));last=started
 while child.poll() is None:
  elapsed=time.monotonic()-started
  if elapsed>1800:
   os.killpg(child.pid,signal.SIGTERM);child.wait(10);raise TimeoutError('bounded client phase timeout')
  if time.monotonic()-last>=30:
   print(json.dumps(dict(phase=phase,pid=child.pid,elapsed_seconds=elapsed)),flush=True);last=time.monotonic()
  time.sleep(.2)
elapsed=time.monotonic()-started
(d/(phase+'.exit')).write_text(str(child.returncode))
proof=json.loads((d/(phase+'-admission.json')).read_text());assert not proof['native_modules_loaded'] and not proof['violations']
if phase=='prepare':
 assert child.returncode==92,(child.returncode,(d/'prepare.stderr').read_text())
 records=[json.loads(p.read_text()) for p in (state/'cow-operations').glob('*.json')]
 roots=[r for r in records if r['path']=='/cow/text/context'];assert len(roots)==1 and roots[0]['state']=='pending'
 (d/'operation').write_text(roots[0]['operation_id'])
 (d/'root-intent.json').write_text(json.dumps(roots[0],indent=2)+'\n')
 files={str(p.relative_to(state/'ledger')):hashlib.sha256(p.read_bytes()).hexdigest() for p in (state/'ledger').rglob('*') if p.is_file()}
 (d/'ledger-before.json').write_text(json.dumps(files,sort_keys=True))
 (d/'reference-source/project.txt').write_text('Reference source changed after committed root reply was lost. Old admitted root must remain unchanged.\n')
 result=dict(status='ROOT_COMMITTED_CLIENT_PENDING',phase=phase,seconds=elapsed,client_exit=child.returncode,operation=roots[0]['operation_id'])
elif phase=='reconcile':
 assert child.returncode==0,(child.returncode,(d/'reconcile.stderr').read_text())
 result=json.loads((d/'reconcile.stdout').read_text());assert result['scope']=='bootstrap' and not result['workflow_advanced']
 journal=OperationJournal(state/'cow-operations');op=(d/'operation').read_text();saved=journal.read(op);old=json.loads((d/'root-intent.json').read_text())
 assert saved['state']=='complete' and saved['body_b64']==old['body_b64']
 assert saved['receipt']==json.loads((d/'original-root-complete.json').read_text())['receipt']
 files={str(p.relative_to(state/'ledger')):hashlib.sha256(p.read_bytes()).hexdigest() for p in (state/'ledger').rglob('*') if p.is_file()}
 assert files==json.loads((d/'ledger-before.json').read_text())
 result.update(status='BOOTSTRAP_RECONCILIATION_PASS',seconds=elapsed,original_request_and_receipt_exact=True,workflow_ledger_unchanged=True)
else:
 assert child.returncode==0,(child.returncode,(d/'resume.stderr').read_text()[-2000:])
 result=json.loads((d/'resume.stdout').read_text());assert result['verified'] is True
 result.update(status='BOUNDED_AUTONOMOUS_CODING_COMPLETE_PARENT_REVIEW_PENDING',seconds=elapsed,parent_interventions_after_start=0)
(d/(phase+'-result.json')).write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result),flush=True)
