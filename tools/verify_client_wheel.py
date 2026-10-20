"""Verify an owned client wheel in a new Linux environment, without source imports."""
import argparse,hashlib,json,os,subprocess,sys,zipfile
from pathlib import Path
PROBE=r'''from pathlib import Path
import json,sys,hashlib
from branchwrite.coding_defaults import workflow_source,system_prefix
from branchwrite.execution import Executor,Grant
from branchwrite.terminal import ShellConfig
root=Path.cwd();source=root/"tool-source";source.mkdir()
(source/"note.txt").write_text("snow 雪 $HOME\n")
executor=Executor.create(source,root/"tool-world",shell=ShellConfig(timeout=3))
grant=Grant((),False,read_paths=("note.txt","new.txt"),create_paths=("new.txt",),allow_shell=True)
created=executor.create_file("installed-create",grant,"new.txt",b"created\n")
result=executor.run_shell("installed-shell",grant,"cat note.txt new.txt")
assert result.exit_code==0,result.stderr.read_bytes()
assert result.stdout.read_bytes()=="snow 雪 $HOME\ncreated\n".encode()
assert not (source/"new.txt").exists()
assert (executor.workspace/"new.txt").read_bytes()==b"created\n"
assert result.details["isolation"]["worker_exited"] and result.details["isolation"]["namespace_members_after"]==[]
from branchwrite.pdf_execution import PdfRuntime,build_document,inspect_document
runtime=PdfRuntime()
source=b"from reportlab.pdfgen import canvas\nc=canvas.Canvas('document.pdf',invariant=1)\nc.drawString(54,730,'Installed PDF support')\nc.save()\n"
built=build_document((('report.py',source),),'report.py',runtime)
assert built['disposition']=='built',built['stderr']
view=inspect_document(built['pdf'],1,runtime)
assert view['status']=='PASS' and view['page_count']==1 and 'Installed PDF support' in view['text']
assert view['image'].startswith(b'\x89PNG\r\n\x1a\n')
assert not built['isolation']['namespace_members_after'] and not view['isolation']['namespace_members_after']
import subprocess,os
helper_env=dict(os.environ);helper_env.pop('PYTHONDONTWRITEBYTECODE',None)
helper=subprocess.run([str(Path(sys.prefix)/'bin/branchwrite'),'--help'],capture_output=True,env=helper_env)
assert helper.returncode==0;runtime.check()
schema={"oneOf":[{"properties":{"tool":{"enum":["run_shell","create_text_file"]}}}]}
print(json.dumps(dict(status="PASS",python=sys.version.split()[0],module_path=__import__("branchwrite").__file__,workflow_sha256=hashlib.sha256(workflow_source().encode()).hexdigest(),prefix_sha256=hashlib.sha256(system_prefix(schema).encode()).hexdigest(),created=created.disposition,shell=result.disposition,isolation=result.details["isolation"],pdf=dict(pages=view["page_count"],bytes=len(built["pdf"]),sha256=hashlib.sha256(built["pdf"]).hexdigest(),actual_png_bytes=len(view["image"])),parallel_help_runtime_unchanged=True)))
'''
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wheel',type=Path,required=True)
    parser.add_argument('--work-dir',type=Path,required=True)
    parser.add_argument('--wheelhouse',type=Path,help='Optional complete offline directory of dependency wheels.')
    args=parser.parse_args()
    wheel=args.wheel.resolve(strict=True);work=args.work_dir.absolute()
    work.mkdir(mode=0o700)
    result=dict(status='RUNNING',wheel_sha256=hashlib.sha256(wheel.read_bytes()).hexdigest(),checks=[])
    def write(): (work/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def run(name,argv,env):
        p=subprocess.run(argv,cwd=work,env=env,capture_output=True,text=True,timeout=120)
        (work/(name+'.stdout')).write_text(p.stdout);(work/(name+'.stderr')).write_text(p.stderr)
        if p.returncode:raise RuntimeError(name+' failed with exit '+str(p.returncode))
        return p.stdout
    env=dict(PATH='/usr/bin:/bin',HOME=str(work),LANG='C.UTF-8',PYTHONDONTWRITEBYTECODE='1',PIP_DISABLE_PIP_VERSION_CHECK='1')
    try:
        with zipfile.ZipFile(wheel) as archive:
            names=archive.namelist()
            if any(n.startswith(('serve/','context_time_travel/','tests/','reference/')) for n in names):raise ValueError('wheel contains server or protected test modules')
            assets={name:hashlib.sha256(archive.read(name)).hexdigest() for name in names if name.startswith('branchwrite/_examples/')}
            if len(assets)!=5:raise ValueError('expected five canonical example assets')
        result['checks'].append(dict(id='wheel-boundary',status='PASS',assets=assets))
        run('venv',[sys.executable,'-m','venv',str(work/'venv')],env)
        python=str(work/'venv/bin/python')
        install=[python,'-m','pip','install']
        if args.wheelhouse is not None:install+=['--no-index','--find-links',str(args.wheelhouse.resolve(strict=True))]
        # Initial installation includes the declared PDF/UI dependencies. Never
        # make an apparently complete --no-deps installation the default.
        run('install',install+[str(wheel)],env)
        help_text=run('help',[str(work/'venv/bin/branchwrite'),'--help'],env)
        if 'code' not in help_text or 'resume' not in help_text:raise ValueError('console commands absent')
        result['checks'].append(dict(id='installed-console',status='PASS'))
        observed=json.loads(run('tools-and-assets',[python,'-I','-c',PROBE],env))
        if not Path(observed['module_path']).is_relative_to(work/'venv'):raise ValueError('client was imported outside the installed environment')
        result['checks'].append(dict(id='installed-tools-and-assets',status='PASS',observed=observed))
        result['status']='INSTALLED_CLIENT_CONTROL_PASS'
        result['scope']='Real Linux file creation/read-only sandbox, packaged assets, initial PDF dependencies/build/reopen/render and parallel-help integrity; no inference, new installed-agent GPU run, adversarial security certification or release qualification.'
        write();print(json.dumps(result,indent=2));return 0
    except BaseException as exc:
        result.update(status='FAIL',error=dict(type=type(exc).__name__,message=str(exc)));write();raise
if __name__=='__main__':raise SystemExit(main())
