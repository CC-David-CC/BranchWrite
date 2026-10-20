"""Pinned Linux commands and opt-in model shell in read-only namespaces.

The model can compose shell commands only with an explicit host grant/config.
Both forms use one worker and the same file projection, process retirement and
receipt boundary. Writes use separate granted file tools; this is not an admin
capability or persistent terminal session. Writable shells need separate scopes.
"""
from dataclasses import dataclass,field
import base64,hashlib,json,math,os,re,stat,subprocess,tempfile,time
from pathlib import Path
from .execution import ToolRejected,ToolResult,Executor,_operation_id,_MAX_CAPTURE_BYTES

def _stat_key(info):
    return (info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_ctime_ns,stat.S_IMODE(info.st_mode))

@dataclass(frozen=True)
class NamedCommand:
    name: str
    argv: tuple[str,...]
    timeout: float=10.0
    _binary_key: tuple=field(init=False,repr=False)
    binary_sha256: str=field(init=False)
    def __post_init__(self):
        if (type(self.name) is not str or re.fullmatch('[A-Za-z][A-Za-z0-9_-]{0,31}',self.name) is None
                or type(self.argv) is not tuple or not 1<=len(self.argv)<=64
                or any(type(v) is not str or '\0' in v for v in self.argv)
                or sum(len(v.encode('utf8')) for v in self.argv)>32768
                or type(self.timeout) not in (int,float) or not math.isfinite(self.timeout)
                or not 0<self.timeout<=120):
            raise ToolRejected('bounded immutable host command definition required')
        executable=Path(self.argv[0])
        if (not executable.is_absolute() or str(executable)!=self.argv[0]
                or executable.parent not in (Path('/usr/bin'),Path('/bin'))
                or not executable.is_file() or not os.access(executable,os.X_OK)):
            raise ToolRejected('command executable must be a host system binary')
        # Ubuntu 26 packages coreutils as /usr/bin aliases into /usr/lib/cargo.
        # Admit root-owned, non-writable packaged targets throughout /usr;
        # a /usr/bin spelling must not grant a link to user-owned code.
        target=executable.resolve(strict=True)
        if not target.is_relative_to('/usr'):
            raise ToolRejected('command target is outside the system runtime')
        for path in (target,*target.parents):
            info=path.stat()
            if info.st_uid!=0 or info.st_mode&0o022:
                raise ToolRejected('command target has writable or non-root ownership')
            if path==Path('/usr'):break
        with executable.open('rb') as stream:
            info=os.fstat(stream.fileno());digest=hashlib.file_digest(stream,'sha256').hexdigest()
            if _stat_key(os.fstat(stream.fileno()))!=_stat_key(info):raise ToolRejected('command executable changed')
        object.__setattr__(self,'timeout',float(self.timeout))
        object.__setattr__(self,'_binary_key',_stat_key(info))
        object.__setattr__(self,'binary_sha256',digest)
    def check(self):
        if _stat_key(Path(self.argv[0]).stat())!=self._binary_key:raise ToolRejected('registered command executable changed')
    @property
    def wire(self):return (self.name,self.argv,self.timeout,self.binary_sha256,self._binary_key)

def command_table(commands):
    if type(commands) is not tuple or len(commands)>32 or any(not isinstance(v,NamedCommand) for v in commands):
        raise ToolRejected('bounded immutable host command tuple required')
    if len({v.name for v in commands})!=len(commands):raise ToolRejected('duplicate host command name')
    return tuple(sorted(commands,key=lambda v:v.name))

@dataclass(frozen=True)
class CommandResult(ToolResult):
    details: dict
    assets: tuple = ()

def _release_bytes():
    path=Path('/etc/os-release').resolve(strict=True)
    with path.open('rb') as stream:
        before=os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size>65536:raise ToolRejected('bounded host OS release unavailable')
        body=stream.read(65537)
        if len(body)!=before.st_size or _stat_key(os.fstat(stream.fileno()))!=_stat_key(before):
            raise ToolRejected('host OS release changed')
    return body

def execute_command(executor,operation_id,grant,name):
    operation_id=_operation_id(operation_id)
    if name not in grant.command_names:raise ToolRejected('command is not granted')
    command=next((v for v in executor._commands if v.name==name),None)
    if command is None:raise ToolRejected('unknown host command')
    return _execute_argv(executor,operation_id,grant,command,command.argv)

def _execute_argv(executor,operation_id,grant,command,command_argv):
    command.check()
    info=executor.workspace.lstat()
    if not stat.S_ISDIR(info.st_mode) or (info.st_dev,info.st_ino)!=executor._workspace_identity:
        raise ToolRejected('owned workspace is stale/replaced')
    # Snapshot only readable files. The child cannot read neighboring workspace
    # files, the caller's home, credentials, protected checks, or the live source.
    outputs=grant.output_paths
    from .command_outputs import initial_state,configure_namespace,publish,OUTPUT_LIMIT
    output_preimages=initial_state(executor,outputs) if outputs else ()
    inputs=[];bodies=[];total=0
    paths = grant.read_paths
    if grant.project_files:
        from .project_scope import expand_directories
        paths = expand_directories(executor.workspace, ["."])
    for path in paths:
        if path in grant.create_paths:
            # A readable future output need not exist yet. Project absence,
            # not an empty/fabricated file; tests may legitimately fail before
            # the model creates it. Links/unsafe paths still fail closed.
            try:executor._workspace_file(path)
            except FileNotFoundError:continue
        if path in outputs:
            try:executor._workspace_file(path)
            except FileNotFoundError:continue
        body=executor._read_private_bytes(path);total+=len(body)
        if total>64*1024**2:raise ToolRejected('command readable inputs exceed bound')
        mode=stat.S_IMODE(executor._workspace_file(path).stat(follow_symlinks=False).st_mode)&0o777
        inputs.append(dict(path=path,bytes=len(body),sha256=hashlib.sha256(body).hexdigest(),mode=format(mode,'04o')))
        bodies.append((path,body,mode))
    release=_release_bytes()
    started=time.monotonic()
    with tempfile.TemporaryDirectory(prefix='command-',dir=executor.run_dir) as temporary:
        stage=Path(temporary);projection=stage/'input';projection.mkdir(mode=0o700)
        for path,body,mode in bodies:
            destination=projection/path;destination.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
            # Preserve execution/read semantics. The namespace mount below
            # remains read-only even when the copied basic mode includes write.
            destination.write_bytes(body);destination.chmod(mode)
        release_file=stage/'os-release';release_file.write_bytes(release);release_file.chmod(0o400)
        package=Path(__file__).resolve().parent
        argv=['/usr/bin/prlimit','--core=0','--fsize=16777216','--as=2147483648',
            '--cpu='+str(math.ceil(command.timeout)+2),'--','/usr/bin/bwrap',
            '--die-with-parent','--new-session','--unshare-all','--unshare-user',
            '--disable-userns','--cap-drop','ALL','--clearenv']
        for path in ['/usr','/lib','/lib64']:argv+=['--ro-bind',path,path]
        argv+=['--proc','/proc','--dev','/dev','--size','67108864','--tmpfs','/tmp','--chmod','1777','/tmp',
            '--dir','/etc','--ro-bind',str(release_file),'/etc/os-release',
            '--ro-bind',str(package),'/app/branchwrite',
            '--ro-bind',str(projection),str(executor.workspace)]
        output_capacity=configure_namespace(argv,projection,executor.workspace,outputs) if outputs else {}
        argv+=['--chdir',str(executor.workspace),
            '--setenv','PATH','/usr/bin:/bin','--setenv','LANG','C.UTF-8',
            '--','/usr/bin/python3','-I','-B','/app/branchwrite/terminal_worker.py']
        request_row=dict(argv=command_argv,timeout=command.timeout)
        if outputs:request_row.update(schema=2,outputs=list(outputs))
        request=json.dumps(request_row,separators=(',',':')).encode()
        if len(request)>1024**2:raise ToolRejected('command request exceeds framing bound')
        if not hasattr(os,'memfd_create'):raise ToolRejected('terminal isolation requires Linux memfd')
        descriptor=os.memfd_create('bw-command-request',os.MFD_CLOEXEC)
        process=None
        try:
            with os.fdopen(descriptor,'w+b') as stream:
                stream.write(request);stream.seek(0)
                process=subprocess.Popen(argv,stdin=stream,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                    close_fds=True,start_new_session=True,env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8'})
            out,err,timed_out,limited,_=Executor._capture(process,time.monotonic()+command.timeout+3,((OUTPUT_LIMIT+2*_MAX_CAPTURE_BYTES)*4//3+1024**2) if outputs else 3*1024**2)
        finally:
            if process is not None and process.poll() is None:
                import signal
                Executor._signal_group(process,signal.SIGKILL);process.wait(timeout=3)
        if timed_out or limited or process.returncode!=0:
            raise ValueError('terminal worker did not settle: '+err.decode('utf8','replace')[-512:])
        row=json.loads(out)
        fields={'schema','argv','cwd','disposition','exit_code','stdout','stderr','isolation'}
        if outputs:fields|={'outputs','output_error'}
        if (type(row) is not dict or set(row)!=fields or row['schema']!=(2 if outputs else 1)
                or row['argv']!=list(command_argv) or row['cwd']!=str(executor.workspace)
                or row['disposition'] not in ('exited','timeout','output_limit','spawn_error')
                or (row['exit_code'] is not None and type(row['exit_code']) is not int)):
            raise ValueError('invalid terminal worker receipt')
        witness=row['isolation']
        if (type(witness) is not dict or witness.get('kind')!='bubblewrap-terminal-v1'
                or any(type(witness.get(name)) is not str
                    or witness[name]==os.readlink('/proc/self/ns/'+suffix)
                    for name,suffix in [('pid_ns','pid'),('net_ns','net'),('mount_ns','mnt')])):
            raise ValueError('terminal namespace isolation is not proven')
        from .browser_isolation import await_namespace_retirement
        members=await_namespace_retirement(witness['pid_ns'])
        if members:raise ValueError('terminal namespace retirement is not proven')
        witness.update(worker_exited=True,launcher_pid=process.pid,namespace_members_after=members)
        stdout=base64.b64decode(row['stdout'],validate=True);stderr=base64.b64decode(row['stderr'],validate=True)
        if max(len(stdout),len(stderr))>_MAX_CAPTURE_BYTES:raise ValueError('terminal output exceeds capture bound')
        details=dict(command=command.name,argv=list(command_argv),binary_sha256=command.binary_sha256,
            cwd=row['cwd'],inputs=inputs,os_release_sha256=hashlib.sha256(release).hexdigest(),
            execution_host=dict(hostname=os.uname().nodename,uid=os.getuid(),euid=os.geteuid(),gid=os.getgid()),
            isolation=witness,scope='host-fixed argv;read-only captured readable files;no network or host home')
        assets=()
        if outputs:
            if row['output_error'] is not None:
                if type(row['output_error']) is not str or len(row['output_error'])>512:raise ValueError('invalid output rejection')
                details.update(outputs=[],output_error=row['output_error'],output_capacity=output_capacity)
                row['disposition']='output_rejected'
            else:
                receipts,assets=publish(executor,outputs,output_preimages,row['outputs'],operation_id)
                details.update(outputs=receipts,output_capacity=output_capacity)
        # Only publish after actual namespace retirement. Upstream publication
        # uncertainty keeps the original intent unresolved; it is not resend.
        result=executor._result(operation_id,row['disposition'],row['exit_code'],started,stdout,stderr)
        return CommandResult(result.operation_id,result.disposition,result.exit_code,result.elapsed_seconds,
            result.stdout,result.stderr,details,assets)

MAX_SHELL_BYTES=16384

def validate_shell_parameters(timeout,expected_hostname=None):
    """Validate portable configuration, without admitting a host executable."""
    if (type(timeout) not in (int,float) or not math.isfinite(timeout)
            or not 0<timeout<=120):
        raise ToolRejected('bounded shell timeout required')
    if expected_hostname is not None and (type(expected_hostname) is not str
            or re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,252}',expected_hostname) is None):
        raise ToolRejected('bounded executor hostname required')

@dataclass(frozen=True)
class ShellConfig:
    """Host selects pinned Bash, timeout and optional executor hostname."""
    timeout: float=10.0
    expected_hostname: str|None=None
    _command: NamedCommand=field(init=False,repr=False)
    def __post_init__(self):
        validate_shell_parameters(self.timeout,self.expected_hostname)
        self.check_host()
        command=NamedCommand('shell',('/usr/bin/bash','--noprofile','--norc'),self.timeout)
        object.__setattr__(self,'timeout',command.timeout)
        object.__setattr__(self,'_command',command)
    @property
    def wire(self):return ('bw.readonly-shell.v1',self._command.wire,MAX_SHELL_BYTES,self.expected_hostname)
    def check_host(self):
        actual=os.uname().nodename
        if self.expected_hostname is not None and actual!=self.expected_hostname:
            raise ToolRejected('executor host mismatch: expected '+self.expected_hostname+', observed '+actual)
    def validate(self,text):
        self.check_host()
        if type(text) is not str or not text or '\0' in text or len(text.encode('utf8'))>MAX_SHELL_BYTES:
            raise ToolRejected('bounded nonempty shell command required')
        self._command.check()
        return self._command.argv+('-c',text)

def execute_shell(executor,operation_id,grant,text):
    operation_id=_operation_id(operation_id)
    if not grant.allow_shell or executor._shell is None:raise ToolRejected('shell is not granted/configured')
    config=executor._shell;argv=config.validate(text)
    result=_execute_argv(executor,operation_id,grant,config._command,argv)
    result.details['scope']=('model-written Bash; protected inputs; bounded declared outputs; no network or host home' if grant.output_paths else 'model-written Bash; read-only captured readable files; no network or host home')
    return result
