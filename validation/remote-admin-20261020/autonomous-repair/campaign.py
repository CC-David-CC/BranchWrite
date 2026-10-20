import fcntl,hashlib,json,os,pty,select,struct,subprocess,termios,time,traceback
from pathlib import Path
from branchwrite.session_ledger import SessionLedger
from branchwrite.records import RuntimeLog
from branchwrite.kernel import FrameKernel
out=Path(__file__).parent;project=Path('/home/dflanag3/projects/bw-autorepair-dev54-20261020');project.mkdir(mode=0o700,exist_ok=True);state=out/'session';exe='/home/dflanag3/spatial-artifacts/branchwrite-dev54-verification-feedback-20261020/venv/bin/branchwrite'
env=os.environ.copy();env.pop('PYTHONPATH',None);env.update(TERM='xterm-256color',BW_COW_CONNECTION=str(out/'connection.json'),BW_COW_API_KEY=(out/'operator-test-key.txt').read_text().strip())
task='This tiny shopping calculator gives wrong totals. First run its existing unit tests to see what is wrong, then fix calculator.py and rerun the tests. Keep the existing tests unchanged. Explain the failure and what you fixed.'
r=dict(status='RUNNING',pid=os.getpid(),task=task,client_host=os.uname().nodename,model='real Q4 through COW HTTP on llm-60',operator_guidance='only initial natural-language task; no intervention',scope='fresh installed dev54 CLI autonomous repair, real Q4 COW HTTP, unchanged existing unit tests')
def save():r['updated']=time.time();(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
transcript=bytearray();master=None;process=None
try:
 assert not (state/'ledger').exists(),'must begin a fresh session'
 f=subprocess.run([exe,'connect','http://10.0.7.68:8099'],env=env,capture_output=True,text=True,timeout=20);(out/'connect.txt').write_text(f.stdout+f.stderr);assert f.returncode==0
 master,slave=pty.openpty();fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',36,160,0,0))
 process=subprocess.Popen([exe,'session',str(project),'--state',str(state),'--sampler','greedy'],env=env,cwd=project,stdin=slave,stdout=slave,stderr=slave,start_new_session=True);os.close(slave)
 started=time.monotonic();last=started;sent=False;done=False;seen={str(p) for p in state.glob('turns/*/world/remote-operations/*/*/intent.json')};before_count=len(seen);save()
 while time.monotonic()-started<1200:
  ready,_,_=select.select([master],[],[],.1)
  if ready:
   try:data=os.read(master,65536)
   except OSError:break
   transcript.extend(data)
   if b'\x1b[6n' in data:os.write(master,b'\x1b[1;1R')
   (out/'terminal.txt').write_bytes(transcript)
  text=transcript.decode(errors='replace')
  if not sent and 'You>' in text:time.sleep(.4);os.write(master,task.encode()+b'\r');sent=True
  for path in state.glob('turns/*/world/remote-operations/*/*/intent.json'):
   if str(path) not in seen:
    try:item=json.loads(path.read_text())
    except (OSError,ValueError):continue
    seen.add(str(path));print(json.dumps(dict(event='observed-remote-intent',operation_id=item['operation_id'],command=('host byte upload' if item.get('schema')==2 else item['command']))),flush=True)
  if any(marker in text for marker in ('Needs recovery:','Could not submit:','Could not open session:')):raise RuntimeError('client needs recovery; preserve original operations')
  if 'Chosen checks passed; review the result.' in text:
   done=True;os.write(master,b'/exit\r');break
  if 'The turn ended; its checks have not established success.' in text or 'Saved at a safe boundary.' in text:raise AssertionError('autonomous task did not finish verified')
  if process.poll() is not None:raise RuntimeError('client exited before final result')
  if time.monotonic()-last>30:
   r.update(elapsed_seconds=time.monotonic()-started,client_pid=process.pid,remote_intents=len(seen)-before_count);save();print(json.dumps(dict(phase='autonomous-q4-admin',elapsed=r['elapsed_seconds'],remote_intents=len(seen)-before_count,pid=process.pid)),flush=True);last=time.monotonic()
 if not done:raise TimeoutError('bounded autonomous trial deadline')
 process.wait(timeout=120);assert process.returncode==0
 ledger=SessionLedger(project,state,json.loads((out/'connection.json').read_text()))
 with RuntimeLog(state/'ledger',read_only=True) as log:
  ledger.log=log;ledger.kernel=FrameKernel(log);record=dict(history=ledger.history(),current=ledger.current())
 (out/'session-audit.json').write_text(json.dumps(record,indent=2)+'\n');assert len(record['history'])==1;assert record['history'][-1]['input']['message']==task
 outcome=record['history'][-1]['result'];assert outcome['status']=='finished' and outcome['checks_passed'] is True
 r.update(status='CLIENT_FLOW_PASS',seconds=time.monotonic()-started,remote_intents=len(seen)-before_count,outcome=outcome,acceptance='INDEPENDENT CHECKS NOT YET RUN')
except BaseException as error:r.update(status='FAIL',error=repr(error),traceback=traceback.format_exc());raise
finally:
 if process is not None and process.poll() is None:
  if master is not None:os.write(master,b'/stop\r');time.sleep(.3);os.write(master,b'/exit\r')
  retirement=time.monotonic()+180
  while process.poll() is None and time.monotonic()<retirement:
   if select.select([master],[],[],.1)[0]:
    try:transcript.extend(os.read(master,65536))
    except OSError:break
  if process.poll() is None:r['unsettled_client_pid']=process.pid
 if master is not None:os.close(master)
 assert env['BW_COW_API_KEY'].encode() not in transcript
 r['finished']=time.time();save();(out/'terminal.txt').write_bytes(transcript)
