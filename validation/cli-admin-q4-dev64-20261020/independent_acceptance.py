from pathlib import Path
import hashlib,json,subprocess,shlex
from branchwrite.records import RuntimeLog,Artifact,decode
from branchwrite.kernel import FrameKernel
root=Path(__file__).parent;d=json.loads((root/'admin-result.json').read_text());assert d['client_exit_code']==0
project=Path('/home/dflanag3/projects/bw-candidate-admin-dev63-20261020');raw=(project/'index.html').read_bytes();sha=hashlib.sha256(raw).hexdigest();target=json.loads((root/'operator-targets.json').read_text())['targets']['admin01']
# The task never required overwriting /. The original audit assumed that path.
# The actual recorded publication preserves it and serves the new /dogs/ site.
with RuntimeLog(Path(d['workflow'])/'ledger',read_only=True) as log:
 outcomes=[]
 for frame in FrameKernel(log).frames():
  if frame['state']=='Closed' and frame['contract']==('ToolOutcome','record'):
   value=decode(log.read_artifact(Artifact(*frame['result'])))[2];outcomes.append(value)
 assert any(v['tool']=='check_remote' and v['exit_code']==0 for v in outcomes)
 assert any(v['tool']=='run_check' and v['exit_code']!=0 for v in outcomes),'retain original missing-awk check'
 assert any(v['tool']=='run_check' and v['exit_code']==0 for v in outcomes)
 (root/'tool-outcomes.json').write_text(json.dumps(outcomes,indent=2)+'\n')
ssh=['ssh','-i',target['identity_file'],'-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+target['known_hosts_file'],'-p',str(target['port']),target['user']+'@'+target['host']]
code="import pathlib,urllib.request,json,hashlib; h=lambda b:hashlib.sha256(b).hexdigest(); p=pathlib.Path('/var/www/html/dogs/index.html'); up=pathlib.Path('/home/maint/.branchwrite-uploads/"+sha+"/index.html'); r=urllib.request.urlopen('http://127.0.0.1/dogs/',timeout=10); print(json.dumps(dict(published_path=str(p),url='http://127.0.0.1/dogs/',status=r.status,local_service_sha256=h(p.read_bytes()),http_sha256=h(r.read()),upload_sha256=h(up.read_bytes()),original_home_sha256=h(pathlib.Path('/var/www/html/index.html').read_bytes()),unrelated_sha256=h(pathlib.Path('/var/www/html/index.nginx-debian.html').read_bytes()))))"
p=subprocess.run(ssh+[shlex.join(['python3','-c',code])],capture_output=True,text=True,timeout=30);p.check_returncode();a=json.loads(p.stdout)
assert a['status']==200;assert a['local_service_sha256']==a['http_sha256']==a['upload_sha256']==sha
baseline='7682b434a69962f7fea2212f684ed8b99d4119297339caf4e2447edf8e7b5662';assert a['original_home_sha256']==a['unrelated_sha256']==baseline
report=dict(status='PASS',cli_exit=0,prompt_sha256=d['prompt_sha256'],source_sha256=sha,source_bytes=len(raw),independent_acceptance=a,checks_passed=True,operator_candidate_edits=0,elapsed_client_seconds=d['completed_seconds'],profile=d['context'],scope='actual installed dev64 CLI -> Q4 server -> pinned owned SSH VM -> exact upload/publication/HTTP; only guest-local URL reachability proven',original_audit='retained NEEDS_INSPECTION: incorrectly assumed root homepage would be overwritten; this independent audit checks the actual permitted /dogs/ deployment and both preserved original files')
(root/'independent-acceptance.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
