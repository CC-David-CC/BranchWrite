from pathlib import Path
import subprocess,json,sys,time
root=Path(__file__).parent;d=root/('coding-'+sys.argv[1]);python='/home/dflanag3/spatial-artifacts/branchwrite-dev19-package-20261019-v1/venv/bin/python'
f=json.loads((d/'workload.json').read_text());assert f['base_snapshot']
access=root/'client-access';assert (access/'credentials.json').exists()
argv=[python,'-B',str(root/'comparison-client-driver.py'),'--checkout','/home/dflanag3/src/branchwrite-model-reconciliation-20261019','--fixture',str(d/'workload.json'),'--state',str(d/'state'),'--credentials',str(access/'credentials.json'),'--ssh-key',str(access/'id_ed25519'),'--known-hosts',str(access/'known_hosts'),'--output',str(d/'output')]
with (d/'launch.stdout').open('x') as o,(d/'launch.stderr').open('x') as e:
 child=subprocess.Popen(argv,stdout=o,stderr=e)
 (d/'client.pid').write_text(str(child.pid));code=child.wait()
(d/'command.exit').write_text(str(code))
if code==0:
 with (d/'audit.stdout').open('x') as o,(d/'audit.stderr').open('x') as e:
  audited=subprocess.run([python,'-B',str(root/'audit-coding-output.py'),str(d)],stdout=o,stderr=e,timeout=90)
 (d/'audit.exit').write_text(str(audited.returncode))
 code=audited.returncode
raise SystemExit(code)
