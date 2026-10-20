import dataclasses,hashlib,json,os,subprocess,sys,time,uuid
from pathlib import Path
from branchwrite.remote_execution import RemoteTarget,RemoteTransport
from branchwrite.remote_ownership import RemoteTargetBusy
out=Path(__file__).parent;root=Path('/home/dflanag3/.local/share/bw-vm/admin01');nonce=uuid.uuid4().hex[:12];rows=[]
target=RemoteTarget('admin01','127.0.0.1',22220,'maint',root/'guest-key',root/'known_hosts-a432129ef6d1',30)
t=RemoteTransport(out/('owner-'+nonce),target);other=RemoteTransport(out/('other-'+nonce),dataclasses.replace(target,name='another-alias',timeout=20))
marker='/home/maint/.local/share/bw-owner-'+nonce
child=out/'ownership_child.py';child.write_text("from pathlib import Path\nimport sys,os,hashlib,json\nfrom branchwrite.remote_execution import RemoteTarget,RemoteTransport\nfrom branchwrite.remote_ownership import _Reservation\nr=Path('/home/dflanag3/.local/share/bw-vm/admin01')\nt=RemoteTransport(Path(sys.argv[1]),RemoteTarget('admin01','127.0.0.1',22220,'maint',r/'guest-key',r/'known_hosts-a432129ef6d1',30))\nif sys.argv[4]=='crash':_Reservation.complete=lambda *args:os._exit(73)\na=t.run(sys.argv[2],hashlib.sha256(sys.argv[3].encode()).hexdigest(),sys.argv[3])\nprint(json.dumps(dict(status='PASS',exit_code=a.exit_code)))\n")
def launch(op,command,mode):
 return subprocess.Popen([sys.executable,str(child),str(t.root),op,command,mode],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
try:
 command='sleep 1; printf \'once\\n\' >> '+marker;op='owner-'+nonce;process=launch(op,command,'normal');end=time.monotonic()+5
 while not t._ownership().marker.exists():
  assert process.poll() is None,'holder exited before observation'
  if time.monotonic()>end:raise TimeoutError('holder never reserved endpoint')
  time.sleep(.01)
 assert process.poll() is None
 refused='forbidden-'+nonce
 try:other.run(refused,'a'*64,'touch '+marker+'-bad')
 except RemoteTargetBusy:pass
 else:raise AssertionError('second client bypassed active remote owner')
 assert not (other.root/refused/'intent.json').exists(),'refused operation recorded as a dispatched remote command'
 stdout,stderr=process.communicate(timeout=10);assert process.returncode==0,stderr
 check=other.run('verify-'+nonce,'b'*64,'test ! -e '+marker+'-bad; cat '+marker);assert check.stdout==b'once\n' and check.exit_code==0
 rows.append(dict(id='RMO-L01-two-process-no-overlap',status='PASS',holder_pid=process.pid,other_alias=other.target.name,no_second_intent=True))
 command='printf \'crash-once\\n\' >> '+marker;op='crash-'+nonce;process=launch(op,command,'crash');stdout,stderr=process.communicate(timeout=10)
 assert process.returncode==73,stderr
 assert t._ownership().marker.exists(),'crash lost durable ownership'
 assert (t.root/op/'receipt.json').exists(),'injection must happen AFTER observed SSH receipt publication'
 after=other.run('after-'+nonce,'c'*64,'cat '+marker);assert after.exit_code==0 and after.stdout==b'once\ncrash-once\n'
 assert not t._ownership().marker.exists(),'validated old receipt did not release resource'
 old=t.read_receipt(op,hashlib.sha256(command.encode()).hexdigest(),command);assert old.exit_code==0
 again=t.run(op,hashlib.sha256(command.encode()).hexdigest(),command);assert old==again
 check=other.run('final-'+nonce,'d'*64,'cat '+marker);assert check.stdout==b'once\ncrash-once\n'
 rows.append(dict(id='RMO-L02-client-crash-after-ACK-recovers-known-receipt',status='PASS',client_exit=73,no_command_reexecution=True,original_operation_id=op,original_receipt_sha256=old.receipt_sha256))
 report=dict(status='PASS',rows=rows,scope='real installed transport, two host client processes and SSH to owned persistent VM; not cross-host locking or unknown-ACK recovery',nonce=nonce,resource_identity=target.resource_identity)
except BaseException as error:
 import traceback
 report=dict(status='FAIL',rows=rows,error=repr(error),traceback=traceback.format_exc());raise
finally:(out/'ownership-live-result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
