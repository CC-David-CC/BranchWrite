import fcntl,hashlib,json,os,pty,re,select,socket,struct,subprocess,termios,time,urllib.request
from pathlib import Path
out=Path(__file__).parent;old=Path('/home/dflanag3/spatial-artifacts/bw-model-pause-client-20261020');state=old/'session';project=Path('/home/dflanag3/projects/bw-active-format-steering-20261020')
exe=out/'venv/bin/branchwrite';env=os.environ.copy();env.pop('PYTHONPATH',None);env.update(TERM='xterm-256color',BW_COW_CONNECTION=str(old/'connection.json'),BW_COW_API_KEY=(old/'operator-test-key.txt').read_text().strip())
def operations():return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (state/'turns').rglob('*.json')}
before=operations();master,slave=pty.openpty();fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',36,160,0,0))
process=subprocess.Popen([str(exe),'session',str(project),'--state',str(state)],cwd=project,env=env,stdin=slave,stdout=slave,stderr=slave,start_new_session=True);os.close(slave)
transcript=bytearray();started=time.monotonic();sent=False;url=None;passed=False;first_url=None;first_port=None
try:
 while time.monotonic()-started<30:
  ready,_,_=select.select([master],[],[],.1)
  if ready:
   try:data=os.read(master,65536)
   except OSError:break
   transcript.extend(data)
   if b'\x1b[6n' in data:os.write(master,b'\x1b[1;1R')
  text=transcript.decode(errors='replace')
  if not sent and 'You>' in text:time.sleep(.3);os.write(master,b'/preview\r');sent=True
  match=re.search(r'http://127\.0\.0\.1:([0-9]+)/[A-Za-z0-9_-]+/index\.html',text)
  if match:
   matches=re.findall(r'http://127\.0\.0\.1:([0-9]+)/[A-Za-z0-9_-]+/index\.html',text)
   links=list(dict.fromkeys(re.findall(r'http://127\.0\.0\.1:[0-9]+/[A-Za-z0-9_-]+/index\.html',text)))
   if first_url is None:
    first_url=match.group();first_port=int(match.group(1));os.write(master,b'/preview\r');continue
   if len(links)<2:continue
   url=links[-1];port=int(url.split(':')[2].split('/')[0]);assert port==first_port,'refresh broke SSH tunnel'
   try:urllib.request.urlopen(first_url,timeout=2)
   except urllib.error.HTTPError as error:assert error.code==404
   else:raise AssertionError('old preview URL remained live')
   req=urllib.request.Request(url)
   with urllib.request.urlopen(req,timeout=3) as response:body=response.read();headers=dict(response.headers)
   assert hashlib.sha256(body).hexdigest()==hashlib.sha256((old/'steered.html').read_bytes()).hexdigest()
   (out/'preview.html').write_bytes(body);assert 'ssh -N -L '+str(port)+':127.0.0.1:'+str(port) in text,'remote help missing'
   os.write(master,b'/exit\r');process.wait(timeout=10)
   assert process.returncode==0;assert before==operations(),'preview altered a model operation or workflow'
   try:socket.create_connection(('127.0.0.1',port),timeout=.5)
   except OSError:pass
   else:raise AssertionError('preview port survived CLI exit')
   report=dict(status='PASS',installed_version='0.1.0.dev44',seconds=time.monotonic()-started,source_sha256=hashlib.sha256(body).hexdigest(),preview_url=url,headers=headers,remote_tunnel_help=True,model_operation_records_unchanged=True,preview_stopped_on_exit=True,refresh_preserves_port=True,old_url_retired=True,wheel_sha256=hashlib.sha256((out/'branchwrite-0.1.0.dev44-py3-none-any.whl').read_bytes()).hexdigest())
   (out/'preview-result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));passed=True;break
 assert passed,'preview did not complete; inspect preview-terminal.txt'
finally:
 if process.poll() is None:
  os.write(master,b'/exit\r')
  try:process.wait(timeout=10)
  except subprocess.TimeoutExpired:process.terminate();process.wait(timeout=5)
 os.close(master);assert env['BW_COW_API_KEY'].encode() not in transcript
 (out/'preview-terminal.txt').write_bytes(transcript)
