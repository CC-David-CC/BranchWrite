"""Default installed PDF runtime and bounded build/independent page inspection.

No model/workflow authority. Reuses the actual Python supervisor and Linux
isolation boundary. ReportLab, pypdf and PDFium are normal package dependencies;
there is no per-task PDF runtime file or user-selected executable.
"""
from dataclasses import dataclass,field
from pathlib import Path
import base64,hashlib,json,os,subprocess,sys,tempfile,time
from .cad_execution import CadRuntime,_sources,_isolated_call
from .terminal import _stat_key

from .pdf_contract import MAX_PDF_BYTES as MAX_PDF,MAX_PAGES
PDF_PACKAGES={'reportlab':'5.0.1','pypdfium2':'5.14.0','pypdf':'6.21.1'}

@dataclass(frozen=True)
class PdfRuntime:
    timeout:float=60
    python:Path=field(default_factory=lambda:Path(sys.executable))
    runtime:CadRuntime=field(init=False,repr=False)
    identity:str=field(init=False)
    _pins:tuple=field(init=False,repr=False)
    def __post_init__(self):
        # Admitted package bytes stay immutable; later host imports must not
        # create bytecode inside the runtime whose full identity is pinned.
        sys.dont_write_bytecode=True
        runtime=CadRuntime(Path(self.python),timeout=self.timeout)
        code='import importlib.metadata as m,json;print(json.dumps({n:m.version(n) for n in '+repr(list(PDF_PACKAGES))+'}))'
        probe=subprocess.run([str(runtime.python),'-I','-B','-c',code],capture_output=True,text=True,timeout=10,check=True,
                             env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8'})
        versions=json.loads(probe.stdout)
        if versions!=PDF_PACKAGES:raise ValueError('installed PDF runtime differs from initial package pins')
        pins=tuple((p,_stat_key(p.stat()),hashlib.sha256(p.read_bytes()).hexdigest()) for p in
                   (Path(__file__),Path(__file__).with_name('pdf_build_worker.py'),Path(__file__).with_name('pdf_inspect_worker.py'),Path(__file__).with_name('pdf_contract.py')))
        identity=hashlib.sha256(json.dumps(dict(python_runtime=runtime.identity,packages=versions,
                           files=[(str(p),h) for p,_,h in pins]),sort_keys=True).encode()).hexdigest()
        object.__setattr__(self,'runtime',runtime);object.__setattr__(self,'_pins',pins);object.__setattr__(self,'identity',identity)
    def check(self):
        self.runtime.check()
        for path,key,_ in self._pins:
            if _stat_key(path.stat())!=key:raise ValueError('admitted PDF runtime changed')


def _job(runtime,worker,files,args):
    runtime.check()
    with tempfile.TemporaryDirectory(prefix='bw-pdf-') as tmp:
        root=Path(tmp);inputs=root/'input';inputs.mkdir();policy=root/'policy';policy.mkdir()
        (policy/'cad_build_worker.py').write_bytes(Path(__file__).with_name('cad_build_worker.py').read_bytes())
        (policy/'pdf_contract.py').write_bytes(Path(__file__).with_name('pdf_contract.py').read_bytes())
        for name,raw in files:
            path=inputs/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        result=_isolated_call(runtime.runtime,Path(__file__).with_name(worker),inputs,args,
                              launcher=runtime.runtime.python,extra_mounts=((policy,'/policy'),))
    runtime.check()
    return result


def build_document(sources,entry,runtime):
    if type(runtime) is not PdfRuntime:raise ValueError('admitted PDF runtime required')
    rows=_sources(sources,entry);started=time.monotonic()
    out,err,timed,limited,code,isolation=_job(runtime,'pdf_build_worker.py',rows,
              [str(runtime.runtime.python),entry,str(runtime.timeout)])
    result=dict(disposition='timeout' if timed else 'output_limit' if limited else 'worker_failed',
                exit_code=code,stdout=b'',stderr=err[-1048576:],pdf=None)
    if not(timed or limited or code):
        data=json.loads(out)
        if type(data) is not dict or set(data)!={'schema','disposition','exit_code','stdout','stderr','pdf'} or data['schema']!=1:
            raise ValueError('PDF builder response differs from pinned protocol')
        result=dict(disposition=data['disposition'],exit_code=data['exit_code'],stdout=base64.b64decode(data['stdout'],validate=True),
                    stderr=base64.b64decode(data['stderr'],validate=True),pdf=None if data['pdf'] is None else base64.b64decode(data['pdf'],validate=True))
        if result['pdf'] is not None and not 0<len(result['pdf'])<=MAX_PDF:raise ValueError('PDF output capacity exceeded')
        if (result['disposition']=='built')!=(result['pdf'] is not None and result['exit_code']==0):raise ValueError('incomplete PDF builder receipt')
    result.update(runtime_id=runtime.identity,isolation=isolation,elapsed_seconds=time.monotonic()-started,
                  source_id=hashlib.sha256(json.dumps([(p,hashlib.sha256(raw).hexdigest()) for p,raw in rows if p!='document.pdf'],sort_keys=True).encode()).hexdigest())
    return result


def inspect_document(pdf,page,runtime):
    if type(runtime) is not PdfRuntime or type(pdf) is not bytes or not 0<len(pdf)<=MAX_PDF:
        raise ValueError('bounded captured PDF and admitted runtime required')
    if type(page) is not int or not 1<=page<=MAX_PAGES:raise ValueError('page must be an integer from 1 to '+str(MAX_PAGES))
    started=time.monotonic();digest=hashlib.sha256(pdf).hexdigest()
    out,err,timed,limited,code,isolation=_job(runtime,'pdf_inspect_worker.py',(('document.pdf',pdf),),[str(page)])
    result=dict(status='FAIL',error='inspection timeout' if timed else 'inspection output limit' if limited else 'inspection worker failed',image=None)
    if not(timed or limited or code):
        result=json.loads(out)
        if result.get('schema')!=1 or result.get('status') not in ('PASS','FAIL'):raise ValueError('invalid PDF inspection protocol')
        if result['status']=='PASS':
            if result['pdf_sha256']!=digest or result['page']!=page:raise ValueError('PDF inspection identity mismatch')
            result['image']=base64.b64decode(result['image'],validate=True)
            if len(result['image'])>MAX_PDF or not result['image'].startswith(b'\x89PNG\r\n\x1a\n'):raise ValueError('PDF page is not a bounded PNG')
        if result.get('page_count') is not None and page>result['page_count']:raise ValueError('PDF page is outside the document')
    result.update(runtime_id=runtime.identity,isolation=isolation,elapsed_seconds=time.monotonic()-started,stderr=err[-4096:].decode('utf8','replace'))
    return result
