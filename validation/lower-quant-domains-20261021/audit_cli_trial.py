
"""Audit actual CLI artifacts and settled image calls; independent of candidate code."""
from pathlib import Path
import argparse,hashlib,json,math,os,subprocess,traceback
from branchwrite.records import RuntimeLog,Artifact,decode
from branchwrite.kernel import FrameKernel

def rotation_angle(a,b):
 def unit_columns(m):
  columns=[[m[row][col] for row in range(3)] for col in range(3)]
  return [[v/math.sqrt(sum(x*x for x in c)) for v in c] for c in columns]
 x,y=unit_columns(a),unit_columns(b)
 trace=sum(sum(a*b for a,b in zip(c,d)) for c,d in zip(x,y))
 return math.degrees(math.acos(max(-1,min(1,(trace-1)/2))))

def scene_motion(scene):
 samples=scene['sampled_transforms'];first={x['name']:x['matrix'] for x in samples['1']};last={x['name']:x['matrix'] for x in samples['24']}
 assert first.keys()==last.keys(),'mesh identities changed'
 rows=[]
 for name,a in first.items():
  b=last[name];delta=max(abs(a[i][j]-b[i][j]) for i in range(4) for j in range(4))
  rows.append(dict(name=name,max_matrix_delta=delta,angle_degrees=rotation_angle(a,b)))
 moving=[x for x in rows if x['max_matrix_delta']>1e-6]
 assert len(moving)==1,('exactly one moving mesh required',moving)
 assert abs(moving[0]['angle_degrees']-45)<1e-3,('45-degree arm requirement',moving)
 return rows

def collect(trial):
 record=json.loads((trial/'result.json').read_text());cli=record['client_result']
 assert record['status']=='CLI_REPORTED_COMPLETE_PENDING_AUDIT' and cli['verified'] is True and cli['status']=='complete'
 root=trial/'state';accepted=trial/'accepted';accepted.mkdir(mode=0o700,exist_ok=True)
 tools=[];sent={};models=0;model_keys=[]
 with RuntimeLog(root/'ledger',read_only=True) as log:
  kernel=FrameKernel(log)
  for frame in kernel.frames():
   if frame['state']!='Closed':continue
   if frame['contract']==('ToolOutcome','record'):
    value=decode(log.read_artifact(Artifact(*frame['result'])))[2];tools.append(value)
   if frame['contract']==('ModelOutput','record'):
    models+=1;value=decode(log.read_artifact(Artifact(*frame['result'])));model_keys.append(list(value) if isinstance(value,dict) else str(type(value)))
   try:request=decode(log.read_artifact(Artifact(*frame['inputs'])))
   except (ValueError,TypeError,KeyError):continue
   if isinstance(request,dict) and request.get('kind')=='bw.model-native-request':
    body=json.loads(request['body']);content=body.get('content',[])
    if isinstance(content,list):
     for part in content:
      if part.get('type')=='image':sent.setdefault(part['image_id'],[]).append(frame['id'])
  exports={}
  for item in cli.get('exports',[]):
   name=item['name'];assert Path(name).name==name and name not in exports
   raw=log.read_artifact(Artifact(item['sha256'],item['bytes']));assert hashlib.sha256(raw).hexdigest()==item['sha256'];(accepted/name).write_bytes(raw);exports[name]=dict(sha256=item['sha256'],bytes=len(raw))
 workspace=root/'world/workspace'
 for name in ['index.html','model.py','scene.py','report.py','make_report.py']:
  if (workspace/name).is_file() and name not in exports:(accepted/name).write_bytes((workspace/name).read_bytes())
 report=dict(status='AUTOMATED_PASS_PENDING_VISUAL_REVIEW',variant=record['variant'],domain=record['domain'],elapsed_seconds=record['elapsed_seconds'],operator_candidate_edits=0,exports=exports,model_frames=models,model_output_keys=model_keys,tools=[{k:x.get(k) for k in ['tool','disposition','exit_code','operation_id']} for x in tools],native_image_requests=sent)
 return report,tools,sent,accepted

def audit(trial,root,source):
 report,tools,sent,accepted=collect(trial);domain=report['domain']
 if domain=='cad':
  successful=[x for x in tools if x['tool']=='inspect_cad' and x['disposition']=='cad_checked'];assert successful
  last=successful[-1];assert last.get('image') and last['image'][0] in sent,'actual current CAD view absent from settled native requests'
  from branchwrite.cad_config import load_cad_config
  from branchwrite.cad_execution import evaluate_candidate
  cap=load_cad_config(json.loads((root/'cad-config.json').read_text()))
  checked=evaluate_candidate((accepted/'part.step').read_bytes(),cap.requirements,cap.runtime)
  assets=checked.pop('assets',{});assert checked['status']=='PASS',checked
  report['independent_geometry']=checked
 elif domain=='pdf':
  from pypdf import PdfReader
  doc=PdfReader(str(accepted/'report.pdf'));assert len(doc.pages)==2
  texts=[page.extract_text() for page in doc.pages];combined='\n'.join(texts).lower()
  for needle in ['daily care','a safe home','food','water','walk','rest','veterinar']:assert needle in combined,needle
  builds=[i for i,x in enumerate(tools) if x['tool']=='build_pdf' and x['disposition']=='pdf_built'];assert builds
  images={}
  for x in tools[builds[-1]:]:
   if x['tool'] in ('build_pdf','render_pdf') and x.get('image'):images[x['details']['page']]=x['image'][0]
  assert set(images)=={1,2},images
  assert all(digest in sent for digest in images.values()),'a current PDF page was not sent to model'
  report['pdf']=dict(pages=2,text=texts,images=images)
 elif domain=='blender':
  checks=[x for x in tools if x['tool']=='inspect_scene' and x['disposition']=='scene_checked'];assert checks
  last=checks[-1];assert last.get('image') and last['image'][0] in sent,'actual Blender view missing'
  scene=last['details']['scene'];report['motion']=scene_motion(scene)
  report['scene']=scene
  # Actual video bytes go directly to the owned VM and an anonymous RAM file.
  import shlex
  remote="import os,sys,subprocess;fd=os.memfd_create('bw-video-audit',0);body=sys.stdin.buffer.read();assert len(body)<33554432;os.write(fd,body);p=subprocess.run(['ffprobe','-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=codec_name,width,height,r_frame_rate,nb_read_frames','-of','json','/proc/self/fd/'+str(fd)],pass_fds=(fd,),capture_output=True);sys.stdout.buffer.write(p.stdout);sys.stderr.buffer.write(p.stderr);sys.exit(p.returncode)"
  cmd=['ssh','-i','/home/dflanag3/.local/share/bw-vm/admin01/guest-key','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile=/home/dflanag3/.local/share/bw-vm/admin01/known_hosts-a432129ef6d1','-p','22220','maint@127.0.0.1','python3 -c '+shlex.quote(remote)]
  p=subprocess.run(cmd,input=(accepted/'animation.mp4').read_bytes(),capture_output=True,timeout=60,check=True);video=json.loads(p.stdout);stream=video['streams'][0]
  assert int(stream['nb_read_frames'])==24 and stream['r_frame_rate']=='12/1' and stream['codec_name']=='h264',video
  report['video']=video
 elif domain=='code':
  from branchwrite.browser_capture import BrowserConfig,PageInspection,render_snapshot
  raw=(accepted/'index.html').read_bytes();checker=source/'validation/cli-code-q4-20261020/website_checks.py';inspection=PageInspection(checker,hashlib.sha256(checker.read_bytes()).hexdigest(),'custom')
  chrome=Path('/home/dflanag3/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome');rows=[]
  for name,w,h in [('desktop',1280,800),('phone',375,812)]:
   result=render_snapshot(raw,BrowserConfig(chrome,w,h,30,inspection=inspection));(accepted/(name+'.png')).write_bytes(result.png)
   assert result.inspection['status']=='PASS' and not result.runtime_errors,(result.inspection,result.runtime_errors)
   assert result.served_sha256==hashlib.sha256(raw).hexdigest()
   rows.append(dict(viewport=name,inspection=result.inspection,runtime_errors=result.runtime_errors,served_sha256=result.served_sha256,isolation=result.isolation))
  report['browser']=rows
 else:raise ValueError('unknown domain')
 return report

def main():
 parser=argparse.ArgumentParser();parser.add_argument('trial',type=Path);parser.add_argument('--root',type=Path,required=True);parser.add_argument('--source',type=Path,required=True);args=parser.parse_args();out=args.trial/'audit.json'
 try:report=audit(args.trial,args.root,args.source)
 except Exception as e:report=dict(status='AUDIT_FAILED',error=repr(e),traceback=traceback.format_exc())
 out.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');print(json.dumps({k:v for k,v in report.items() if k in ['status','variant','domain','error']}))
 if report['status']=='AUDIT_FAILED':raise SystemExit(1)
if __name__=='__main__':main()
