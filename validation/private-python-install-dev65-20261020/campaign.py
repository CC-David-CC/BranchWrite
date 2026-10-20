from pathlib import Path
import subprocess,os,sys,json,hashlib,time
root=Path(__file__).parent;repo=Path('/home/dflanag3/src/branchwrite-documents-20261020');sys.path.insert(0,str(repo/'tools'))
from install_private_client import copy_standalone_python,snapshot
from verify_client_wheel import PROBE
report=dict(status='RUNNING',phase='copy-owned-source',started=time.time())
def save(): (root/'result.json').write_text(json.dumps(report,indent=2)+'\n')
save()
try:
 source,source_receipt=copy_standalone_python(Path('/home/dflanag3/.local/share/uv/python/cpython-3.12.15-linux-x86_64-gnu/bin/python3.12'),root/'owned-source-python')
 report['source_copy']=source_receipt;report['phase']='install';save()
 wheel=next((root/'wheels').glob('*.whl'));uv='/home/dflanag3/spatial-artifacts/bw-build123d-20261020/bootstrap/bin/uv'
 env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'}
 command=[sys.executable,'-B',str(repo/'tools/install_private_client.py'),'--source-python',str(source),'--uv',uv,'--wheel',str(wheel),'--dest',str(root/'release')]
 p=subprocess.run(command,env=env,capture_output=True,text=True,timeout=240);(root/'install.txt').write_text(p.stdout+p.stderr);p.check_returncode()
 report['phase']='installed-tools';save()
 old=snapshot(root/'owned-source-python');work=root/'probe';work.mkdir()
 mutate="import subprocess;subprocess.run(["+repr(str(source))+",'-I','-B','-c',\"import py_compile,sys;from pathlib import Path;p=Path(sys.base_prefix)/'lib/python3.12/compileall.py';py_compile.compile(str(p),doraise=True)\"],check=True)\n"
 probe=PROBE.replace('helper_env=dict(os.environ)',mutate+'helper_env=dict(os.environ)')
 p=subprocess.run([str(root/'release/venv/bin/python'),'-I','-B','-c',probe],cwd=work,env=env,capture_output=True,text=True,timeout=120)
 (root/'probe.stdout').write_text(p.stdout);(root/'probe.stderr').write_text(p.stderr);p.check_returncode();observed=json.loads(p.stdout)
 new=snapshot(root/'owned-source-python')
 if new==old:raise ValueError('external cache mutation did not actually happen')
 install=json.loads((root/'release/install-receipt.json').read_text())
 if Path(install['runtime']['base']).resolve()!=(root/'release/python').resolve():raise ValueError('wrong installed Python base')
 report.update(status='PASS',phase='COMPLETE',source_base_changed=True,source_before_sha256=hashlib.sha256(json.dumps(old).encode()).hexdigest(),source_after_sha256=hashlib.sha256(json.dumps(new).encode()).hexdigest(),installed_probe=observed,installation=install,scope='new wheel, default dependencies, isolated real shell/file/PDF build and page render; full runtime guard survives an actual cache addition in its disposable original Python; no GPU inference')
except BaseException as error:report.update(status='FAIL',error=repr(error));save();raise
finally:report['finished']=time.time();save()
print(json.dumps(report))
