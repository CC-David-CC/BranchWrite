"""Build a private installed candidate from an exact committed revision; no network."""
from pathlib import Path
import subprocess,hashlib,json,os,zipfile,sys
repo=Path(sys.argv[1]).resolve(strict=True);out=Path(sys.argv[2]).absolute()
assert not out.is_relative_to(repo),'build output must be outside source'
revision=subprocess.run(['git','-C',str(repo),'rev-parse','HEAD'],capture_output=True,text=True,check=True).stdout.strip()
assert not subprocess.run(['git','-C',str(repo),'status','--porcelain'],capture_output=True,text=True,check=True).stdout,'commit or preserve source changes first'
out.mkdir(mode=0o700,exist_ok=False);source=out/'source';source.mkdir();wheel=out/'wheel';wheel.mkdir()
archive=subprocess.Popen(['git','-C',str(repo),'archive',revision],stdout=subprocess.PIPE)
unpack=subprocess.run(['tar','-x','-C',str(source)],stdin=archive.stdout,capture_output=True,text=True);archive.stdout.close();assert archive.wait()==0;unpack.check_returncode()
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1');env.pop('PYTHONPATH',None)
def command(argv,name):
 r=subprocess.run(argv,capture_output=True,text=True,env=env,timeout=120);(out/name).write_text(r.stdout+r.stderr);r.check_returncode();return r
build_tools=json.loads(command([sys.executable,'-c','import json,setuptools,wheel;print(json.dumps(dict(setuptools=setuptools.__version__,wheel=wheel.__version__)))'],'build-tools.log').stdout)
command([sys.executable,'-m','pip','wheel','--no-index','--no-deps','--no-build-isolation','--wheel-dir',str(wheel),str(source)],'build.log')
command([sys.executable,'-m','venv',str(out/'venv')],'venv.log')
files=list(wheel.glob('*.whl'));assert len(files)==1;python=str(out/'venv/bin/python')
command([python,'-m','pip','install','--no-index','--no-deps',str(files[0])],'install.log')
r=command([python,'-I','-B','-c','import branchwrite;print(branchwrite.__file__)'],'import-proof.log');package=Path(r.stdout.strip()).parent
with zipfile.ZipFile(files[0]) as z:
 modules=[n for n in z.namelist() if n.startswith('branchwrite/') and n.endswith('.py')]
 assert all((package.parent/n).read_bytes()==z.read(n) for n in modules)
proof=dict(status='BUILT_INSTALLED_NOT_GPU_QUALIFIED',source_revision=revision,wheel=files[0].name,wheel_sha256=hashlib.sha256(files[0].read_bytes()).hexdigest(),build_tools=build_tools,installed_package=str(package),module_count=len(modules),all_wheel_module_bytes_match=True,builder_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
(out/'build-provenance.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof,indent=2))
