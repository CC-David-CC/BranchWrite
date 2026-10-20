import json,uuid,hashlib,time
from pathlib import Path
from branchwrite.remote_execution import RemoteTransport,RemoteTarget
r=Path(__file__).parent;vm=Path('/home/dflanag3/.local/share/bw-vm/admin01');rows=[]
for label,command,timeout,expected in [('output-limit',"python3 -c \"import os; os.write(1,b'x'*(4*1024*1024))\"",5,'output_limit'),('timeout',"python3 -c \"import os,time; os.write(1,b'started'); time.sleep(10)\"",.2,'timeout')]:
 target=RemoteTarget('admin01','127.0.0.1',22220,'maint',vm/'guest-key',vm/'known_hosts-a432129ef6d1',timeout)
 transport=RemoteTransport(r/('bounds-'+label+'-'+uuid.uuid4().hex[:8]),target)
 start=time.monotonic();result=transport.run('probe',hashlib.sha256(command.encode()).hexdigest(),command)
 assert result.disposition==expected,(label,result.disposition)
 assert len(result.stdout)<=1048576 and len(result.stderr)<=1048576
 if label=='output-limit':assert len(result.stdout)==1048576
 else:assert result.stdout==b'started'
 rows.append(dict(id=label,status='PASS',disposition=result.disposition,exit_code=result.exit_code,stdout_bytes=len(result.stdout),stderr_bytes=len(result.stderr),seconds=time.monotonic()-start))
(r/'bounds-result.json').write_text(json.dumps(dict(status='PASS',rows=rows,scope='real SSH; unprivileged same-UID processes only'),indent=2)+'\n');print(json.dumps(rows))
