import fcntl,hashlib,json,os,pty,select,struct,subprocess,termios,time,traceback
from pathlib import Path
from branchwrite.records import RuntimeLog
from branchwrite.kernel import FrameKernel
from branchwrite.session_ledger import SessionLedger
out=Path(__file__).parent
project=Path('/home/dflanag3/projects/bw-active-format-steering-20261020')
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
master=None;process=None;transcript=bytearray()
try:
 assert not (state/'ledger').exists(),'must be a fresh session'
 connected=subprocess.run([exe,'connect','http://10.0.7.68:18099'],env=env,capture_output=True,text=True,timeout=20)
 (out/'connect.txt').write_text(connected.stdout+connected.stderr);assert connected.returncode==0
 master,slave=pty.openpty();fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',36,130,0,0))
 process=subprocess.Popen([exe,'session',str(project),'--state',str(state)],cwd=project,env=env,stdin=slave,stdout=slave,stderr=slave,start_new_session=True);os.close(slave)
 started=time.monotonic();last=started;sent=False;steered=False;finished=False;pause_seen=False;boundary_seen=False
 while time.monotonic()-started<1800:
  ready,_,_=select.select([master],[],[],.1)
  if ready:
   try:data=os.read(master,65536)
   except OSError:break
   transcript.extend(data)
   if b'\x1b[6n' in data:os.write(master,b'\x1b[1;1R')
  text=transcript.decode(errors='replace')
  if not sent and 'You>' in text:
   time.sleep(.5);os.write(master,goal.encode()+b'\r');sent=True;r['initial_sent_seconds']=time.monotonic()-started;save()
  if sent and not steered:
   pending=pending_model()
   if pending:
    r['pending_when_steered']=pending;r['steering_sent_seconds']=time.monotonic()-started
    os.write(master,steering.encode()+b'\r');steered=True;save()
  if not pause_seen and 'Pause requested; waiting for the original saved model result.' in text:
   pause_seen=True;r['pause_ack_seconds']=time.monotonic()-started;save()
  if not boundary_seen and 'Saved at a safe boundary.' in text:
   boundary_seen=True;r['settled_boundary_seconds']=time.monotonic()-started;save()
  if 'Needs recovery:' in text or 'Could not submit:' in text or 'Could not open session:' in text:raise AssertionError('client failure: inspect terminal.txt')
  if steered and 'Chosen checks passed; review the result.' in text:
   finished=True;time.sleep(.5);os.write(master,b'/exit\r');break
  if process.poll() is not None:raise RuntimeError('client exited unexpectedly')
  if time.monotonic()-last>30:
   print(json.dumps(dict(phase='active-steering',elapsed=time.monotonic()-started,steered=steered,pause_ack=pause_seen,safe_boundary=boundary_seen,pid=process.pid)),flush=True);last=time.monotonic();save()
 if not finished:raise TimeoutError('active steering deadline')
 process.wait(timeout=60);assert process.returncode==0
 record=audit();(out/'audit.json').write_text(json.dumps(record,indent=2)+'\n')
 assert len(record['history'])==2,[(v['input'],v['result']) for v in record['history']]
 first,second=record['history']
 assert first['result']['status']=='interrupted',first['result']
 assert second['result']['status']=='finished',second['result']
 assert pause_seen and boundary_seen,'actual pause acknowledgment and safe boundary are required'
 page=Path(record['current']['workdir'])/'index.html';assert page.is_file()
 (out/'steered.html').write_bytes(page.read_bytes())
 r.update(status='PASS',seconds=time.monotonic()-started,pause_ack=pause_seen,safe_boundary=boundary_seen,html_sha256=hashlib.sha256(page.read_bytes()).hexdigest(),turns=[dict(id=v['id'],result=v['result']) for v in record['history']],browser='NOT_RUN')
except BaseException as error:
 r.update(status='FAIL',error=repr(error),traceback=traceback.format_exc());raise
finally:
 if process is not None and process.poll() is None:
  if master is not None:os.write(master,b'/exit\r')
  try:process.wait(timeout=120)
  except subprocess.TimeoutExpired:r['unsettled_client_pid']=process.pid
 if master is not None:os.close(master)
 if env['BW_COW_API_KEY'].encode() in transcript:raise AssertionError('key leaked in transcript')
 (out/'terminal.txt').write_bytes(transcript);r['finished']=time.time();save()
 receipt=out/'client-finished.json';receipt.write_text(json.dumps(dict(status=r['status'],evidence=str(out/'result.json')))+'\n')
 subprocess.run(['scp','-q','-i',str(Path.home()/'.ssh/id_ed25519_codi_fleet'),'-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','HostKeyAlias=llm-60','-o','IdentitiesOnly=yes',str(receipt),'dflanag3@10.0.7.68:/home/dflanag3/spatial-artifacts/bw-model-pause-live-20261020/client-finished.json'],check=True)
