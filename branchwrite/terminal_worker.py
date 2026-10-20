"""Trusted worker inside one short-lived, read-only terminal namespace."""
import base64,json,os,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from branchwrite.execution import Executor,_MAX_CAPTURE_BYTES
def main():
    request=json.loads(sys.stdin.buffer.read(1024*1024+1))
    writing=isinstance(request,dict) and request.get('schema')==2
    expected={'schema','argv','timeout','outputs'} if writing else {'argv','timeout'}
    if type(request) is not dict or set(request)!=expected:raise ValueError('invalid command framing')
    paths=tuple(request['outputs']) if writing else ()
    if writing:
        from branchwrite.command_outputs import validate_paths,initialize_private,collect_private
        validate_paths(paths,paths)
        directory_modes=initialize_private(paths)
    argv=request['argv'];timeout=request['timeout']
    if type(argv) is not list or not argv or any(type(v) is not str or '\0' in v for v in argv):raise ValueError('invalid fixed argv')
    witness=dict(kind='bubblewrap-terminal-v1',pid_ns=os.readlink('/proc/self/ns/pid'),
        net_ns=os.readlink('/proc/self/ns/net'),mount_ns=os.readlink('/proc/self/ns/mnt'))
    started=time.monotonic();process=None
    try:
        process=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
            close_fds=True,start_new_session=True,env=dict(PATH='/usr/bin:/bin',LANG='C.UTF-8',LC_ALL='C.UTF-8',HOME='/tmp'))
    except OSError as error:
        stdout=b'';stderr=str(error).encode()[:4096];disposition='spawn_error';code=None
    else:
        stdout,stderr,timed_out,limited,_=Executor._capture(process,started+timeout,_MAX_CAPTURE_BYTES)
        disposition='timeout' if timed_out else 'output_limit' if limited else 'exited';code=process.returncode
    result=dict(schema=1,argv=argv,cwd=os.getcwd(),disposition=disposition,exit_code=code,
        stdout=base64.b64encode(stdout).decode(),stderr=base64.b64encode(stderr).decode(),isolation=witness)
    if writing:
        try:outputs=collect_private(paths,directory_modes);output_error=None
        except (ValueError,OSError) as error:outputs=[];output_error=str(error)[:512]
        result.update(schema=2,outputs=outputs,output_error=output_error)
    sys.stdout.write(json.dumps(result,separators=(',',':')))
if __name__=='__main__':main()
