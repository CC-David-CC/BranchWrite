"""Build a fresh, private BW runtime, then atomically publish its launcher."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess

def publish_launcher(home, release, bindir):
    release=Path(release).resolve(strict=True) if Path(release).exists() else Path(release)
    executable=release/"venv/bin/branchwrite"
    if not executable.is_file() or not os.access(executable,os.X_OK):
        raise ValueError("The new release has no working BranchWrite executable.")
    bindir=Path(bindir)
    bindir.mkdir(parents=True,exist_ok=True)
    # Pin the absolute release in each launcher. Never change an admitted run's
    # interpreter by moving a venv or following a mutable 'current' link.
    text="#!/bin/sh\nexec "+shlex.quote(str(executable))+' "$@"\n'
    temporary=bindir/(".bw-"+str(os.getpid())+".tmp")
    temporary.write_text(text)
    temporary.chmod(0o700)
    os.replace(temporary,bindir/"bw")
    return bindir/"bw"

def run(argv, **kw):
    subprocess.run([str(x) for x in argv],check=True,**kw)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source",type=Path,required=True)
    parser.add_argument("--source-python",type=Path,required=True)
    parser.add_argument("--uv",type=Path,required=True)
    parser.add_argument("--home",type=Path,required=True)
    parser.add_argument("--bin",type=Path,required=True)
    args=parser.parse_args()
    source=args.source.resolve(strict=True)
    revision=subprocess.check_output(["git","-C",str(source),"rev-parse","HEAD"],text=True).strip()
    if len(revision)!=40 or any(c not in "0123456789abcdef" for c in revision):
        raise ValueError("Could not identify the downloaded source revision.")
    home=args.home.resolve()
    release=home/"releases"/revision
    (home/"releases").mkdir(parents=True,exist_ok=True)
    if release.exists():
        raise FileExistsError("This release already exists. Run "+str(args.bin/"bw")+
                              "; it will not be overwritten. Keep old releases for saved work.")
    wheels=home/"build"/revision
    wheels.mkdir(parents=True,exist_ok=False)
    env=dict(os.environ,UV_NO_CONFIG="1",UV_CACHE_DIR=str(home/"download-cache"),
             PYTHONDONTWRITEBYTECODE="1")
    run([args.uv,"build","--wheel","--python",args.source_python,
         "--out-dir",wheels,source],env=env)
    found=list(wheels.glob("branchwrite-*.whl"))
    if len(found)!=1: raise ValueError("Expected exactly one BranchWrite wheel.")
    run([args.source_python,"-I","-B",source/"tools/install_private_client.py",
         "--source-python",args.source_python,"--uv",args.uv,
         "--wheel",found[0],"--dest",release],env=env)
    run([release/"venv/bin/branchwrite","--help"],stdout=subprocess.DEVNULL,env=env)
    receipt=json.loads((release/"install-receipt.json").read_text())
    receipt.update(source_revision=revision,source_origin="https://github.com/CC-David-CC/BranchWrite",
                   wheel_sha256=hashlib.sha256(found[0].read_bytes()).hexdigest())
    tmp=release/"source-receipt.tmp"
    tmp.write_text(json.dumps(receipt,indent=2)+"\n")
    tmp.chmod(0o600)
    os.replace(tmp,release/"source-receipt.json")
    target=publish_launcher(home,release,args.bin)
    print("\nBranchWrite is installed.\nOpen your project folder, then run:\n  "+str(target))
    print("Keep the old releases folder: saved work may still use its runtime.")

if __name__=="__main__":main()
