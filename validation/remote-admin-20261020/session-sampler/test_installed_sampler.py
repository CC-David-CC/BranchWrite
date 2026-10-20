from pathlib import Path
import os,subprocess,pty,select,fcntl,termios,struct,time,json
r=Path(__file__).parent;p=r/'project';p.mkdir();state=r/'session';old=Path('/home/dflanag3/spatial-artifacts/bw-autonomous-admin-q4-20261020')
env=os.environ.copy();env.pop('PYTHONPATH',None);env.update(TERM='xterm-256color',BW_COW_CONNECTION=str(old/'connection.json'),BW_COW_API_KEY=(old/'operator-test-key.txt').read_text().strip())
m,s=pty.openpty();fcntl.ioctl(s,termios.TIOCSWINSZ,struct.pack('HHHH',30,120,0,0));q=subprocess.Popen([str(r/'venv/bin/branchwrite'),'session',str(p),'--state',str(state),'--sampler','min-p'],env=env,stdin=s,stdout=s,stderr=s,start_new_session=True);os.close(s);data=bytearray();sent=False;start=time.monotonic()
try:
 while time.monotonic()-start<30:
  if select.select([m],[],[],.1)[0]:
   try:chunk=os.read(m,65536)
   except OSError:break
   data.extend(chunk)
   if b'\x1b[6n' in chunk:os.write(m,b'\x1b[1;1R')
  if not sent and b'You>' in data:os.write(m,b'/exit\r');sent=True
  if q.poll() is not None:break
 q.wait(timeout=10)
 assert q.returncode==0 and sent
 assert b'New requests use min-p sampling' in data
 assert env['BW_COW_API_KEY'].encode() not in data
 assert not list(state.glob('turns/*/cow-operations/*.json'))
 (r/'installed-pty-result.json').write_text(json.dumps(dict(status='PASS',exit_code=q.returncode,sampler_display='min-p',submitted_tasks=0,native_operations=0,scope='installed real PTY; no model inference'))+'\n')
finally:
 os.close(m);(r/'installed-pty-terminal.txt').write_bytes(data)
print('PASS installed Min-P selection without inference')
