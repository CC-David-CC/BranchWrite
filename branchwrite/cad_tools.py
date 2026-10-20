"""Host-bound CAD capability on the existing registry and workflow ledger."""
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import json
from .cad_execution import CadRuntime,build_candidate,evaluate_candidate,MAX_INPUT
from .cad_requirements import PlateSpec
from .cad_carrier import CarrierSpec
from .records import Artifact,encode,decode,MAX_BYTES
from .execution import ToolRejected

@dataclass(frozen=True)
class CadCapability:
    runtime:CadRuntime
    requirements:PlateSpec
    def __post_init__(self):
        if type(self.runtime) is not CadRuntime or type(self.requirements) not in (PlateSpec,CarrierSpec) or self.runtime.osmesa is None:
            raise ValueError('host CAD runtime and exact requirements required')
    @property
    def identity(self):
        return sha256(encode(('bw.cad.v1',self.runtime.identity,self.requirements.identity,
            sha256(Path(__file__).read_bytes()).hexdigest()))).hexdigest()

def capture_sources(registry):
    rows=[];total=0
    for path in sorted(registry.executor.workspace.rglob('*')):
        if path.is_dir():continue
        relative=path.relative_to(registry.executor.workspace).as_posix()
        if not registry._grant.permits_file('read_paths',relative):continue
        body=registry.executor._read_private_bytes(relative);rows.append((relative,body));total+=len(body)
        if len(rows)>1000 or total>MAX_INPUT:raise ToolRejected('CAD project source capacity exceeded')
    return tuple(rows)

def execute_cad(registry,plan,operation_id,args,inventory):
    from .tool_registry import ToolOutcome
    cap=registry._cad;rows=capture_sources(registry);built=build_candidate(rows,args['path'],cap.runtime)
    details={k:v for k,v in built.items() if k not in ('stdout','stderr','step')}
    details.update(capability_id=cap.identity,requirements_id=cap.requirements.identity,workspace_after_sha256=inventory)
    stdout=built['stdout'];stderr=built['stderr'];assets=[];manifest=[];image=None
    disposition='cad_failed';exit_code=1
    if built['disposition']=='built':
        report=evaluate_candidate(built['step'],cap.requirements,cap.runtime)
        exports={'part.step':built['step'],**report.pop('assets')}
        # RuntimeLog has a frozen per-artifact limit. Reject a larger export
        # explicitly; never truncate it or silently call it a checked artifact.
        if any(len(body)>MAX_BYTES for body in exports.values()):raise ValueError('CAD artifact exceeds workflow artifact capacity')
        for name,body in exports.items():
            ref=registry.executor._artifact(body);assets.append(ref)
            manifest.append(dict(name=name,sha256=sha256(body).hexdigest(),bytes=len(body)))
            if name=='views.png':image=ref
        details.update(report,asset_manifest=manifest,build_isolation=built['isolation'])
        stdout=json.dumps(dict(geometry=report.get('geometry'),error=report.get('error'),requirements=cap.requirements.document()),sort_keys=True).encode()
        if report['status']=='PASS':disposition='cad_checked';exit_code=0
    if registry._inventory()!=inventory:raise ValueError('CAD source changed during build/check')
    return ToolOutcome(disposition,exit_code,built['elapsed_seconds']+details.get('elapsed_seconds',0),stdout,stderr,
        operation_id,plan.sha256,'inspect_cad',details=encode(details),image=image,assets=tuple(assets))

@dataclass(frozen=True)
class CadPolicy:
    capability_id:str
    @classmethod
    def admit(cls,spec,registry):
        if type(spec) is not dict or spec!={'schema':1,'cad':True} or type(spec.get('schema')) is not int or registry._cad is None:
            raise ValueError('closed host CAD verification policy required')
        return cls(registry._cad.identity)
    @property
    def identity(self):return sha256(encode(('bw.cad-policy.v1',self.capability_id))).hexdigest()
    def verify(self,registry,log,outcomes):
        outcomes=tuple(outcomes);witness=None
        with registry.executor._lock:
            registry._world_check();inventory=registry._inventory()
            for frame,value in outcomes:
                if value.get('tool')!='inspect_cad':continue
                witness=None # A later failed attempt supersedes earlier acceptance.
                try:
                    plan=decode(log.read_artifact(Artifact(*frame['inputs'])))
                    details=value['details'];manifest=details['asset_manifest'];files={a['name']:a for a in manifest}
                    valid=(frame['state']=='Closed' and len(plan)==8 and plan[:4]==('bw.tool-plan.v2',registry.identity,registry.world,'inspect_cad')
                        and plan[6]==inventory and details['workspace_after_sha256']==inventory
                        and value['plan_sha256']==frame['inputs'][0] and frame['dispatch'][0]==value['operation_id']
                        and decode(log.read_artifact(Artifact(*frame['result'])))[2]==value
                        and value['disposition']=='cad_checked' and value['exit_code']==0
                        and details['capability_id']==self.capability_id and details['requirements_id']==registry._cad.requirements.identity
                        and details['geometry']['status']=='PASS' and details['render']['artifact_sha256']==details['artifact_sha256']
                        and files['part.step']['sha256']==details['artifact_sha256']
                        and files['views.png']['sha256']==details['render']['contact_sheet']['sha256']
                        and value['image']==(files['views.png']['sha256'],files['views.png']['bytes'])
                        and len(files)==8 and len(manifest)==8)
                    for key in ('isolation','build_isolation'):
                        iso=details[key];valid=valid and iso['kind']=='bubblewrap-cad-v1' and iso['worker_exited'] is True and iso['namespace_members_after']==[]
                    for item in manifest:log.read_artifact(Artifact(item['sha256'],item['bytes']))
                    if valid:witness=frame['id']
                except (KeyError,TypeError,ValueError,OSError):pass
        result=dict(status='pass' if witness else 'fail',policy='cad-geometry-and-finish',policy_identity=self.identity,
            check_frame=witness,reason='current export, independent geometry and actual views matched' if witness else 'build and inspect current CAD source against the fixed requirements before finishing')
        from .pdf_tools import include_document_acceptance
        return include_document_acceptance(registry,log,outcomes,result)
