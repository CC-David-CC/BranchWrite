from pathlib import Path
import subprocess,time,json
b=Path('/home/dflanag3/spatial-artifacts/branchwrite-SC14-repository-scope-dev15-20261019-v1');key=b/'ssh'
while not (b/'command.exit').exists():time.sleep(1)
argv=['ssh','-o','BatchMode=yes','-o','IdentitiesOnly=yes','-o','StrictHostKeyChecking=yes','-o','HostKeyAlias=bw-llm60','-o','UserKnownHostsFile='+str(key/'known_hosts'),'-i',str(key/'id_ed25519'),'dflanag3@llm-60','stop-owned-campaign']
p=subprocess.run(argv,capture_output=True,text=True,timeout=30);(b/'automatic-stop.json').write_text(json.dumps(dict(exit_code=p.returncode,stderr=p.stderr)))
if p.returncode:raise SystemExit(p.returncode)
for name in ['credentials.json','id_ed25519','id_ed25519.pub']:
 for folder in [key]:(folder/name).unlink(missing_ok=True)
(b/'secret-retirement.json').write_text(json.dumps(dict(credentials_removed=True,private_key_removed=True)))
