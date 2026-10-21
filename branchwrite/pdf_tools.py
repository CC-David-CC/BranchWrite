"""Built-in PDF observations and publication in the existing BW world/ledger."""
from dataclasses import dataclass,field
from hashlib import sha256
from pathlib import Path
import base64,json,time
from .pdf_execution import PdfRuntime,build_document,inspect_document
from .cad_tools import capture_sources
from .records import encode,decode,Artifact
from .terminal import _stat_key
from .execution import ToolRejected

@dataclass(frozen=True)
class PdfCapability:
    runtime:PdfRuntime=field(default_factory=PdfRuntime)
    identity:str=field(init=False)
    _source_key:tuple=field(init=False,repr=False)
    def __post_init__(self):
        if type(self.runtime) is not PdfRuntime:raise ValueError('host PDF runtime required')
        path=Path(__file__);key=_stat_key(path.stat())
        object.__setattr__(self,'_source_key',key)
        object.__setattr__(self,'identity',sha256(encode(('bw.pdf-capability.v1',self.runtime.identity,sha256(path.read_bytes()).hexdigest()))).hexdigest())
    def check(self):
        self.runtime.check()
        if _stat_key(Path(__file__).stat())!=self._source_key:raise ValueError('PDF tool implementation changed')


def execute_pdf(registry,plan,operation_id,args,inventory,tool):
    from .tool_registry import ToolOutcome,FileObservation
    from .command_outputs import initial_state,publish
    cap=registry._pdf;cap.check();start=time.monotonic();assets=[];build=None
    if tool=='build_pdf':
        before=initial_state(registry.executor,(args['output'],))
        build=build_document(capture_sources(registry),args['path'],cap.runtime)
        if build['disposition']!='built':
            return ToolOutcome('pdf_failed',1,time.monotonic()-start,build['stdout'],build['stderr'],operation_id,plan.sha256,tool,
                details=encode(dict(capability_id=cap.identity,build_disposition=build['disposition'],build_isolation=build['isolation'])))
        raw=build['pdf'];page=1
    else:
        raw=registry.executor._read_private_bytes(args['path']);page=args['page']
    try:view=inspect_document(raw,page,cap.runtime)
    except ValueError as error:
        # Rendering/validation precedes publication; a bad selected page has no
        # uncertain filesystem effect and is ordinary model-visible feedback.
        return ToolOutcome('pdf_failed',1,time.monotonic()-start,b'',str(error).encode('utf8'),operation_id,plan.sha256,tool,
            details=encode(dict(capability_id=cap.identity,error=str(error))))
    if view['status']!='PASS':
        return ToolOutcome('pdf_failed',1,time.monotonic()-start,b'',str(view.get('error')).encode('utf8'),operation_id,plan.sha256,tool,
            details=encode(dict(capability_id=cap.identity,inspection_isolation=view['isolation'],error=view.get('error'))))
    if registry._inventory()!=inventory:raise ValueError('PDF inputs changed while building or rendering')
    digest=sha256(raw).hexdigest();manifest=[];publication=[]
    if tool=='build_pdf':
        old_mode=before[0][2];row=dict(path=args['output'],deleted=False,bytes=len(raw),data=base64.b64encode(raw).decode(),sha256=digest,
                                     mode=format(old_mode if old_mode is not None else 0o600,'04o'))
        publication,stored=publish(registry.executor,(args['output'],),before,[row],operation_id);assets.extend(stored)
        path=args['output']
        manifest.append(dict(name=path,sha256=digest,bytes=len(raw)))
    else:
        path=args['path'];assets.append(registry.executor._artifact(raw))
        manifest.append(dict(name=path,sha256=digest,bytes=len(raw)))
    image=registry.executor._artifact(view.pop('image'));assets.append(image)
    manifest.append(dict(name='page-'+str(page)+'.png',sha256=image.sha256,bytes=image.size_bytes))
    details=dict(view,capability_id=cap.identity,pdf_path=path,pdf_bytes=len(raw),asset_manifest=manifest,
                 workspace_after_sha256=registry._inventory(),publication=publication)
    if build is not None:details.update(build_isolation=build['isolation'],source_id=build['source_id'],entry=args['path'])
    cap.check()
    summary=dict(status='PASS',pdf_path=path,pdf_sha256=digest,page=page,page_count=view['page_count'],text=view['text'],layout=view['layout'],
                 meaning='actual PDF parse and page render; visual correctness still requires reviewing the image')
    return ToolOutcome('pdf_built' if tool=='build_pdf' else 'pdf_rendered',0,time.monotonic()-start,
        json.dumps(summary,ensure_ascii=False).encode('utf8'),b'',operation_id,plan.sha256,tool,details=encode(details),
        observation=FileObservation(registry.world,path,digest),image=image,assets=tuple(assets))


def verify_documents(registry,log,outcomes):
    """Require current canonical page evidence, independently of named checks.

    This proves that every page of the current built document was actually
    rendered and made available to the workflow. It cannot prove the model
    understood the images, or that layout/content meets arbitrary requirements.
    The ordinary image-feedback loop and live acceptance tests cover that next
    boundary. No model-supplied 'reviewed' flag is accepted here.
    """
    from .pdf_contract import MAX_PAGES,RENDER_PROFILE
    documents={};invalid=False
    for frame,value in outcomes:
        tool=value.get('tool')
        if tool not in ('build_pdf','render_pdf'):continue
        try:
            plan=decode(log.read_artifact(Artifact(*frame['inputs'])))
            if (frame.get('state')!='Closed' or type(plan) is not tuple or len(plan)!=8
                    or plan[:4]!=('bw.tool-plan.v2',registry.identity,registry.world,tool)
                    or value['plan_sha256']!=frame['inputs'][0]
                    or frame['dispatch'][0]!=value['operation_id']
                    or frame['operation']!=registry.operation_kind(tool)
                    or log.read_artifact(Artifact(*frame['definition']))!=registry.definition_bytes(tool)
                    or decode(log.read_artifact(Artifact(*frame['result'])))[2]!=value):
                raise ValueError('unbound PDF receipt')
            args=registry._arguments(tool,plan[4]);path=args['output'] if tool=='build_pdf' else args['path']
            item=documents.setdefault(path,dict(build=None,pages={},failure=None))
            if tool=='build_pdf':item.update(build=None,pages={},failure='latest PDF build did not succeed')
            details=value['details']
            if details.get('capability_id')!=registry._pdf.identity:raise ValueError('PDF capability differs')
            for stream in ('stdout','stderr'):log.read_artifact(Artifact(*value[stream]))
            success=value['disposition']==('pdf_built' if tool=='build_pdf' else 'pdf_rendered') and value['exit_code']==0
            if not success:
                if tool=='render_pdf':item['pages'].pop(args['page'],None)
                continue
            digest=details['pdf_sha256'];page=details['page'];count=details['page_count']
            if (type(page) is not int or type(count) is not int or not 1<=page<=count<=MAX_PAGES
                    or page!=(1 if tool=='build_pdf' else args['page']) or details['pdf_path']!=path
                    or details['runtime_id']!=registry._pdf.runtime.identity
                    or details['render_profile']!=RENDER_PROFILE
                    or value['observation']!=(registry.world,path,digest)):
                raise ValueError('incompatible PDF page evidence')
            for key in (('isolation','build_isolation') if tool=='build_pdf' else ('isolation',)):
                iso=details[key]
                if iso['kind']!='bubblewrap-cad-v1' or iso['worker_exited'] is not True or iso['namespace_members_after']!=[]:
                    raise ValueError('PDF worker not retired')
            manifest=details['asset_manifest'];files={row['name']:row for row in manifest}
            if len(manifest)!=2 or len(files)!=2:raise ValueError('exact PDF and page artifacts required')
            pdf=files[path];image=files['page-'+str(page)+'.png']
            if pdf['sha256']!=digest or value['image']!=(image['sha256'],image['bytes']):raise ValueError('PDF/page binding differs')
            for row in manifest:body=log.read_artifact(Artifact(row['sha256'],row['bytes']))
            if not body.startswith(b'\x89PNG\r\n\x1a\n'):raise ValueError('actual page PNG missing')
            if tool=='build_pdf':item.update(build=details,failure=None)
            item['pages'][page]=dict(pdf_sha256=digest,page_count=count,frame=frame['id'])
        except (ToolRejected,KeyError,IndexError,TypeError,ValueError,OSError):invalid=True
    rows=[]
    for path,item in documents.items():
        try:
            current=sha256(registry.executor._read_private_bytes(path)).hexdigest()
            build=item['build'];same=(build is None or build['workspace_after_sha256']==registry._inventory())
            matching={p:row for p,row in item['pages'].items() if row['pdf_sha256']==current}
            count=build['page_count'] if build is not None else next(iter(matching.values()))['page_count']
            rendered=sorted(p for p,row in matching.items() if row['page_count']==count)
            missing=sorted(set(range(1,count+1))-set(rendered))
            passed=not item['failure'] and same and not missing and (build is None or build['pdf_sha256']==current)
            reason=('all actual current pages rendered; visual/content judgment remains separate' if passed else
                    item['failure'] or ('source/files changed since the latest PDF build; rebuild and render current pages' if not same else
                    'render every page of the current PDF before finishing'))
            rows.append(dict(path=path,status='pass' if passed else 'fail',pdf_sha256=current,page_count=count,
                             rendered_pages=rendered,missing_pages=missing,reason=reason))
        except (KeyError,TypeError,ValueError,OSError,ToolRejected,StopIteration):
            rows.append(dict(path=path,status='fail',rendered_pages=[],missing_pages=[],reason='current PDF or valid page evidence missing'))
    passed=not invalid and all(row['status']=='pass' for row in rows)
    return dict(status='pass' if passed else 'fail',pdf_documents=tuple(rows),
                reason='current PDF page evidence matched' if passed else
                       'PDF evidence missing, stale or invalid; rebuild after edits and render every current page')


def include_document_acceptance(registry,log,outcomes,result):
    """Compose the same page obligations with any primary domain policy.

    Installing a CAD/Blender capability must not weaken PDF completion. This
    remains the canonical PDF receipt verifier, not a separate model verdict.
    Domains with no PDF activity keep their existing acceptance requirements.
    """
    if registry._pdf is None:return result
    with registry.executor._lock:
        registry._world_check();documents=verify_documents(registry,log,outcomes)
    if documents['pdf_documents'] or documents['status']!='pass':
        result['pdf_documents']=documents['pdf_documents']
        if documents['status']!='pass':result.update(status='fail',reason=documents['reason'])
    return result
