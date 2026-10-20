import fcntl,hashlib,importlib.metadata,json,os,pty,select,struct,subprocess,termios,time,urllib.request
from pathlib import Path
out=Path(__file__).parent;project=Path('/home/dflanag3/projects/branchwrite-default-dev42-smoke');project.mkdir(exist_ok=True)
key=Path('/home/dflanag3/spatial-artifacts/branchwrite-dev39-interactive-20261020/api-key.txt').read_text().strip()
def server_status():
 req=urllib.request.Request('http://10.0.7.68:8099/cow/status',headers={'Authorization':'Bearer '+key})
 with urllib.request.urlopen(req,timeout=10) as response:return json.load(response)
before=server_status();transcript=bytearray();master,slave=pty.openpty()
fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',32,120,0,0))
env=os.environ.copy();env.pop('PYTHONPATH',None);env['BW_COW_API_KEY']=key;env['TERM']='xterm-256color'
process=subprocess.Popen([str(out/'venv/bin/branchwrite')],cwd=project,env=env,stdin=slave,stdout=slave,stderr=slave,start_new_session=True)
os.close(slave)
def until(marker,timeout=20):
 end=time.monotonic()+timeout
 while marker not in transcript and time.monotonic()<end:
  ready,_,_=select.select([master],[],[],.2)
  if ready:
   try:data=os.read(master,65536)
   except OSError:break
   transcript.extend(data)
   if b'\x1b[6n' in data:os.write(master,b'\x1b[1;1R')
 if marker not in transcript:raise AssertionError('missing terminal marker '+repr(marker))
try:
 until(b'You>');os.write(master,b'/help\r');until(b'Enter steers current work')
 os.write(master,b'/plan\r');until(b'files stay unchanged')
 os.write(master,b'/history\r');until(b'No saved turns yet')
 os.write(master,b'/work\r');until(b'Work mode: I can edit')
 os.write(master,b'/exit\r');until(b'Settling current work');process.wait(timeout=20)
 assert process.returncode==0
 assert key.encode() not in transcript
 assert not (Path.home()/'.config/branchwrite/credentials.json').exists()
 assert list(project.iterdir())==[],'idle launch changed project files'
 after=server_status();assert before['completed']==after['completed'],'idle controls dispatched model work'
 result=dict(status='PASS',scope='Installed no-argument CLI, real PTY and authenticated LAN server; no inference requested',
   version='0.1.0.dev42',client_host=os.uname().nodename,server='llm-60',project=str(project),
   exit_code=process.returncode,key_in_output=False,key_saved=False,project_unchanged=True,
   completed_gpu_requests_before=before['completed'],completed_gpu_requests_after=after['completed'],
   controls=['help','plan','history','work','exit'],
   wheel_sha256=hashlib.file_digest((out/'branchwrite-0.1.0.dev42-py3-none-any.whl').open('rb'),'sha256').hexdigest())
 (out/'default-pty-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
finally:
 if process.poll() is None:process.terminate();process.wait(timeout=10)
 os.close(master);(out/'default-pty-transcript.txt').write_bytes(transcript)
