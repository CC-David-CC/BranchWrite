"""Actual installed interactive CLI; one user prompt, no candidate edits."""
from pathlib import Path
import fcntl,os,pty,select,struct,subprocess,termios,time,json,traceback,hashlib
from branchwrite.session_ledger import SessionLedger
from branchwrite.records import RuntimeLog,Artifact,decode
from branchwrite.kernel import FrameKernel
out=Path(__file__).parent;exe=Path('/home/dflanag3/spatial-artifacts/bw-cli-workflows-dev64-20261020/venv/bin/branchwrite')
project=Path('/home/dflanag3/projects/bw-candidate-admin-dev63-20261020');project.mkdir(mode=0o700,exist_ok=True)
state=out/'session';assert not (state/'ledger').exists(),'never resend an admitted task as a fresh session'
prompt_path=Path('/home/dflanag3/src/branchwrite-documents-20261020/examples/prompts/admin-deploy.txt');prompt=prompt_path.read_text().strip()
env=dict(os.environ,BW_COW_CONNECTION=str(out/'connection.json'),BW_COW_API_KEY=(out/'operator-test-key.txt').read_text().strip(),PYTHONDONTWRITEBYTECODE='1',TERM='xterm-256color',BW_REMOTE_TARGETS=str(out/'operator-targets.json'));env.pop('PYTHONPATH',None)
record=dict(status='RUNNING',controller_pid=os.getpid(),client_host=os.uname().nodename,prompt_sha256=hashlib.sha256(prompt_path.read_bytes()).hexdigest(),task=prompt,operator_candidate_edits=0,scope='installed dev64 interactive session -> candidate780e824a HTTP/Q4; configured owned admin01, exact source/upload/service hashes and HTTP; no operator task revisions')
started=time.monotonic();last=started;transcript=bytearray()
def save():
 record['elapsed_seconds']=time.monotonic()-started;temp=out/'admin-result.tmp';temp.write_text(json.dumps(record,indent=2)+'\n');os.replace(temp,out/'admin-result.json')
save();master=None;process=None
try:
 master,slave=pty.openpty();fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',40,140,0,0))
 process=subprocess.Popen([str(exe),'session',str(project),'--state',str(state)],cwd=project,env=env,stdin=slave,stdout=slave,stderr=slave,start_new_session=True);os.close(slave);record['client_pid']=process.pid;save()
 sent=False;finished=False
 while True:
  ready,_,_=select.select([master],[],[],.1)
  if ready:
   try:data=os.read(master,65536)
   except OSError:break
   transcript.extend(data)
   if b'\x1b[6n' in data:os.write(master,b'\x1b[1;1R')
  text=transcript.decode('utf8','replace')
  if not sent and 'You>' in text:os.write(master,prompt.encode()+b'\r');sent=True;record['submitted_seconds']=time.monotonic()-started;save()
  if 'Needs recovery:' in text or 'Could not open session:' in text:record['status']='NEEDS_RECOVERY';raise RuntimeError('original session needs inspection; no automatic resend')
  if not finished and 'Chosen checks passed; review the result.' in text:
   finished=True;record['completed_seconds']=time.monotonic()-started;os.write(master,b'/exit\r');save()
  if process.poll() is not None:
   if not finished:raise RuntimeError('client exited before completion')
   # Drain the complete PTY, including the actual saved export paths.
   while select.select([master],[],[],.1)[0]:
    try:transcript.extend(os.read(master,65536))
    except OSError:break
   break
  if time.monotonic()-last>=30:
   (out/'admin-terminal.txt').write_bytes(transcript);save();print(json.dumps(dict(phase='interactive-admin',elapsed=record['elapsed_seconds'],client_pid=process.pid)),flush=True);last=time.monotonic()
  if time.monotonic()-started>1200 and not finished:record['status']='OBSERVATION_DEADLINE_CLIENT_LIVE';save() # keep observing the same handle
 process.wait(timeout=60);assert process.returncode==0;record['client_exit_code']=process.returncode
 connection=json.loads((out/'connection.json').read_text());ledger=SessionLedger(project,state,connection)
 with RuntimeLog(state/'ledger',read_only=True) as log:
  ledger.log=log;ledger.kernel=FrameKernel(log);history=ledger.history();assert len(history)==1
  result=history[0]['result'];assert result['status']=='finished' and result['checks_passed'] is True
  record['workflow']=result['workflow'];record['file_commit']=result['file_commit'];record['context']=result['context'];record['exports']=result['exports']
  (out/'admin-session-audit.json').write_text(json.dumps(dict(history=history,current=ledger.current()),indent=2)+'\n')
 accepted=out/'accepted';accepted.mkdir(mode=0o700,exist_ok=True)
 assert (project/'index.html').is_file();raw=(project/'index.html').read_bytes();(accepted/'index.html').write_bytes(raw)
 target=json.loads((out/'operator-targets.json').read_text())['targets']['admin01']
 ssh=['ssh','-i',target['identity_file'],'-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+target['known_hosts_file'],'-p',str(target['port']),target['user']+'@'+target['host']]
 command="python3 -c "+__import__('shlex').quote("import pathlib,urllib.request,json,hashlib; p=pathlib.Path('/var/www/html/index.html'); a=p.read_bytes(); b=urllib.request.urlopen('http://127.0.0.1/',timeout=10).read(); print(json.dumps(dict(file_sha256=hashlib.sha256(a).hexdigest(),http_sha256=hashlib.sha256(b).hexdigest(),unrelated_sha256=hashlib.sha256(pathlib.Path('/var/www/html/index.nginx-debian.html').read_bytes()).hexdigest(),bytes=len(a))))")
 checked=subprocess.run(ssh+[command],capture_output=True,text=True,timeout=30);checked.check_returncode();proof=json.loads(checked.stdout)
 assert proof['file_sha256']==hashlib.sha256(raw).hexdigest()==proof['http_sha256'],proof
 assert proof['unrelated_sha256']=='7682b434a69962f7fea2212f684ed8b99d4119297339caf4e2447edf8e7b5662',proof
 record['independent_acceptance']=proof
 record['reachability']='HTTP loopback inside configured owned QEMU admin01; not public LAN/web reachability'
 record.update(status='PASS',project=str(project),session_state=str(state))
except BaseException as error:
 if record['status']=='RUNNING':record['status']='NEEDS_INSPECTION'
 record.update(error=repr(error),traceback=traceback.format_exc());raise
finally:
 (out/'admin-terminal.txt').write_bytes(transcript);save()
 if master is not None:os.close(master)
 print(json.dumps({k:v for k,v in record.items() if k not in ['exports','geometry','task','traceback']}),flush=True)
