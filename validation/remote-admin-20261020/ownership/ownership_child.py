from pathlib import Path
import sys,os,hashlib,json
from branchwrite.remote_execution import RemoteTarget,RemoteTransport
from branchwrite.remote_ownership import _Reservation
r=Path('/home/dflanag3/.local/share/bw-vm/admin01')
t=RemoteTransport(Path(sys.argv[1]),RemoteTarget('admin01','127.0.0.1',22220,'maint',r/'guest-key',r/'known_hosts-a432129ef6d1',30))
if sys.argv[4]=='crash':_Reservation.complete=lambda *args:os._exit(73)
a=t.run(sys.argv[2],hashlib.sha256(sys.argv[3].encode()).hexdigest(),sys.argv[3])
print(json.dumps(dict(status='PASS',exit_code=a.exit_code)))
