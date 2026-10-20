"""Blender MCP observations use BW's existing plans, artifact store and verifier."""
from dataclasses import dataclass,field
from pathlib import Path
from hashlib import sha256
import base64,json,os,subprocess,tempfile,time
from .cad_execution import CadRuntime
from .blender_execution import BlenderRuntime
from .cad_tools import capture_sources
from .records import encode,decode,Artifact,MAX_BYTES
from .execution import Executor

@dataclass(frozen=True)
class BlenderCapability:
    runtime:BlenderRuntime
    mcp_python:Path
    require_animation:bool=True
    sdk:CadRuntime=field(init=False,repr=False)
    identity:str=field(init=False)
    def __post_init__(self):
        if type(self.runtime) is not BlenderRuntime or type(self.require_animation) is not bool:raise ValueError('host Blender capability required')
        sdk=CadRuntime(Path(self.mcp_python),timeout=120)
        files=tuple((name,sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()) for name in ('blender_tools.py','blender_mcp.py','blender_mcp_server.py'))
        identity=sha256(encode(('bw.blender-capability.v1',self.runtime.identity,sdk.identity,self.require_animation,files))).hexdigest()
        object.__setattr__(self,'sdk',sdk);object.__setattr__(self,'identity',identity)
    def check(self):self.runtime.check();self.sdk.check()

def execute_blender(registry,plan,operation_id,args,inventory):
    from .tool_registry import ToolOutcome
    cap=registry._blender;cap.check();sources=capture_sources(registry);started=time.monotonic()
    request=dict(python=str(cap.mcp_python),runtime=str(cap.runtime.prefix),timeout=cap.runtime.timeout,entry=args['path'],files={n:base64.b64encode(raw).decode() for n,raw in sources})
    env=dict(PATH='/usr/bin:/bin',HOME='/tmp',LANG='C.UTF-8',PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(Path(__file__).resolve().parent.parent))
    with tempfile.TemporaryFile() as stdin:
        stdin.write(json.dumps(request,separators=(',',':')).encode());stdin.seek(0)
        child=subprocess.Popen([str(cap.mcp_python),'-B','-m','branchwrite.blender_mcp'],stdin=stdin,stdout=subprocess.PIPE,stderr=subprocess.PIPE,cwd='/',env=env,close_fds=True,start_new_session=True)
        try:out,err,timed,limited,_=Executor._capture(child,time.monotonic()+2*cap.runtime.timeout+60,50*1024*1024)
        finally:
            if child.poll() is None:
                import signal
                Executor._signal_group(child,signal.SIGKILL);child.wait(timeout=3)
    if timed or limited or child.returncode:raise ValueError('Blender MCP transport failed: '+err[-3000:].decode('utf8','replace'))
    data=json.loads(out);raw_assets=data.pop('assets');assets=[];manifest=[];image=None
    allowed={'scene.blend','top.png','front.png','side.png','isometric.png','animation.mp4'}
    if type(raw_assets) is not dict or set(raw_assets)-allowed:raise ValueError('unregistered Blender output')
    for name,encoded in sorted(raw_assets.items()):
        raw=base64.b64decode(encoded,validate=True)
        if len(raw)>MAX_BYTES:raise ValueError('Blender output exceeds workflow artifact capacity')
        ref=registry.executor._artifact(raw);assets.append(ref);manifest.append(dict(name=name,sha256=sha256(raw).hexdigest(),bytes=len(raw)))
        if name=='isometric.png':image=ref
    if manifest!=data['asset_manifest']:raise ValueError('Blender MCP asset manifest differs from captured bytes')
    data.update(capability_id=cap.identity,workspace_after_sha256=inventory)
    if registry._inventory()!=inventory:raise ValueError('Blender source changed during inspection')
    cap.check();passed=data['status']=='PASS' and (not cap.require_animation or data['scene']['transform_animation_observed'])
    summary=dict(status='PASS' if passed else 'FAIL',error=data.get('error'),scene=data.get('scene'),asset_manifest=manifest)
    return ToolOutcome('scene_checked' if passed else 'scene_failed',0 if passed else 1,time.monotonic()-started,
        json.dumps(summary,sort_keys=True).encode(),err[-16384:],operation_id,plan.sha256,'inspect_scene',details=encode(data),image=image,assets=tuple(assets))

@dataclass(frozen=True)
class BlenderPolicy:
    capability_id:str
    @classmethod
    def admit(cls,spec,registry):
        if type(spec) is not dict or spec!={'schema':1,'blender':True} or type(spec.get('schema')) is not int or registry._blender is None:raise ValueError('closed host Blender policy required')
        return cls(registry._blender.identity)
    @property
    def identity(self):return sha256(encode(('bw.blender-policy.v1',self.capability_id))).hexdigest()
    def verify(self,registry,log,outcomes):
        outcomes=tuple(outcomes);witness=None
        with registry.executor._lock:
            registry._world_check();inventory=registry._inventory()
            for frame,value in outcomes:
                if value.get('tool')!='inspect_scene':continue
                witness=None
                try:
                    plan=decode(log.read_artifact(Artifact(*frame['inputs'])));d=value['details'];files={v['name']:v for v in d['asset_manifest']}
                    valid=(frame['state']=='Closed' and len(plan)==8 and plan[:4]==('bw.tool-plan.v2',registry.identity,registry.world,'inspect_scene')
                        and plan[6]==inventory and d['workspace_after_sha256']==inventory and value['plan_sha256']==frame['inputs'][0]
                        and frame['dispatch'][0]==value['operation_id'] and decode(log.read_artifact(Artifact(*frame['result'])))[2]==value
                        and d['capability_id']==self.capability_id and value['disposition']=='scene_checked' and value['exit_code']==0
                        and files['scene.blend']['sha256']==d['artifact_sha256'] and len(files)==6
                        and value['image']==(files['isometric.png']['sha256'],files['isometric.png']['bytes'])
                        and d['mcp']['initialized'] is True and d['mcp']['transport']=='stdio' and d['mcp']['tool']=='render_scene'
                        and d['scene']['render_profile']=='bw.blender-cpu-views-motion.v2'
                        and d['scene']['animation']==dict(start=1,end=24,fps=12,frames_rendered=24)
                        and (not registry._blender.require_animation or d['scene']['transform_animation_observed']))
                    for key in ('isolation','build_isolation'):
                        iso=d[key];valid=valid and iso['worker_exited'] is True and iso['namespace_members_after']==[]
                    for item in files.values():log.read_artifact(Artifact(item['sha256'],item['bytes']))
                    if valid:witness=frame['id']
                except (KeyError,TypeError,ValueError,OSError):pass
        result=dict(status='pass' if witness else 'fail',policy='blender-scene-and-finish',policy_identity=self.identity,
            check_frame=witness,reason='current saved scene, actual controlled renders and animation are retained' if witness else 'build and inspect the current scene with the configured Blender tool',
            scope='scene/render pipeline; visual/design quality not independently certified')
        from .pdf_tools import include_document_acceptance
        return include_document_acceptance(registry,log,outcomes,result)

def validate_blender_config(spec):
    if type(spec) is not dict or set(spec)!={'distribution','mcp_python','timeout','require_animation'}:raise ValueError('closed Blender runtime configuration required')
    import math
    if type(spec['require_animation']) is not bool or type(spec['timeout']) not in (int,float) or not math.isfinite(spec['timeout']) or not 0<spec['timeout']<=120:raise ValueError('bounded Blender parameters required')
    if any(type(spec[k]) is not str or not Path(spec[k]).is_absolute() for k in ('distribution','mcp_python')):raise ValueError('absolute Blender/MCP runtime paths required')
    return spec

def load_blender_config(spec):
    validate_blender_config(spec)
    return BlenderCapability(BlenderRuntime(Path(spec['distribution']),timeout=spec['timeout']),Path(spec['mcp_python']),spec['require_animation'])
