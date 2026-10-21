"""Trusted stdlib-only build supervisor; deliberately excludes geometry checks."""
import base64,ctypes,errno,json,os,selectors,shutil,signal,stat,subprocess,sys,time
LIMIT=1024*1024
MAX_STEP=32*1024*1024

def candidate_process_policy():
    """Linux x86-64: one candidate process, threads allowed, no new namespaces.

    Installed in the single-threaded supervisor's child before exec. Hard AS/CPU
    limits then cover the candidate's shared address space. This is not a cgroup
    RSS guarantee or a claim of kernel vulnerability resistance. Other platforms
    fail closed until their syscall policy is implemented and exercised.
    """
    import platform
    if platform.machine()!='x86_64':raise OSError('CAD syscall policy requires Linux x86-64')
    class Filter(ctypes.Structure):
        _fields_=[('code',ctypes.c_ushort),('jt',ctypes.c_ubyte),('jf',ctypes.c_ubyte),('k',ctypes.c_uint)]
    class Program(ctypes.Structure):
        _fields_=[('length',ctypes.c_ushort),('filter',ctypes.POINTER(Filter))]
    allow=0x7fff0000;deny=0x00050000|errno.EPERM
    # seccomp_data: nr@0, arch@4, args[0]@16. Kill x32/other ABI.
    rows=[(0x20,0,0,4),(0x15,1,0,0xc000003e),(0x06,0,0,0x80000000),
          (0x20,0,0,0),(0x35,0,1,0x40000000),(0x06,0,0,0x80000000)]
    for syscall in (57,58,101,248,249,250,272,308,310,311):
        rows.extend([(0x15,0,1,syscall),(0x06,0,0,deny)])
    # glibc may fall back from clone3(ENOSYS) to clone for pthread_create.
    rows.extend([(0x15,0,1,435),(0x06,0,0,0x00050000|errno.ENOSYS),
                 (0x15,0,3,56),(0x20,0,0,16),(0x45,1,0,0x00010000),
                 (0x06,0,0,deny),(0x06,0,0,allow)])
    array=(Filter*len(rows))(*(Filter(*r) for r in rows));program=Program(len(rows),array)
    libc=ctypes.CDLL(None,use_errno=True)
    if libc.prctl(38,1,0,0,0)!=0 or libc.prctl(22,2,ctypes.byref(program),0,0)!=0:
        raise OSError(ctypes.get_errno(),'install CAD seccomp policy')

def run(*, output_name="part.step", output_limit=MAX_STEP, result_key="step"):
    # Candidate processes must not inspect/modify the supervisor through /proc.
    libc=ctypes.CDLL(None,use_errno=True)
    if libc.prctl(4,0,0,0,0)!=0:raise OSError(ctypes.get_errno(),'PR_SET_DUMPABLE')
    python,entry,seconds=sys.argv[1:];seconds=float(seconds)
    for root,dirs,files in os.walk('/inputs'):
        for name in files:
            source=os.path.join(root,name);relative=os.path.relpath(source,'/inputs')
            if relative==output_name:continue # Never accept an old output as a fresh build.
            destination=os.path.join('/work',relative);os.makedirs(os.path.dirname(destination),exist_ok=True);shutil.copyfile(source,destination)
    os.chdir('/work')
    launch="import runpy,sys;sys.path.insert(0,'/work');runpy.run_path(sys.argv[1],run_name='__main__')"
    child=subprocess.Popen([python,'-I','-B','-c',launch,'/work/'+entry],stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,close_fds=True,start_new_session=True,preexec_fn=candidate_process_policy)
    streams=[bytearray(),bytearray()];selector=selectors.DefaultSelector()
    for index,stream in enumerate((child.stdout,child.stderr)):
        os.set_blocking(stream.fileno(),False);selector.register(stream,selectors.EVENT_READ,index)
    deadline=time.monotonic()+seconds;disposition='exited'
    while selector.get_map() or child.poll() is None:
        if time.monotonic()>deadline:disposition='timeout';break
        for key,_ in selector.select(min(.1,max(0,deadline-time.monotonic()))):
            data=os.read(key.fileobj.fileno(),65536)
            if not data:selector.unregister(key.fileobj);continue
            target=streams[key.data];remaining=LIMIT-len(target);target.extend(data[:remaining])
            if len(data)>remaining:
                disposition='output_limit';break
        if disposition!='exited':break
    if child.poll() is None:
        try:os.killpg(child.pid,signal.SIGKILL)
        except ProcessLookupError:pass
    child.wait(timeout=3);selector.close()
    # All these PIDs are in this owned namespace. Detached grandchildren must
    # not remain alive to rewrite an export while it is being captured.
    descendants=[]
    for name in os.listdir('/proc'):
        if name.isdecimal() and int(name) not in (1,os.getpid()):
            try:os.kill(int(name),signal.SIGKILL);descendants.append(int(name))
            except ProcessLookupError:pass
    if descendants and disposition=='exited':disposition='background_processes'
    step=None
    if disposition=='exited' and child.returncode==0:
        try:
            fd=os.open('/work/'+output_name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
            with os.fdopen(fd,'rb') as f:
                if not stat.S_ISREG(os.fstat(f.fileno()).st_mode):raise ValueError('not a regular STEP export')
                step=f.read(output_limit+1)
                if not step or len(step)>output_limit:raise ValueError('STEP export size rejected')
            disposition='built'
        except FileNotFoundError:
            disposition='missing_artifact'
            streams[1].extend(('\n[BranchWrite build verification] The program exited successfully but did not create '
                +output_name+'. Save this exact filename in the worker working directory; the host publishes it under the requested destination name.\n').encode('utf8'))
        except (OSError,ValueError):
            disposition='output_rejected';step=None
            streams[1].extend(('\n[BranchWrite build verification] Rejected '+output_name+
                ': a fresh regular nonempty file of at most '+str(output_limit)+' bytes is required.\n').encode('utf8'))
    result=dict(schema=1,disposition=disposition,exit_code=child.returncode,
        stdout=base64.b64encode(streams[0]).decode(),stderr=base64.b64encode(streams[1]).decode(),
        **{result_key:None if step is None else base64.b64encode(step).decode()})
    sys.stdout.write(json.dumps(result,separators=(',',':'))+'\n');sys.stdout.flush()
if __name__=='__main__':run()
