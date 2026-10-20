"""Independent audit coordinator; no model/tool decisions or live ledger reads."""
from pathlib import Path
import subprocess,time,json,os
b=Path(__file__).parent;children=[b/'A',b/'B']
py='/home/dflanag3/spatial-artifacts/branchwrite-dev16-package-20261019-v1/installation/venv/bin/python'
start=time.monotonic();result=dict(status='WAITING_FOR_CLIENTS',pid=os.getpid(),clients={})
def save():
 result['elapsed_seconds']=time.monotonic()-start
 p=b/'result.partial';p.write_text(json.dumps(result,indent=2));p.replace(b/'result.json')
try:
 save()
 while not all((d/'command.exit').exists() for d in children):
  if time.monotonic()-start>2100:raise TimeoutError('owned client observation deadline')
  time.sleep(5);save()
 for d in children:
  info=json.loads((d/'output/result.json').read_text())
  pid=info.get('positive',{}).get('pid',info.get('client_pid'))
  if pid and Path('/proc',str(pid)).exists():raise RuntimeError('client producer still present')
  result['clients'][d.name]=dict(producer_exit=int((d/'command.exit').read_text()),producer_pid=pid,audits=[])
 key=children[0]/'ssh'
 argv=['ssh','-o','BatchMode=yes','-o','IdentitiesOnly=yes','-o','StrictHostKeyChecking=yes','-o','HostKeyAlias=bw-llm60','-o','UserKnownHostsFile='+str(key/'known_hosts'),'-i',str(key/'id_ed25519'),'dflanag3@llm-60','stop-owned-campaign']
 p=subprocess.run(argv,capture_output=True,text=True,timeout=30)
 (b/'automatic-stop.json').write_text(json.dumps(dict(exit_code=p.returncode,stderr=p.stderr)))
 if p.returncode:raise RuntimeError('owned service stop request failed')
 for d in children:
  for name in ['credentials.json','id_ed25519','id_ed25519.pub']:(d/'ssh'/name).unlink(missing_ok=True)
 result['status']='AUDITING';save()
 for d in children:
  entry=result['clients'][d.name]
  if entry['producer_exit']!=0:continue
  for name in ['audit-output.py','audit-ledger.py','audit-policy.py','audit-public-flow.py']:
   with (d/(name+'.stdout')).open('x') as out,(d/(name+'.stderr')).open('x') as err:
    p=subprocess.run([py,'-B',str(d/name)],cwd=d,stdin=subprocess.DEVNULL,stdout=out,stderr=err,timeout=120)
   entry['audits'].append(dict(script=name,exit_code=p.returncode));save()
 result['status']='PASS' if all(v['producer_exit']==0 and len(v['audits'])==4 and all(a['exit_code']==0 for a in v['audits']) for v in result['clients'].values()) else 'FAIL'
except BaseException as exc:
 result.update(status='FAIL',error=dict(type=type(exc).__name__,message=str(exc)))
finally:save()
raise SystemExit(result['status']!='PASS')
