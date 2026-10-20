"""Own the client subprocess; audit only after its terminal exit."""
from pathlib import Path
import subprocess,json,time,os
b=Path(__file__).parent;python='/home/dflanag3/spatial-artifacts/branchwrite-dev19-package-20261019-v1/venv/bin/python'
r=dict(status='RUNNING',started_ns=time.time_ns(),scope='frozen SC19 task with explicit Min-P; not new unfamiliar-task quality')
def write():
 p=b/'campaign-result.partial';p.write_text(json.dumps(r,indent=2)+'\n');p.replace(b/'campaign-result.json')
write()
try:
 child=subprocess.Popen([python,'-B',str(b/'run-client.py')]);r['client_supervisor_pid']=child.pid;write()
 code=child.wait();r['client_exit']=code;assert code==0,('client failed',code)
 assert (b/'command.exit').read_text().strip()=='0'
 for name in ['audit-output.py','audit-ledger.py','audit-public-flow.py']:
  with (b/(name+'.stdout')).open('x') as o,(b/(name+'.stderr')).open('x') as e:
   completed=subprocess.run([python,'-I','-B',str(b/name)],stdout=o,stderr=e,timeout=90)
  r[name]=completed.returncode;write();assert completed.returncode==0,('audit failed',name)
 r['status']='BOUNDED_MINP_AUTONOMOUS_CLI_PASS'
except BaseException as exc:r.update(status='FAIL',error=dict(type=type(exc).__name__,message=str(exc)))
finally:
 r['finished_ns']=time.time_ns();write()
 (b/'campaign.exit').write_text('0' if r['status']=='BOUNDED_MINP_AUTONOMOUS_CLI_PASS' else '1')
