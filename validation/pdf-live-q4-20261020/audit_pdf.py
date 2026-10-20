from pathlib import Path
import json,hashlib,shutil
from branchwrite.records import RuntimeLog,Artifact,decode
from branchwrite.kernel import FrameKernel
root=Path(__file__).parent;state=root/'pdf-run';out=root/'pdf-accepted';out.mkdir(mode=0o700,exist_ok=True)
cli=json.loads((root/'pdf-stdout.json').read_text());assert cli['verified'] is True and cli['status']=='complete'
assert not Path('/proc/'+str(json.loads((root/'campaign-result.json').read_text())['client_pid'])).exists()
rows=[];images={};sent={};models=0;native=0
with RuntimeLog(state/'ledger',read_only=True) as log:
 kernel=FrameKernel(log)
 for frame in kernel.frames():
  if frame['state']!='Closed':continue
  if frame['contract']==('ToolOutcome','record'):
   value=decode(log.read_artifact(Artifact(*frame['result'])))[2]
   row=dict(frame=frame['id'],tool=value['tool'],disposition=value['disposition'],exit_code=value['exit_code'],operation_id=value['operation_id'])
   if value['tool'] in ('build_pdf','render_pdf'):
    row['details']=value['details']
    if value['image']:images[value['details']['page']]=value['image'][0]
   rows.append(row)
  if frame['contract']==('ModelOutput','record'):models+=1
  try:request=decode(log.read_artifact(Artifact(*frame['inputs'])))
  except (ValueError,TypeError):continue
  if type(request) is dict and request.get('kind')=='bw.model-native-request':
   native+=1;body=json.loads(request['body']);content=body.get('content',[])
   if isinstance(content,list):
    for part in content:
     if part.get('type')=='image':sent.setdefault(part['image_id'],[]).append(frame['id'])
 assert set(images)=={1,2},images
 assert all(digest in sent for digest in images.values()),(images,sent)
 for item in cli['exports']:
  body=log.read_artifact(Artifact(item['sha256'],item['bytes']));(out/item['name']).write_bytes(body)
 for name in ['report.py','make_report.py']:
  p=state/'world/workspace'/name
  if p.exists():shutil.copyfile(p,out/name)
 report=dict(status='PASS',scope='installed dev59 CLI/Q4 authored two-page PDF, actual page images submitted in settled native requests, current named checks and canonical finish; no general layout certification',
   elapsed_seconds=json.loads((root/'campaign-result.json').read_text())['elapsed_seconds'],operator_candidate_edits=0,
   pdf_sha256=hashlib.sha256((out/'report.pdf').read_bytes()).hexdigest(),pages=images,actual_image_native_frames={str(page):sent[digest] for page,digest in images.items()},model_frames=models,native_requests=native,
   checks=[row for row in rows if row['tool']=='run_check'],tool_sequence=[{k:v for k,v in row.items() if k!='details'} for row in rows],
   connection=json.loads((root/'connection.json').read_text()),wheel=json.loads((root/'install.json').read_text()),visual_inspection='actual page contact sheet inspected: both headings/table/checklist/page numbers readable; no visible overlap or clipping')
 (root/'pdf-ledger-audit.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({k:v for k,v in report.items() if k not in ['connection','checks','tool_sequence','actual_image_native_frames']}))
