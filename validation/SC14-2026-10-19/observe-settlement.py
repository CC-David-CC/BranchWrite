"""Post-settlement independent observer; never supplies a model action."""
from pathlib import Path
import os,json,time,subprocess
b=Path(__file__).parent
py='/home/dflanag3/spatial-artifacts/branchwrite-dev15-package-20261019-v1/venv/bin/python'
start=time.monotonic()
result=dict(status='WAITING_FOR_PRODUCER',pid=os.getpid(),audits=[])
def save():
 result['elapsed_seconds']=time.monotonic()-start
 p=b/'settled-audit-result.partial';p.write_text(json.dumps(result,indent=2))
 p.replace(b/'settled-audit-result.json')
try:
 fd=os.open(b/'audit-observer.lock',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 os.close(fd);save()
 while not (b/'command.exit').exists():
  if time.monotonic()-start>2100:raise TimeoutError('producer observation deadline')
  time.sleep(5);save()
 code=int((b/'command.exit').read_text())
 info=json.loads((b/'output/result.json').read_text())
 child=info.get('positive',{}).get('pid',info.get('client_pid'))
 if child and Path('/proc',str(child)).exists():raise RuntimeError('producer handle still present')
 result.update(producer_exit=code,producer_pid=child,producer_absent=True,status='AUDITING');save()
 if code!=0:raise RuntimeError('producer did not complete successfully; retain original failure')
 for name in ['audit-output-with-supplemental.py','audit-ledger.py']:
  with (b/(name+'.stdout')).open('x') as out,(b/(name+'.stderr')).open('x') as err:
   p=subprocess.run([py,'-B',str(b/name)],cwd=b,stdin=subprocess.DEVNULL,stdout=out,stderr=err,timeout=120)
  result['audits'].append(dict(script=name,exit_code=p.returncode));save()
 result['status']='PASS' if all(x['exit_code']==0 for x in result['audits']) else 'FAIL'
except BaseException as exc:
 result.update(status='FAIL',error=dict(type=type(exc).__name__,message=str(exc)))
finally:save()
raise SystemExit(result['status']!='PASS')
