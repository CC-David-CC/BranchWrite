import fcntl,hashlib,json,os,pty,select,struct,subprocess,termios,time,traceback
from pathlib import Path
from branchwrite.records import RuntimeLog
from branchwrite.kernel import FrameKernel
from branchwrite.session_ledger import SessionLedger
out=Path(__file__).parent;project=Path('/home/dflanag3/projects/branchwrite-fast-controls-20261020')
project.mkdir(exist_ok=True);state=out/'session';exe='/home/dflanag3/spatial-artifacts/branchwrite-dev42-interactive-20261020/venv/bin/branchwrite'
env=os.environ.copy();env.pop('PYTHONPATH',None);env['TERM']='xterm-256color';env['BW_COW_CONNECTION']=str(out/'connection.json')
env['BW_COW_API_KEY']=(out/'operator-test-key.txt').read_text().strip()
result=dict(status='RUNNING',pid=os.getpid(),client_host=os.uname().nodename,server='llm-60:18099',turns=[])
def save():
 result['updated']=time.time();(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
def audit():
 connection=json.loads((out/'connection.json').read_text())
 ledger=SessionLedger(project,state,connection)
 with RuntimeLog(state/'ledger',read_only=True) as log:
  ledger.log=log;ledger.kernel=FrameKernel(log)
  return dict(history=ledger.history(),current=ledger.current())
def turn(command,label):
 master,slave=pty.openpty();fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',36,130,0,0))
 process=subprocess.Popen([exe,'session',str(project),'--state',str(state)],cwd=project,env=env,stdin=slave,stdout=slave,stderr=slave,start_new_session=True);os.close(slave)
 transcript=bytearray();started=time.monotonic();sent=False;completed=False;last_heartbeat=started
 try:
  while time.monotonic()-started<1800:
   ready,_,_=select.select([master],[],[],.2)
   if ready:
    try:data=os.read(master,65536)
    except OSError:break
    transcript.extend(data)
    if b'\x1b[6n' in data:os.write(master,b'\x1b[1;1R')
   if not sent and b'You>' in transcript:
    time.sleep(.7);os.write(master,command.encode()+b'\r');sent=True
   text=transcript.decode(errors='replace')
   if 'Needs recovery:' in text or 'Could not submit:' in text or 'Could not open session:' in text:
    raise AssertionError('client reported failure; inspect '+label+'-terminal.txt')
   markers=['Chosen checks passed; review the result.','The turn ended; its checks have not established success.','Selected saved turn ']
   if sent and any(marker in text for marker in markers):
    completed=True;time.sleep(.3);os.write(master,b'/exit\r');break
   if process.poll() is not None:raise RuntimeError('terminal exited unexpectedly')
   if time.monotonic()-last_heartbeat>30:
    print(json.dumps(dict(phase=label,pid=process.pid,elapsed=time.monotonic()-started)),flush=True);last_heartbeat=time.monotonic()
  if not completed:raise TimeoutError('terminal turn deadline '+label)
  process.wait(timeout=60);assert process.returncode==0
  record=audit();row=record['history'][-1];assert row['result']['status']=='finished',row['result']['status']
  result['turns'].append(dict(label=label,command=command,seconds=time.monotonic()-started,id=row['id'],result=row['result']))
  (out/(label+'-audit.json')).write_text(json.dumps(record,indent=2)+'\n');save()
  return record
 finally:
  if process.poll() is None:
   os.write(master,b'/exit\r')
   try:process.wait(timeout=60)
   except subprocess.TimeoutExpired:process.terminate();process.wait(timeout=10)
  os.close(master)
  if env['BW_COW_API_KEY'].encode() in transcript:raise AssertionError('key in transcript')
  (out/(label+'-terminal.txt')).write_bytes(transcript)
try:
 assert not (project/'index.html').exists(),'new fixture path already populated'
 (project/'index.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Bird Notes</title><style>body{font-family:system-ui;margin:2rem}h1{color:navy}</style><h1>Bird Notes</h1><p>Birds are wonderful neighbors.</p><button onclick="document.getElementById(\'fact\').textContent=\'Birds have feathers.\'">Show a bird fact</button><p id="fact"></p></html>')
 connected=subprocess.run([exe,'connect','http://10.0.7.68:18099'],env=env,capture_output=True,text=True,timeout=20)
 (out/'connect.txt').write_text(connected.stdout+connected.stderr);assert connected.returncode==0
 first=turn('Make this little bird page pretty and easy to read on a phone. Make its main heading blue. Keep the button working and keep everything in index.html with no downloads.','work')
 (out/'work.html').write_bytes((project/'index.html').read_bytes())
 edited=turn('/edit 1 Make this little bird page pretty and easy to read on a phone. Make its main heading purple instead of blue. Keep the button working and keep everything in index.html with no downloads.','edit')
 (out/'edit.html').write_bytes((project/'index.html').read_bytes());purple=hashlib.sha256((project/'index.html').read_bytes()).hexdigest()
 assert len(edited['history'])==2 and edited['history'][0]['result']==first['history'][0]['result']
 explored=turn('/explore 1 Try making the main heading green, using the current files. Keep everything else and keep the button working. Keep everything in index.html with no downloads.','explore')
 assert hashlib.sha256((project/'index.html').read_bytes()).hexdigest()==purple,'exploration changed original project'
 alternative=Path(explored['current']['workdir']);assert alternative!=project and alternative.is_relative_to(state/'alternatives')
 (out/'explore.html').write_bytes((alternative/'index.html').read_bytes())
 assert explored['history'][2]['input']['target']==first['history'][0]['id']
 # Close/reopen and select prior results through the installed terminal.
 selected=turn('/switch 2','switch-edit');assert selected['current']['context']==edited['current']['context'];assert Path(selected['current']['workdir'])==project
 assert hashlib.sha256((project/'index.html').read_bytes()).hexdigest()==purple
 selected=turn('/switch 3','switch-explore');assert selected['current']['context']==explored['current']['context'];assert Path(selected['current']['workdir'])==alternative
 result.update(status='PASS',original_preserved_during_explore=True,matching_selection=True,model_task_acceptance='browser check still required')
except BaseException as error:
 result.update(status='FAIL',error=repr(error),traceback=traceback.format_exc());raise
finally:
 result['finished']=time.time();save()
 # Signal remote service manager even after a failure; it restores the original service.
 receipt=out/'client-finished.json';receipt.write_text(json.dumps(dict(status=result['status'],evidence=str(out/'result.json')))+'\n')
 subprocess.run(['scp','-q','-i',str(Path.home()/'.ssh/id_ed25519_codi_fleet'),'-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','HostKeyAlias=llm-60','-o','IdentitiesOnly=yes',str(receipt),'dflanag3@10.0.7.68:/home/dflanag3/spatial-artifacts/bw-fast-integration-20261020/client-finished.json'],check=True)
