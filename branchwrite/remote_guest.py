"""One bounded remote command. Transport code, not a second BW interpreter.

The target VM is an explicitly host-granted administrative scope. Its services
may intentionally survive the command (for example nginx). This worker does not
claim that a shell cwd contains root administration or that all VM work stopped.
No credential or BW ledger is copied into the target.
"""
import base64,hashlib,json,math,os,selectors,signal,subprocess,sys,tempfile,time
LIMIT=1024*1024

def main():
 raw=sys.stdin.buffer.read(8*1024*1024+1)
 if len(raw)>8*1024*1024:raise ValueError('request exceeds bound')
 r=json.loads(raw)
 expected={'schema','operation_id','command','timeout'}
 if type(r) is dict and r.get('schema')==2:expected.add('stdin_b64')
 if (type(r) is not dict or set(r)!=expected
     or type(r['schema']) is not int or r['schema'] not in (1,2) or type(r['operation_id']) is not str
     or type(r['command']) is not str or not r['command'] or len(r['command'].encode())>16384
     or type(r['timeout']) not in (int,float) or not math.isfinite(r['timeout']) or not 0<r['timeout']<=600):
  raise ValueError('invalid bounded remote command')
 payload=base64.b64decode(r.get('stdin_b64',''),validate=True)
 if len(payload)>4*1024*1024:raise ValueError('stdin exceeds bound')
 started=time.monotonic();code=None;disposition='spawn_error';pid=None
 # Bound only captured streams. A process-wide RLIMIT_FSIZE also limits apt,
 # compilers and ordinary project writes, so it cannot implement this promise.
 stdout=bytearray();stderr=bytearray()
 input_stream=tempfile.TemporaryFile()
 input_stream.write(payload);input_stream.seek(0)
 try:
  p=subprocess.Popen(['/bin/bash','-c',r['command']],stdin=input_stream,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
   start_new_session=True,close_fds=True,
   env=dict(PATH='/usr/sbin:/usr/bin:/sbin:/bin',HOME=os.path.expanduser('~'),LANG='C.UTF-8',LC_ALL='C.UTF-8'))
 except OSError as error:stderr.extend(str(error).encode()[:4096])
 else:
  pid=p.pid;disposition='exited'
  with selectors.DefaultSelector() as ready:
   for stream,buffer in [(p.stdout,stdout),(p.stderr,stderr)]:
    os.set_blocking(stream.fileno(),False);ready.register(stream,selectors.EVENT_READ,buffer)
   try:
    while ready.get_map():
     remaining=r['timeout']-(time.monotonic()-started)
     if remaining<=0:
      disposition='timeout';break
     for key,_ in ready.select(min(.05,remaining)):
      chunk=os.read(key.fileobj.fileno(),65536)
      if not chunk:
       ready.unregister(key.fileobj);key.fileobj.close();continue
      buffer=key.data;buffer.extend(chunk[:LIMIT-len(buffer)])
      if len(buffer)>=LIMIT:
       disposition='output_limit';break
     if disposition=='output_limit':break
    # Pipes may close before the shell exits; the deadline still covers waiting.
    if disposition=='exited':
     try:code=p.wait(timeout=max(0,r['timeout']-(time.monotonic()-started)))
     except subprocess.TimeoutExpired:disposition='timeout'
    if disposition!='exited':
     try:os.killpg(p.pid,signal.SIGKILL)
     except ProcessLookupError:pass
     # Permission/retirement errors intentionally escape: the host must keep the
     # original effect indeterminate rather than acknowledge a settled command.
     code=p.wait(timeout=3)
   finally:
    p.stdout.close();p.stderr.close()
 input_stream.close()
 result=dict(schema=1,operation_id=r['operation_id'],request_sha256=hashlib.sha256(raw).hexdigest(),
  disposition=disposition,exit_code=code,stdout_b64=base64.b64encode(stdout).decode(),stderr_b64=base64.b64encode(stderr).decode(),
  elapsed_seconds=time.monotonic()-started,command_pid=pid,worker_pid=os.getpid())
 sys.stdout.write(json.dumps(result,separators=(',',':'),allow_nan=False));sys.stdout.flush()
if __name__=='__main__':main()
