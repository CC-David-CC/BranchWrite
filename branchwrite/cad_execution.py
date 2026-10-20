"""One bounded build process for captured source; no execution authority from COW."""
from dataclasses import dataclass,field
from pathlib import Path,PurePosixPath
import base64,hashlib,json,math,os,stat,subprocess,tempfile,time
from .execution import Executor
from .terminal import NamedCommand,_stat_key
from .browser_isolation import await_namespace_retirement

MAX_INPUT=64*1024*1024
MAX_STEP=32*1024*1024

def _pins(roots):
    pins=[]
    for root in dict.fromkeys(roots):
        paths=[root] if root.is_file() else [root,*sorted(root.rglob('*'))]
        for path in paths:
            if path.is_symlink():
                target=path.resolve(strict=True)
                if not any(target.is_relative_to(r) for r in roots):raise ValueError('CAD runtime link leaves admitted runtime')
                pins.append((path,_stat_key(path.lstat()),'link:'+os.readlink(path)))
            elif path.is_dir():pins.append((path,_stat_key(path.stat()),'directory'))
            elif path.is_file():
                with path.open('rb') as f:
                    before=_stat_key(os.fstat(f.fileno()));digest=hashlib.file_digest(f,'sha256').hexdigest()
                    if _stat_key(os.fstat(f.fileno()))!=before:raise ValueError('CAD runtime changed during admission')
                pins.append((path,before,digest))
    return tuple(pins)

def _system_python_roots(prefix,base,executable,stdlib):
    """Pin the distro Python closure, never all unrelated files under /usr.

    Venv links keep the same closed-target rule. Only the OS stdlib's own
    regular-file links may add explicitly pinned system-library/config files.
    Nothing from a project or arbitrary home directory is admitted that way.
    """
    stdlib=stdlib.resolve(strict=True);executable=executable.resolve(strict=True)
    if not stdlib.is_relative_to(base/'lib') or not executable.is_relative_to(base/'bin'):
        raise ValueError('system Python paths leave their expected installation')
    roots=[prefix,stdlib,executable]
    config=Path('/etc')/('python'+str(stdlib.name.removeprefix('python')))
    for link in sorted(stdlib.rglob('*')):
        if not link.is_symlink():continue
        target=link.resolve(strict=True)
        if target.is_relative_to(stdlib):continue
        if not target.is_file() or not any(target.is_relative_to(parent) for parent in (base/'lib',base/'share',config)):
            raise ValueError('system Python dependency link leaves admitted OS paths')
        roots.append(target)
        if len(roots)>256:raise ValueError('system Python dependency capacity exceeded')
    roots=tuple(dict.fromkeys(roots))
    return roots,tuple(p for p in roots if p!=prefix and not p.is_relative_to(base))

@dataclass(frozen=True)
class CadRuntime:
    python:Path
    timeout:float=60
    osmesa:Path|None=None
    prefix:Path=field(init=False)
    base_prefix:Path=field(init=False)
    identity:str=field(init=False)
    aliases:tuple=field(init=False)
    support_paths:tuple=field(init=False)
    _pins:tuple=field(init=False,repr=False)
    _commands:tuple=field(init=False,repr=False)
    def __post_init__(self):
        if type(self.timeout) not in (int,float) or not math.isfinite(self.timeout) or not 0<self.timeout<=120:raise ValueError('bounded CAD timeout required')
        python=Path(self.python)
        if not python.is_absolute() or not python.is_file() or not os.access(python,os.X_OK):raise ValueError('absolute CAD Python executable required')
        result=subprocess.run([str(python),'-I','-B','-c','import sys,json;print(json.dumps([sys.prefix,sys.base_prefix,sys._base_executable]))'],cwd='/',env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8'},capture_output=True,text=True,timeout=10,check=True)
        prefix,base,base_executable=map(Path,json.loads(result.stdout))
        alias=base_executable.parent.parent
        if alias.resolve(strict=True)!=base:raise ValueError('Python launcher alias leaves pinned base runtime')
        aliases=() if alias==base else (alias,)
        if prefix==base or python.parent.parent!=prefix:raise ValueError('dedicated CAD virtual environment required')
        osmesa=None if self.osmesa is None else Path(self.osmesa).resolve(strict=True)
        if osmesa is not None and (not osmesa.is_dir() or not (osmesa/'libOSMesa.so.8').is_file()):raise ValueError('OSMesa library directory required')
        support_paths=()
        if base in (Path('/usr'),Path('/usr/local')):
            probe=subprocess.run([str(python),'-I','-B','-c',
                'import sysconfig;print(sysconfig.get_path("stdlib"))'],cwd='/',env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8'},
                capture_output=True,text=True,timeout=10,check=True)
            roots,support_paths=_system_python_roots(prefix,base,base_executable,Path(probe.stdout.strip()))
        else:roots=(prefix,base)
        if osmesa is not None:roots+= (osmesa,)
        pins=_pins(roots);commands=(NamedCommand('cad-bwrap',('/usr/bin/bwrap',)),NamedCommand('cad-prlimit',('/usr/bin/prlimit',)),NamedCommand('cad-supervisor',('/usr/bin/python3',)))
        worker=Path(__file__).with_name('cad_build_worker.py');worker_hash=hashlib.sha256(worker.read_bytes()).hexdigest()
        for name in ('cad_build_worker.py','cad_evaluate_worker.py','cad_requirements.py','cad_inspect.py','cad_carrier.py','cad_render.py','cad_execution.py','cad_tools.py','cad_config.py','__init__.py'):
            source=Path(__file__).with_name(name);pins+=((source,_stat_key(source.stat()),hashlib.sha256(source.read_bytes()).hexdigest()),)
        identity=hashlib.sha256(json.dumps(dict(runtime=[(str(p),h) for p,_,h in pins],commands=[c.wire for c in commands],worker=worker_hash,aliases=list(map(str,aliases)),osmesa=None if osmesa is None else str(osmesa),timeout=self.timeout),sort_keys=True).encode()).hexdigest()
        for name,value in [('osmesa',osmesa),('python',python),('prefix',prefix),('base_prefix',base),('aliases',aliases),('support_paths',support_paths),('_pins',pins),('_commands',commands),('identity',identity)]:object.__setattr__(self,name,value)
    def check(self):
        for command in self._commands:command.check()
        for path,key,_ in self._pins:
            if _stat_key(path.lstat() if path.is_symlink() else path.stat())!=key:raise ValueError('admitted CAD runtime changed')

def _sources(sources,entry):
    if type(sources) is not tuple or not 1<=len(sources)<=1000:raise ValueError('bounded captured source tuple required')
    rows=[];seen=set();total=0
    for item in sources:
        if type(item) is not tuple or len(item)!=2:raise ValueError('captured path and immutable bytes required')
        path,body=item
        if type(path) is not str or not path or '\0' in path or len(path.encode())>4096:raise ValueError('bounded relative source path required')
        pure=PurePosixPath(path)
        if pure.is_absolute() or str(pure)!=path or any(p in ('.','..','.git') for p in pure.parts) or path in seen:raise ValueError('source path escapes or aliases another input')
        if type(body) is not bytes:raise ValueError('captured source must be bytes')
        seen.add(path);total+=len(body)
        if total>MAX_INPUT:raise ValueError('source capacity exceeded')
        rows.append((path,body))
    for path in seen:
        if any(str(parent) in seen for parent in PurePosixPath(path).parents if str(parent)!='.'):
            raise ValueError('input file aliases a parent directory')
    if type(entry) is not str or entry not in seen or not entry.endswith('.py'):raise ValueError('captured Python entry required')
    return sorted(rows)

def build_candidate(sources,entry,runtime):
    rows=_sources(sources,entry)
    if type(runtime) is not CadRuntime:raise ValueError('admitted CAD runtime required')
    runtime.check();manifest=[dict(path=p,bytes=len(b),sha256=hashlib.sha256(b).hexdigest()) for p,b in rows if p!='part.step']
    source_id=hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest();started=time.monotonic()
    with tempfile.TemporaryDirectory(prefix='bw-cad-build-') as tmp:
        root=Path(tmp);projection=root/'input';projection.mkdir(mode=0o700)
        for path,body in rows:
            target=projection/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(body);target.chmod(0o400)
        out,err,timed_out,limited,exit_code,isolation=_isolated_call(runtime,Path(__file__).with_name('cad_build_worker.py'),projection,[str(runtime.python),entry,str(runtime.timeout)])
        if timed_out or limited or exit_code!=0:
            value=dict(disposition='timeout' if timed_out else 'output_limit' if limited else 'worker_failed',exit_code=exit_code,stdout=b'',stderr=err[-1024*1024:],step=None)
        else:
            try:
                data=json.loads(out)
                if type(data) is not dict or set(data)!={'schema','disposition','exit_code','stdout','stderr','step'} or data['schema']!=1:raise ValueError('bad CAD response')
                if data['disposition'] not in ('built','exited','timeout','output_limit','missing_artifact','output_rejected','background_processes') or type(data['exit_code']) is not int:raise ValueError('bad CAD result')
                value=dict(disposition=data['disposition'],exit_code=data['exit_code'],stdout=base64.b64decode(data['stdout'],validate=True),stderr=base64.b64decode(data['stderr'],validate=True),step=None if data['step'] is None else base64.b64decode(data['step'],validate=True))
                if max(len(value['stdout']),len(value['stderr']))>1024*1024 or (value['step'] is not None and len(value['step'])>MAX_STEP):raise ValueError('CAD response bound exceeded')
                if (value['disposition']=='built')!=(value['step'] is not None and value['exit_code']==0):raise ValueError('CAD response artifact mismatch')
            except (ValueError,TypeError,KeyError):value=dict(disposition='worker_failed',exit_code=exit_code,stdout=b'',stderr=b'invalid CAD worker result',step=None)
    runtime.check()
    value.update(source_id=source_id,inputs=manifest,runtime_id=runtime.identity,isolation=isolation,elapsed_seconds=time.monotonic()-started)
    return value

def _isolated_call(runtime,worker,inputs,arguments,*,launcher='/usr/bin/python3',extra_mounts=(),command=None):
    with tempfile.TemporaryFile() as info:
        argv=['/usr/bin/prlimit','--core=0','--fsize=33554432','--as=8589934592','--cpu='+str(math.ceil(runtime.timeout)+3),'--','/usr/bin/bwrap','--die-with-parent','--new-session','--unshare-all','--unshare-user','--disable-userns','--cap-drop','ALL','--clearenv','--info-fd',str(info.fileno())]
        for path in (Path('/usr'),Path('/lib'),Path('/lib64')):argv+=['--ro-bind',str(path),str(path)]
        for source,target in extra_mounts:argv+=['--ro-bind',str(source),target]
        if runtime.osmesa is not None:argv+=['--ro-bind',str(runtime.osmesa),str(runtime.osmesa),'--setenv','LD_LIBRARY_PATH',str(runtime.osmesa),'--setenv','LIBGL_ALWAYS_SOFTWARE','1']
        invocation=[str(launcher),'-I','-B','/runner.py',*arguments] if command is None else command
        argv+=['--ro-bind',str(worker),'/runner.py','--ro-bind',str(inputs),'/inputs','--proc','/proc','--dev','/dev','--size','67108864','--tmpfs','/tmp','--chmod','1777','/tmp','--size','134217728','--tmpfs','/work','--chdir','/work','--setenv','LANG','C.UTF-8','--setenv','PATH','/usr/bin:/bin','--setenv','HOME','/tmp','--setenv','PYTHONDONTWRITEBYTECODE','1']
        # Runtime mounts follow scratch mounts: a valid venv under /tmp must
        # not disappear beneath the worker's private /tmp filesystem.
        for path in dict.fromkeys((runtime.prefix,runtime.base_prefix,*runtime.support_paths)):
            argv+=['--ro-bind',str(path),str(path)]
        for alias in runtime.aliases:argv+=['--ro-bind',str(runtime.base_prefix),str(alias)]
        argv+=['--',*invocation]
        process=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,close_fds=True,pass_fds=(info.fileno(),),start_new_session=True,env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8'})
        try:out,err,timed_out,limited,_=Executor._capture(process,time.monotonic()+runtime.timeout+6,50*1024*1024)
        finally:
            if process.poll() is None:
                import signal
                Executor._signal_group(process,signal.SIGKILL);process.wait(timeout=3)
        info.seek(0);witness=json.load(info)
    for name,host in [('pid-namespace','pid'),('net-namespace','net'),('mnt-namespace','mnt')]:
        if witness.get(name)==int(os.readlink('/proc/self/ns/'+host).split('[')[1][:-1]):raise ValueError('CAD namespace was not isolated')
    namespace='pid:['+str(witness['pid-namespace'])+']';members=await_namespace_retirement(namespace)
    if members:raise ValueError('CAD worker namespace remains live')
    isolation=dict(kind='bubblewrap-cad-v1',pid_ns=namespace,net_ns='net:['+str(witness['net-namespace'])+']',mount_ns='mnt:['+str(witness['mnt-namespace'])+']',worker_exited=True,launcher_pid=process.pid,namespace_members_after=members)
    return out,err,timed_out,limited,process.returncode,isolation


def evaluate_candidate(step,spec,runtime):
    """Reopen untrusted geometry in a different process with no candidate source."""
    from .cad_requirements import PlateSpec
    from .cad_carrier import CarrierSpec
    if type(step) is not bytes or not 0<len(step)<=MAX_STEP:raise ValueError('bounded captured STEP bytes required')
    if type(spec) not in (PlateSpec,CarrierSpec) or type(runtime) is not CadRuntime or runtime.osmesa is None:
        raise ValueError('admitted requirements and CPU render runtime required')
    runtime.check();started=time.monotonic();identity=hashlib.sha256(step).hexdigest()
    with tempfile.TemporaryDirectory(prefix='bw-cad-evaluate-') as tmp:
        inputs=Path(tmp);(inputs/'part.step').write_bytes(step);(inputs/'requirements.json').write_text(json.dumps(spec.document()))
        # Only trusted inspection modules are exposed to this separate worker.
        # The build namespace never mounts this directory or receives these bytes.
        package=inputs/'package';package.mkdir();target=package/'branchwrite';target.mkdir()
        for name in ('__init__.py','cad_build_worker.py','cad_requirements.py','cad_inspect.py','cad_carrier.py','cad_render.py'):
            (target/name).write_bytes(Path(__file__).with_name(name).read_bytes())
        out,err,timed_out,limited,exit_code,isolation=_isolated_call(runtime,Path(__file__).with_name('cad_evaluate_worker.py'),inputs,[],launcher=runtime.python,extra_mounts=((package,'/trusted'),))
        if timed_out or limited or exit_code!=0:
            result=dict(status='FAIL',geometry=None,render=None,assets={},error='inspection timeout' if timed_out else 'inspection output limit' if limited else 'inspection worker failed',stderr=err[-4096:].decode('utf8','replace'))
        else:
            data=json.loads(out)
            if (type(data) is not dict or data.get('schema')!=1 or data.get('artifact_sha256')!=identity
                    or data.get('requirements_id')!=spec.identity or data.get('status') not in ('PASS','FAIL')):
                raise ValueError('inspection receipt identity mismatch')
            result=data;assets=result.pop('encoded_assets');result['assets']={}
            allowed={'top.png','bottom.png','side.png','isometric.png','views.png','index.html','render.json'}
            if type(assets) is not dict or set(assets)-allowed:raise ValueError('unregistered CAD output')
            total=0
            for name,body in assets.items():
                decoded=base64.b64decode(body,validate=True);total+=len(decoded)
                if total>32*1024*1024:raise ValueError('CAD evidence exceeds capacity')
                result['assets'][name]=decoded
            if result['status']=='PASS' and (result['geometry']['status']!='PASS' or result['render']['artifact_sha256']!=identity or not allowed<=set(result['assets'])):
                raise ValueError('incomplete CAD acceptance evidence')
    runtime.check();result.update(artifact_sha256=identity,requirements_id=spec.identity,runtime_id=runtime.identity,isolation=isolation,elapsed_seconds=time.monotonic()-started)
    return result
