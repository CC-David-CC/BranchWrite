"""Bounded native Blender build/reopen/render jobs; no workflow authority."""
from dataclasses import dataclass,field
from pathlib import Path
import base64,hashlib,json,os,tempfile,time,math
from .cad_execution import _pins,_sources,_isolated_call
from .terminal import NamedCommand,_stat_key

@dataclass(frozen=True)
class BlenderRuntime:
    prefix:Path
    timeout:float=120
    base_prefix:Path=field(init=False)
    osmesa:object=field(default=None,init=False)
    aliases:tuple=field(default=(),init=False)
    support_paths:tuple=field(default=(),init=False)
    identity:str=field(init=False)
    _pins:tuple=field(init=False,repr=False)
    _commands:tuple=field(init=False,repr=False)
    def __post_init__(self):
        root=Path(self.prefix).resolve(strict=True)
        if not root.is_dir() or not (root/'blender').is_file():raise ValueError('pinned Blender distribution required')
        if type(self.timeout) not in (int,float) or not math.isfinite(self.timeout) or not 0<self.timeout<=120:raise ValueError('bounded Blender deadline required')
        pins=_pins((root,))
        for name in ('blender_execution.py','blender_worker.py','cad_build_worker.py','cad_execution.py'):
            f=Path(__file__).with_name(name);pins+=((f,_stat_key(f.stat()),hashlib.sha256(f.read_bytes()).hexdigest()),)
        commands=(NamedCommand('blender-bwrap',('/usr/bin/bwrap',)),NamedCommand('blender-prlimit',('/usr/bin/prlimit',)))
        identity=hashlib.sha256(json.dumps(dict(files=[(str(f),h) for f,_,h in pins],timeout=self.timeout,render_profile='bw.blender-cpu-views-motion.v2'),sort_keys=True).encode()).hexdigest()
        for name,value in [('prefix',root),('base_prefix',root),('_pins',pins),('_commands',commands),('identity',identity)]:object.__setattr__(self,name,value)
    def check(self):
        for cmd in self._commands:cmd.check()
        for path,key,_ in self._pins:
            if _stat_key(path.lstat() if path.is_symlink() else path.stat())!=key:raise ValueError('Blender runtime changed')

def _job(runtime,rows,mode,entry=''):
    worker=Path(__file__).with_name('blender_worker.py')
    with tempfile.TemporaryDirectory(prefix='bw-blender-') as tmp:
        root=Path(tmp)
        for path,raw in rows:
            target=root/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
        # Only the generic syscall policy is shared with CAD. No geometry
        # acceptance code or host credentials is mounted in the scene builder.
        policy=root/'policy';policy.mkdir();(policy/'cad_build_worker.py').write_bytes(Path(__file__).with_name('cad_build_worker.py').read_bytes())
        cmd=[str(runtime.prefix/'blender'),'--background','--factory-startup','--disable-autoexec','--threads','4','--python-exit-code','17','--python','/runner.py','--',mode,entry]
        out,err,timed,limited,code,isolation=_isolated_call(runtime,worker,root,[],extra_mounts=((policy,'/policy'),),command=cmd)
        if timed or limited or code:raise ValueError(('Blender timeout' if timed else 'Blender output limit' if limited else 'Blender worker exited '+str(code))+': '+err[-3000:].decode('utf8','replace'))
        data=json.loads(out)
        if type(data) is not dict or set(data)!={'schema','status','error','scene','assets'} or data['schema']!=1 or data['status'] not in ('PASS','FAIL'):raise ValueError('invalid Blender worker receipt')
        assets={};total=0
        allowed={'scene.blend'} if mode=='build' else {'top.png','front.png','side.png','isometric.png','animation.mp4'}
        for name,body in data['assets'].items():
            if name not in allowed:raise ValueError('unregistered Blender artifact')
            raw=base64.b64decode(body,validate=True);total+=len(raw)
            if total>32*1024*1024:raise ValueError('Blender output capacity exceeded')
            assets[name]=raw
        if data['status']=='PASS' and set(assets)!=allowed:raise ValueError('incomplete Blender artifacts')
        data['assets']=assets;data['isolation']=isolation;return data

def build_scene(sources,entry,runtime):
    rows=_sources(sources,entry)
    if type(runtime) is not BlenderRuntime:raise ValueError('admitted Blender runtime required')
    runtime.check();started=time.monotonic()
    manifest=[dict(path=p,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw)) for p,raw in rows if p!='scene.blend']
    source_id=hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()
    built=_job(runtime,rows,'build',entry);assets=built['assets'];result=built
    if built['status']=='PASS':
        scene=assets['scene.blend'];result=_job(runtime,(('scene.blend',scene),),'inspect')
        result['build_isolation']=built['isolation'];result['assets'].update(assets)
        result['artifact_sha256']=hashlib.sha256(scene).hexdigest()
    runtime.check();result.update(source_id=source_id,inputs=manifest,runtime_id=runtime.identity,elapsed_seconds=time.monotonic()-started,
        asset_manifest=[dict(name=n,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw)) for n,raw in sorted(result['assets'].items())])
    return result
