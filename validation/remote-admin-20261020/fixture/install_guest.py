import json,os,subprocess,time
from pathlib import Path
out=Path(__file__).parent;r=Path('/home/dflanag3/.local/share/bw-vm/admin01')
a=['ssh','-i',str(r/'guest-key'),'-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+str(r/'known_hosts-a432129ef6d1'),'-p','22220','maint@127.0.0.1','sudo -n bash -s']
started=time.monotonic();report=dict(status='RUNNING',pid=os.getpid(),scope='owned blank 32GiB QEMU guest disk only',started=time.time())
with (out/'guest-install.log').open('w') as log,(out/'guest-install.sh').open('r') as script:
 p=subprocess.Popen(a,stdin=script,stdout=log,stderr=subprocess.STDOUT)
 report['ssh_pid']=p.pid
 while p.poll() is None:
  report['elapsed_seconds']=time.monotonic()-started;(out/'install-result.json').write_text(json.dumps(report,indent=2)+'\n');time.sleep(5)
 report.update(status='PASS' if p.returncode==0 else 'FAIL',exit_code=p.returncode,elapsed_seconds=time.monotonic()-started)
 (out/'install-result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
