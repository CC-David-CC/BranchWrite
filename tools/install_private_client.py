"""Initial Linux client setup with a release-owned standalone Python base.

A venv alone shares its standard library. Never use this installer to modify an
admitted runtime. It creates a new destination, verifies a real relocatable copy,
installs declared dependencies in copy mode, then makes runtime trees read-only.
"""
import argparse,hashlib,json,os,shutil,stat,subprocess,time
from pathlib import Path

def clean_environment():
 return dict(PATH='/usr/bin:/bin',HOME=str(Path.home()),LANG='C.UTF-8',PYTHONDONTWRITEBYTECODE='1')

def probe(python):
 code='import sys,json;print(json.dumps(dict(prefix=sys.prefix,base=sys.base_prefix,executable=sys.executable,base_executable=sys._base_executable,version=sys.version)))'
 p=subprocess.run([str(python),'-I','-B','-c',code],cwd='/',env=clean_environment(),capture_output=True,text=True,timeout=15,check=True)
 return json.loads(p.stdout)

def snapshot(root):
 rows=[]
 for p in [root,*sorted(root.rglob('*'))]:
  relative=str(p.relative_to(root));info=p.lstat()
  if p.is_symlink():value=('link',os.readlink(p))
  elif p.is_dir():value=('directory',)
  elif p.is_file():
   before=(info.st_ino,info.st_size,info.st_mtime_ns,info.st_ctime_ns)
   with p.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
   after=p.stat()
   if before!=(after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns):raise ValueError('Python source changed while copying')
   value=('file',digest,info.st_size)
  else:raise ValueError('unsupported object in standalone Python')
  rows.append((relative,stat.S_IMODE(info.st_mode),*value))
 return rows

def copy_standalone_python(source_python,target):
 target=Path(target).absolute()
 if target.exists() or target.is_symlink():raise FileExistsError(str(target))
 target=target.parent.resolve(strict=True)/target.name
 source_python=Path(source_python).absolute();observed=probe(source_python);base=Path(observed['base']).resolve(strict=True)
 if base in (Path('/'),Path('/usr'),Path('/usr/local')) or not (base/'bin').is_dir() or not (base/'lib').is_dir():
  raise ValueError('a relocatable standalone Python is required; never clone the system prefix')
 if target.is_relative_to(base):raise ValueError('standalone destination must be outside its source')
 for p in base.rglob('*'):
  if p.is_symlink() and (os.path.isabs(os.readlink(p)) or not p.resolve(strict=True).is_relative_to(base)):
   raise ValueError('standalone link is absolute or leaves its source')
 before=snapshot(base);shutil.copytree(base,target,symlinks=True)
 if snapshot(base)!=before or snapshot(target)!=before:raise ValueError('standalone copy differs or source changed')
 copied=target/'bin'/Path(observed['base_executable']).name
 actual=probe(copied)
 if Path(actual['base']).resolve()!=target.resolve() or actual['version']!=observed['version']:
  raise ValueError('copied standalone Python did not relocate')
 for p in target.rglob('*'):
  if p.is_symlink() and not p.resolve(strict=True).is_relative_to(target):raise ValueError('copied interpreter still depends on old source')
 return copied,dict(source_base=str(base),private_base=str(target),source_manifest_sha256=hashlib.sha256(json.dumps(before,separators=(',',':')).encode()).hexdigest(),files=len(before),bytes=sum(x[4] for x in before if x[2]=='file'),probe=actual)

def freeze_tree(root):
 paths=[root,*root.rglob('*')]
 for p in paths:
  if p.is_symlink():continue
  p.chmod(0o500 if p.is_dir() or p.stat().st_mode&0o111 else 0o400)

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source-python',type=Path,required=True);parser.add_argument('--uv',type=Path,required=True);parser.add_argument('--wheel',type=Path,required=True);parser.add_argument('--dest',type=Path,required=True);args=parser.parse_args()
 wheel=args.wheel.resolve(strict=True);uv=args.uv.resolve(strict=True);root=args.dest.absolute();root.mkdir(mode=0o700)
 report=dict(status='INSTALLING',started=time.time(),wheel_sha256=hashlib.sha256(wheel.read_bytes()).hexdigest(),uv_sha256=hashlib.sha256(uv.read_bytes()).hexdigest())
 def save():
  temp=root/'install-receipt.tmp';temp.write_text(json.dumps(report,indent=2)+'\n');temp.chmod(0o600);os.replace(temp,root/'install-receipt.json')
 save()
 try:
  python,receipt=copy_standalone_python(args.source_python,root/'python');report['python_copy']=receipt;save()
  env=clean_environment();env['UV_CACHE_DIR']=str(root/'cache')
  commands=[['venv','--python',str(python),str(root/'venv')],['pip','install','--link-mode','copy','--compile-bytecode','--python',str(root/'venv/bin/python'),str(wheel)]]
  for i,command in enumerate(commands):
   p=subprocess.run([str(uv),*command],cwd=root,env=env,capture_output=True,text=True,timeout=180)
   (root/('setup-'+str(i)+'.txt')).write_text(p.stdout+p.stderr)
   if p.returncode:raise RuntimeError('private setup step '+str(i)+' failed; see its retained log')
  observed=probe(root/'venv/bin/python')
  if Path(observed['base']).resolve()!=(root/'python').resolve():raise ValueError('installed venv still depends on another Python base')
  freeze_tree(root/'venv');freeze_tree(root/'python')
  report.update(status='INSTALLED_PRIVATE_RUNTIME',client=str(root/'venv/bin/branchwrite'),runtime=observed,scope='new initial installation; full Python/cache/package hashes remain enforced, no existing saved workflow migrated');save();print(json.dumps(report));return 0
 except BaseException as error:report.update(status='FAIL',error=repr(error));save();raise

if __name__=='__main__':raise SystemExit(main())
