import dataclasses,hashlib,importlib.metadata,json,os,shlex,subprocess,time,uuid
from pathlib import Path
from branchwrite.remote_execution import RemoteTarget,RemoteTransport,RemoteIndeterminate
out=Path(__file__).parent;root=Path('/home/dflanag3/.local/share/bw-vm/admin01');nonce=uuid.uuid4().hex[:12];rows=[];started=time.monotonic()
target=RemoteTarget('admin01','127.0.0.1',22220,'maint',root/'guest-key',root/'known_hosts-a432129ef6d1',30)
t=RemoteTransport(out/('jobs-'+nonce),target)
def record(name,result,**extra):
 rows.append(dict(id=name,status='PASS',**extra,**({} if result is None else dict(operation_id=result.operation_id,disposition=result.disposition,exit_code=result.exit_code,elapsed_seconds=result.elapsed_seconds,receipt_sha256=result.receipt_sha256))))
 (out/'remote-live-result.json').write_text(json.dumps(dict(status='RUNNING',rows=rows,nonce=nonce),indent=2)+'\n')
def execute(label,command,*,transport=t):
 return transport.run('ra-'+nonce+'-'+label,hashlib.sha256(command.encode()).hexdigest(),command)
try:
 a=execute('root','findmnt -n -o SOURCE,FSTYPE /; hostname')
 assert a.exit_code==0 and b'/dev/vda2 ext4' in a.stdout and b'branchwrite-admin01' in a.stdout;record('RA-L01-owned-disk-root',a)
 command='printf \'%s\\n\' '+shlex.quote('spaces "quotes" $HOME caf\u00e9 \u96ea')+'; printf \'deliberate failure\\n\' >&2; exit 23'
 a=execute('text',command);assert a.exit_code==23 and a.stdout=='spaces "quotes" $HOME caf\u00e9 \u96ea\n'.encode() and a.stderr==b'deliberate failure\n';record('RA-L02-literals-unicode-status',a)
 a=execute('exit255','exit 255');assert a.exit_code==255 and a.disposition=='exited';record('RA-L03-remote-exit255-is-not-SSH-loss',a)
 a=execute('binary','python3 -c '+shlex.quote('import sys; sys.stdout.buffer.write(bytes(range(256))*16)'))
 assert a.exit_code==0 and a.stdout==bytes(range(256))*16;record('RA-L04-exact-binary',a,bytes=len(a.stdout),sha256=hashlib.sha256(a.stdout).hexdigest())
 marker='/home/maint/.local/share/bw-remote-'+nonce
 code='from pathlib import Path; p=Path('+repr(marker)+'); p.parent.mkdir(parents=True,exist_ok=True); f=p.open("a"); f.write("once\\n"); f.close(); print("done")'
 command='python3 -c '+shlex.quote(code);op='ra-'+nonce+'-once';plan=hashlib.sha256(command.encode()).hexdigest()
 first=t.run(op,plan,command);assert first.exit_code==0
 reopened=RemoteTransport(t.root,target);second=reopened.run(op,plan,command);assert first==second
 check=execute('verify-once','cat '+shlex.quote(marker));assert check.stdout==b'once\n',check.stdout
 record('RA-L05-completed-receipt-reopen-no-reexecution',second,marker_count=1)
 command='touch '+shlex.quote(marker+'-must-not-exist');intent=t.intent('ra-'+nonce+'-unknown','a'*64,command);t.record_intent(intent)
 try:t.run(intent['operation_id'],'a'*64,command)
 except RemoteIndeterminate:pass
 else:raise AssertionError('unacknowledged intent was resent')
 a=execute('verify-unknown','test ! -e '+shlex.quote(marker+'-must-not-exist'));assert a.exit_code==0;record('RA-L06-unknown-intent-not-resent',a)
 short=RemoteTransport(out/('short-'+nonce),dataclasses.replace(target,timeout=.1))
 a=execute('timeout','sleep 2',transport=short);assert a.disposition=='timeout' and a.exit_code!=0;record('RA-L07-remote-deadline',a)
 a=execute('output','python3 -c '+shlex.quote('print("x"*2000000)'));assert a.disposition=='output_limit' and len(a.stdout)<=1024*1024;record('RA-L08-bounded-output',a,bytes=len(a.stdout))
 (out/'persistent-marker.json').write_text(json.dumps(dict(path=marker,sha256=hashlib.sha256(b'once\n').hexdigest(),nonce=nonce),indent=2)+'\n')
 result=dict(status='PASS',scope='installed transport candidate over real pinned SSH to owned persistent QEMU VM; no model/tool-registry/CLI dispatch claim',installed_version=importlib.metadata.version('branchwrite'),client_host=os.uname().nodename,target_identity=target.identity,rows=rows,seconds=time.monotonic()-started,limitations=['not model-facing yet','abrupt client death before receipt publication remains indeterminate; no automatic resend','VM-wide admin scope intentionally permits services to survive commands'])
except BaseException as error:
 import traceback
 result=dict(status='FAIL',error=repr(error),traceback=traceback.format_exc(),rows=rows);raise
finally:(out/'remote-live-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='rows'}))
