import fcntl,hashlib,json,os,pty,select,struct,subprocess,termios,time,traceback
from pathlib import Path
from branchwrite.session_ledger import SessionLedger
from branchwrite.records import RuntimeLog
from branchwrite.kernel import FrameKernel
out=Path(__file__).parent;project=Path('/home/dflanag3/projects/bw-code-deploy-dev51-20261020');project.mkdir(mode=0o700,exist_ok=True);state=out/'session';exe='/home/dflanag3/spatial-artifacts/branchwrite-dev51-upload-private-20261020/venv/bin/branchwrite'
env=os.environ.copy();env.pop('PYTHONPATH',None);env.update(TERM='xterm-256color',BW_COW_CONNECTION=str(out/'connection.json'),BW_COW_API_KEY=(out/'operator-test-key.txt').read_text().strip(),BW_REMOTE_TARGETS=str(out/'operator-targets.json'))
task='Make a pretty, phone-friendly website about dogs in index.html with no downloads. Include the sentences Milo plays. Luna runs. Add a Say hello button that shows Hello, David! when clicked. Keep the file here and put the website on my test machine admin01, replacing its welcome page. Check your work and tell me what I can open.'
r=dict(status='RUNNING',pid=os.getpid(),task=task,client_host=os.uname().nodename,model='real Q4 through COW HTTP on llm-60',operator_guidance='only initial natural-language task; no intervention',scope='autonomous local coding plus exact file upload and remote website publication; independent browser acceptance required')
def save():r['updated']=time.time();(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
transcript=bytearray();master=None;process=None
try:
 assert not (state/'ledger').exists(),'new trial session required'
 f=subprocess.run([exe,'connect','http://10.0.7.68:8099'],env=env,capture_output=True,text=True,timeout=20);(out/'connect.txt').write_text(f.stdout+f.stderr);assert f.returncode==0
 master,slave=pty.openpty();fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',36,160,0,0))
 process=subprocess.Popen([exe,'session',str(project),'--state',str(state)],env=env,cwd=project,stdin=slave,stdout=slave,stderr=slave,start_new_session=True);os.close(slave)
 started=time.monotonic();last=started;sent=False;done=False;seen=set();save()
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
   r.update(elapsed_seconds=time.monotonic()-started,client_pid=process.pid,remote_intents=len(seen));save();print(json.dumps(dict(phase='autonomous-q4-admin',elapsed=r['elapsed_seconds'],remote_intents=len(seen),pid=process.pid)),flush=True);last=time.monotonic()
 if not done:raise TimeoutError('bounded autonomous trial deadline')
 process.wait(timeout=120);assert process.returncode==0
 ledger=SessionLedger(project,state,json.loads((out/'connection.json').read_text()))
 with RuntimeLog(state/'ledger',read_only=True) as log:
  ledger.log=log;ledger.kernel=FrameKernel(log);record=dict(history=ledger.history(),current=ledger.current())
 (out/'session-audit.json').write_text(json.dumps(record,indent=2)+'\n');assert len(record['history'])==1
 outcome=record['history'][0]['result'];assert outcome['status']=='finished' and outcome['checks_passed'] is True
 r.update(status='CLIENT_FLOW_PASS',seconds=time.monotonic()-started,remote_intents=len(seen),outcome=outcome,acceptance='INDEPENDENT CHECKS NOT YET RUN')
except BaseException as error:r.update(status='FAIL',error=repr(error),traceback=traceback.format_exc());raise
finally:
 if process is not None and process.poll() is None:
  if master is not None:os.write(master,b'/stop\r');time.sleep(.3);os.write(master,b'/exit\r')
  try:process.wait(timeout=180)
  except subprocess.TimeoutExpired:r['unsettled_client_pid']=process.pid
 if master is not None:os.close(master)
 assert env['BW_COW_API_KEY'].encode() not in transcript
 r['finished']=time.time();save();(out/'terminal.txt').write_bytes(transcript)
