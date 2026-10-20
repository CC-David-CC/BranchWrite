import fcntl,hashlib,json,os,pty,select,struct,subprocess,termios,time,traceback
from pathlib import Path
from branchwrite.records import RuntimeLog
from branchwrite.kernel import FrameKernel
from branchwrite.session_ledger import SessionLedger
out=Path(__file__).parent
project=Path('/home/dflanag3/projects/bw-stop-resume-project-20261020')
project.mkdir(exist_ok=True);state=out/'session'
exe='/home/dflanag3/spatial-artifacts/branchwrite-dev43-pause-20261020/venv/bin/branchwrite'
env=os.environ.copy();env.pop('PYTHONPATH',None);env['TERM']='xterm-256color'
env['BW_COW_CONNECTION']=str(out/'connection.json');env['BW_COW_API_KEY']=(out/'operator-test-key.txt').read_text().strip()
goal='Make a pretty, phone-friendly website about dogs, all in index.html with no downloads. Include these two short sentences: Milo plays. Luna runs. Add a Say hello button that shows Hello, David! when clicked.'
steering='One change: make the dog names Milo and Luna bold, and make the verbs plays and runs both italic and underlined. Keep all the other parts of my request.'
r=dict(status='RUNNING',pid=os.getpid(),client_host=os.uname().nodename,goal=goal,steering=steering,server='llm-60:18099')
def save():
 r['updated']=time.time();(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
def audit():
 ledger=SessionLedger(project,state,json.loads((out/'connection.json').read_text()))
 with RuntimeLog(state/'ledger',read_only=True) as log:
  ledger.log=log;ledger.kernel=FrameKernel(log)
  return dict(history=ledger.history(),current=ledger.current())
def pending_model():
 for p in state.glob('turns/*/cow-operations/*.json'):
  try:record=json.loads(p.read_text())
  except (OSError,ValueError):continue
  if record.get('frame_key') and record.get('path') in ('/cow/text/ask','/cow/text/answer','/cow/text/append-user','/cow/text/resume') and record.get('state')!='complete':
   return dict(operation_id=record['operation_id'],path=record['path'],state=record['state'],journal=str(p))
 return None
def terminal_turn(command,label,stop_first=False):
 master,slave=pty.openpty();fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',36,130,0,0))
 process=subprocess.Popen([exe,'session',str(project),'--state',str(state)],cwd=project,env=env,stdin=slave,stdout=slave,stderr=slave,start_new_session=True);os.close(slave)
 transcript=bytearray();started=time.monotonic();last=started;sent=False;stopped=False;done=False
 try:
  while time.monotonic()-started<1800:
   ready,_,_=select.select([master],[],[],.1)
   if ready:
    try:data=os.read(master,65536)
    except OSError:break
    transcript.extend(data)
    if b'\x1b[6n' in data:os.write(master,b'\x1b[1;1R')
   text=transcript.decode(errors='replace')
   if not sent and 'You>' in text:
    time.sleep(.5);os.write(master,command.encode()+b'\r');sent=True
   if sent and stop_first and not stopped:
    pending=pending_model()
    if pending:
     r['pending_when_stopped']=pending;r['stop_sent_seconds']=time.monotonic()-started
     os.write(master,b'\x1b');stopped=True;save()
   if stop_first and stopped and 'Pause requested; waiting for the original saved model result.' in text and 'Saved at a safe boundary.' in text:
    r['safe_boundary_seconds']=time.monotonic()-started;done=True;os.write(master,b'/exit\r');break
   if not stop_first and 'Chosen checks passed; review the result.' in text:
    done=True;os.write(master,b'/exit\r');break
   if 'Needs recovery:' in text or 'Could not submit:' in text or 'Could not open session:' in text:raise AssertionError('client error '+label)
   if process.poll() is not None:raise RuntimeError('client exited unexpectedly')
   if time.monotonic()-last>30:
    print(json.dumps(dict(phase=label,elapsed=time.monotonic()-started,stopped=stopped,pid=process.pid)),flush=True);last=time.monotonic();save()
  if not done:raise TimeoutError(label)
  process.wait(timeout=60);assert process.returncode==0
  record=audit();(out/(label+'-audit.json')).write_text(json.dumps(record,indent=2)+'\n')
  r[label]=dict(seconds=time.monotonic()-started,pid=process.pid,exit_code=process.returncode);save();return record
 finally:
  if process.poll() is None:
   os.write(master,b'/exit\r')
   try:process.wait(timeout=120)
   except subprocess.TimeoutExpired:r['unsettled_client_pid']=process.pid
  os.close(master)
  assert env['BW_COW_API_KEY'].encode() not in transcript
  (out/(label+'-terminal.txt')).write_bytes(transcript)
try:
 connected=subprocess.run([exe,'connect','http://10.0.7.68:18099'],env=env,capture_output=True,text=True,timeout=20)
 (out/'connect.txt').write_text(connected.stdout+connected.stderr);assert connected.returncode==0
 first=terminal_turn(goal,'stop',True)
 assert len(first['history'])==1 and first['history'][0]['result']['status']=='interrupted'
 original_workflow=first['history'][0]['result']['workflow']
 original_record=Path(r['pending_when_stopped']['journal']);before=original_record.read_bytes();assert json.loads(before)['state']=='complete'
 final=terminal_turn('/continue','continue')
 assert len(final['history'])==2 and final['history'][1]['result']['status']=='finished'
 assert final['history'][1]['result']['workflow']==original_workflow,'continuation replaced original workflow'
 assert original_record.read_bytes()==before,'completed original operation record changed'
 assert len(list((state/'turns').iterdir()))==1,'continue created a replacement model workflow'
 page=Path(final['current']['workdir'])/'index.html';(out/'resumed.html').write_bytes(page.read_bytes())
 r.update(status='PASS',original_workflow=original_workflow,original_operation_record_sha256=hashlib.sha256(before).hexdigest(),html_sha256=hashlib.sha256(page.read_bytes()).hexdigest(),browser='NOT_RUN')
except BaseException as error:r.update(status='FAIL',error=repr(error),traceback=traceback.format_exc());raise
finally:
 r['finished']=time.time();save()
 receipt=out/'client-finished.json';receipt.write_text(json.dumps(dict(status=r['status'],evidence=str(out/'result.json')))+'\n')
 subprocess.run(['scp','-q','-i',str(Path.home()/'.ssh/id_ed25519_codi_fleet'),'-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','HostKeyAlias=llm-60','-o','IdentitiesOnly=yes',str(receipt),'dflanag3@10.0.7.68:/home/dflanag3/spatial-artifacts/bw-stop-resume-live-20261020/client-finished.json'],check=True)
