"""Trusted independent geometry worker. No candidate Python is imported."""
import base64,hashlib,json,sys,os
from pathlib import Path
sys.path.insert(0,'/trusted')
from branchwrite.cad_build_worker import candidate_process_policy
from branchwrite.cad_requirements import requirements_from_document
from branchwrite.cad_inspect import inspect_step
from branchwrite.cad_render import render_step

def run():
    protocol=os.dup(1);os.dup2(2,1) # Native OCCT diagnostics are not protocol data.
    candidate_process_policy()
    spec=requirements_from_document(json.loads(Path('/inputs/requirements.json').read_text()))
    step=Path('/inputs/part.step');identity=hashlib.sha256(step.read_bytes()).hexdigest()
    result=dict(schema=1,artifact_sha256=identity,requirements_id=spec.identity,status='FAIL',geometry=None,render=None,encoded_assets={})
    try:
        result['geometry']=inspect_step(step,spec)
        # Failed dimensional checks still merit actual views for diagnosis.
        result['render']=render_step(step,'/work/views')
        for path in sorted(Path('/work/views').iterdir()):
            result['encoded_assets'][path.name]=base64.b64encode(path.read_bytes()).decode()
        result['status']='PASS' if result['geometry']['status']=='PASS' else 'FAIL'
    except Exception as exc:result['error']=type(exc).__name__+': '+str(exc)[:4096]
    with os.fdopen(protocol,'w') as response:response.write(json.dumps(result,separators=(',',':'))+'\n')
if __name__=='__main__':run()
