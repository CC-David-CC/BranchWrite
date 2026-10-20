"""Actual installed interactive CLI; one user prompt, no candidate edits."""
from pathlib import Path
import fcntl,os,pty,select,struct,subprocess,termios,time,json,traceback,hashlib
from branchwrite.session_ledger import SessionLedger
from branchwrite.records import RuntimeLog,Artifact,decode
from branchwrite.kernel import FrameKernel
out=Path(__file__).parent;exe=Path('/home/dflanag3/spatial-artifacts/bw-cli-workflows-dev63-20261020/venv/bin/branchwrite')
project=Path('/home/dflanag3/projects/bw-candidate-spatial-dev63-20261020');project.mkdir(mode=0o700,exist_ok=True)
state=out/'spatial-session';assert (state/'ledger').exists();assert not (out/'blender-result.json').exists(),'never resend an admitted turn';prior=json.loads((out/'cad-session-audit.json').read_text());cad_source=(project/'model.py').read_bytes()
prompt_path=Path('/home/dflanag3/src/branchwrite-documents-20261020/examples/prompts/blender.txt');prompt=prompt_path.read_text().strip()
env=dict(os.environ,BW_COW_CONNECTION=str(out/'connection.json'),BW_COW_API_KEY=(out/'operator-test-key.txt').read_text().strip(),PYTHONDONTWRITEBYTECODE='1',TERM='xterm-256color');env.pop('PYTHONPATH',None)
record=dict(status='RUNNING',controller_pid=os.getpid(),client_host=os.uname().nodename,prompt_sha256=hashlib.sha256(prompt_path.read_bytes()).hexdigest(),task=prompt,operator_candidate_edits=0,scope='installed dev63 interactive session -> candidate780e824a HTTP/Q4; reopen CAD session for Blender, prior context/files and actual image feedback; no operator task revisions')
started=time.monotonic();last=started;transcript=bytearray()
def save():
 record['elapsed_seconds']=time.monotonic()-started;temp=out/'blender-result.tmp';temp.write_text(json.dumps(record,indent=2)+'\n');os.replace(temp,out/'blender-result.json')
save();master=None;process=None
try:
 master,slave=pty.openpty();fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',40,140,0,0))
 process=subprocess.Popen([str(exe),'session',str(project),'--state',str(state),'--blender-config',str(out/'blender-config.json')],cwd=project,env=env,stdin=slave,stdout=slave,stderr=slave,start_new_session=True);os.close(slave);record['client_pid']=process.pid;save()
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
   (out/'blender-terminal.txt').write_bytes(transcript);save();print(json.dumps(dict(phase='interactive-blender',elapsed=record['elapsed_seconds'],client_pid=process.pid)),flush=True);last=time.monotonic()
  if time.monotonic()-started>1200 and not finished:record['status']='OBSERVATION_DEADLINE_CLIENT_LIVE';save() # keep observing the same handle
 process.wait(timeout=60);assert process.returncode==0;record['client_exit_code']=process.returncode
 connection=json.loads((out/'connection.json').read_text());ledger=SessionLedger(project,state,connection)
 with RuntimeLog(state/'ledger',read_only=True) as log:
  ledger.log=log;ledger.kernel=FrameKernel(log);history=ledger.history();assert len(history)==2;assert history[0]==prior['history'][0]
  result=history[-1]['result'];assert result['status']=='finished' and result['checks_passed'] is True
  assert result['exports'];record['workflow']=result['workflow'];record['file_commit']=result['file_commit'];record['context']=result['context'];record['exports']=result['exports']
  (out/'blender-session-audit.json').write_text(json.dumps(dict(history=history,current=ledger.current()),indent=2)+'\n')
 accepted=out/'blender-accepted';accepted.mkdir(mode=0o700,exist_ok=True)
 with RuntimeLog(Path(record['workflow'])/'ledger',read_only=True) as log:
  kernel=FrameKernel(log);checks=[]
  for frame in kernel.frames():
   if frame['state']=='Closed' and frame['contract']==('ToolOutcome','record'):
    value=decode(log.read_artifact(Artifact(*frame['result'])))[2]
    if value['tool']=='inspect_scene':checks.append(value)
  assert checks and checks[-1]['disposition']=='scene_checked';record['scene_builds']=len(checks);record['scene']=checks[-1]['details']['scene'];record['blender_receipt']=checks[-1]['details']
  for item in result['exports']:(accepted/item['name']).write_bytes(log.read_artifact(Artifact(item['sha256'],item['bytes'])))
 assert (project/'model.py').read_bytes()==cad_source,'Blender turn altered earlier CAD source';assert (project/'scene.py').is_file();(accepted/'scene.py').write_bytes((project/'scene.py').read_bytes());record['prior_cad_source_unchanged']=True;record['prior_history_unchanged']=True
 record.update(status='PASS_PENDING_VISUAL_REVIEW',project=str(project),session_state=str(state))
except BaseException as error:
 if record['status']=='RUNNING':record['status']='NEEDS_INSPECTION'
 record.update(error=repr(error),traceback=traceback.format_exc());raise
finally:
 (out/'blender-terminal.txt').write_bytes(transcript);save()
 if master is not None:os.close(master)
 print(json.dumps({k:v for k,v in record.items() if k not in ['exports','geometry','task','traceback']}),flush=True)
