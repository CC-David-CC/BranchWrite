from pathlib import Path
import hashlib,json,os,subprocess,sys,time,importlib.metadata,io
from PIL import Image
from branchwrite.pdf_execution import PdfRuntime,build_document,inspect_document
root=Path(__file__).parent;began=time.monotonic();runtime=PdfRuntime();rows=[]
assert Path(__import__('branchwrite').__file__).is_relative_to(root/'venv')
env=dict(os.environ);env.pop('PYTHONDONTWRITEBYTECODE',None);env.pop('PYTHONPATH',None)
for command in ['--help','doctor']:
 p=subprocess.run([str(root/'venv/bin/branchwrite'),command],cwd=root,env=env,capture_output=True,text=True,timeout=60)
 (root/('installed-'+command.strip('-')+'.txt')).write_text(p.stdout+p.stderr)
 assert p.returncode==0,(command,p.stdout,p.stderr)
 runtime.check();rows.append(dict(id=command,status='PASS',admitted_runtime_unchanged=True))
source=b"from reportlab.pdfgen import canvas\nc=canvas.Canvas('document.pdf',invariant=1)\nc.drawString(54,730,'Installed BranchWrite PDF')\nc.save()\n"
built=build_document((('report.py',source),),'report.py',runtime);assert built['disposition']=='built',built['stderr']
viewed=inspect_document(built['pdf'],1,runtime);assert viewed['status']=='PASS',viewed.get('error');assert 'Installed BranchWrite PDF' in viewed['text'];assert viewed['page_count']==1
image=Image.open(io.BytesIO(viewed['image']));assert image.format=='PNG'
assert built['isolation']['worker_exited'] and not built['isolation']['namespace_members_after']
assert viewed['isolation']['worker_exited'] and not viewed['isolation']['namespace_members_after']
(root/'installed-probe.pdf').write_bytes(built['pdf']);(root/'installed-probe.png').write_bytes(viewed['image'])
rows.append(dict(id='default-installed-pdf-build-reopen-render',status='PASS',pdf_sha256=hashlib.sha256(built['pdf']).hexdigest(),png_sha256=hashlib.sha256(viewed['image']).hexdigest(),bytes=len(built['pdf']),page_count=1))
wheel=next((root/'wheels').glob('*.whl'))
report=dict(status='PASS',source_commit='c419e4b640dfc66e42afe4ab575e5ad362d07265',version=importlib.metadata.version('branchwrite'),wheel_sha256=hashlib.sha256(wheel.read_bytes()).hexdigest(),python=sys.version,rows=rows,elapsed_seconds=time.monotonic()-began,scope='fresh installed wheel, real command/sandbox/default PDF boundaries; no model inference')
(root/'installed-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
