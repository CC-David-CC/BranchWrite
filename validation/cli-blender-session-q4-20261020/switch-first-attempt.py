from pathlib import Path
import fcntl,hashlib,json,os,pty,select,struct,subprocess,termios,time
from branchwrite.session_ledger import SessionLedger
from branchwrite.records import RuntimeLog
from branchwrite.kernel import FrameKernel
root=Path(__file__).parent;state=root/'spatial-session';project=Path('/home/dflanag3/projects/bw-candidate-spatial-dev63-20261020')
exe='/home/dflanag3/spatial-artifacts/bw-cli-workflows-dev63-20261020/venv/bin/branchwrite'
prior=json.loads((root/'blender-recovery-session-audit.json').read_text())['history'];assert len(prior)==2
model=(project/'model.py').read_bytes();scene=(project/'scene.py').read_bytes()
def receipts():return {str(p.relative_to(state)):hashlib.sha256(p.read_bytes()).hexdigest() for p in state.glob('turns/*/cow-operations/*.json')}
before=receipts();env=dict(os.environ,TERM='xterm-256color',PYTHONDONTWRITEBYTECODE='1',BW_COW_CONNECTION=str(root/'connection.json'),BW_COW_API_KEY=(root/'operator-test-key.txt').read_text().strip());env.pop('PYTHONPATH',None)
master,slave=pty.openpty();fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',40,140,0,0))
p=subprocess.Popen([exe,'session',str(project),'--state',str(state)],cwd=project,env=env,stdin=slave,stdout=slave,stderr=slave,start_new_session=True);os.close(slave)
raw=bytearray();stage=0;start=time.monotonic()
while p.poll() is None:
 if time.monotonic()-start>30:raise RuntimeError('observation limit; retain original control IDs and client handle '+str(p.pid))
 if select.select([master],[],[],.1)[0]:
  try:data=os.read(master,65536)
  except OSError:break
  raw.extend(data)
  if b'\x1b[6n' in data:os.write(master,b'\x1b[1;1R')
 text=raw.decode('utf8','replace')
 if 'Needs recovery:' in text:raise RuntimeError('control needs original-operation inspection')
 if stage==0 and 'You>' in text:os.write(master,b'/switch 1\r');stage=1
 if stage==1 and text.count('Selected saved turn ')>=1:
  assert not (project/'scene.py').exists();assert (project/'model.py').read_bytes()==model
  os.write(master,b'/switch 2\r');stage=2
 if stage==2 and text.count('Selected saved turn ')>=2:
  assert (project/'scene.py').read_bytes()==scene;assert (project/'model.py').read_bytes()==model
  os.write(master,b'/exit\r');stage=3
p.wait(timeout=5);assert p.returncode==0 and stage==3
(root/'switch-terminal.txt').write_bytes(raw);assert receipts()==before,'selecting saved versions must not call inference'
connection=json.loads((root/'connection.json').read_text());ledger=SessionLedger(project,state,connection)
with RuntimeLog(state/'ledger',read_only=True) as log:
 ledger.log=log;ledger.kernel=FrameKernel(log);h=ledger.history();assert len(h)==4 and h[:2]==prior
 assert h[2]['result']['context']==prior[0]['result']['context'];assert h[3]['result']['context']==prior[1]['result']['context']
 assert h[2]['result']['exports']==prior[0]['result']['exports'];assert h[3]['result']['exports']==prior[1]['result']['exports']
 assert ledger.current()['context']==prior[1]['result']['context']
 proof=dict(status='PASS',client_exit=p.returncode,commands=['/switch 1','/switch 2','/exit'],saved_turns=len(h),new_model_requests=0,all_existing_operation_journals_unchanged=True,prior_history_unchanged=True,file_versions_restored=True,matching_context_and_exports_restored=True,elapsed_seconds=time.monotonic()-start)
(root/'switch-result.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof));os.close(master)
