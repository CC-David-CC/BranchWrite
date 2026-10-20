#!/usr/bin/env python3
"""One-shot, owner-authorized replacement monitor; no installer or model runs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import time
import importlib.util


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifacts',type=Path,required=True)
    parser.add_argument('--vm-root',type=Path,required=True)
    parser.add_argument('--current-sha256',required=True)
    args=parser.parse_args();os.umask(0o077)
    base=args.artifacts.resolve(strict=True);root=args.vm_root.resolve(strict=True)
    spec=importlib.util.spec_from_file_location('vm_helper',base/'admin_vm.py')
    vm=importlib.util.module_from_spec(spec);spec.loader.exec_module(vm)
    options=['-o','BatchMode=yes','-o','ConnectTimeout=10','-o','StrictHostKeyChecking=yes',
        '-o','UserKnownHostsFile='+str(base/'transfer_known_hosts'),'-o','IdentitiesOnly=yes',
        '-i',str(Path.home()/'.ssh/id_ed25519_codi_fleet')]
    host='dflanag3@10.0.7.87'
    inventory="from pathlib import Path; import json; print(json.dumps([dict(path=str(p),size=p.stat().st_size,mtime=p.stat().st_mtime_ns,inode=p.stat().st_ino) for p in Path('/home/dflanag3/Desktop').glob('*.iso') if p.is_file() and not p.is_symlink()]))"
    def remote(code):
        p=subprocess.run(['ssh',*options,host,'python3 -c '+shlex.quote(code)],capture_output=True,text=True,timeout=60)
        p.check_returncode();return json.loads(p.stdout)
    def status(phase,**values):
        vm.save(base/'iso-watch-status.json',dict(phase=phase,updated_at=time.time(),pid=os.getpid(),**values))
    observed={};ignored=set();switching=False;deadline=time.monotonic()+6*3600
    status('watching',scope='New/replaced desktop ISO; verify then boot once with UEFI. Guest installation remains unrun.')
    while time.monotonic()<deadline:
        try:
            rows=remote(inventory)
            for row in sorted(rows,key=lambda r:r['mtime'],reverse=True):
                identity=(row['path'],row['size'],row['mtime'],row['inode'])
                if row['size']<=0 or identity in ignored:continue
                since=observed.setdefault(identity,time.monotonic())
                if time.monotonic()-since<60:continue
                path=row['path']
                # The sidecar is an additional completed-build check when present.
                code="from pathlib import Path; import hashlib,json; p=Path("+repr(path)+"); s=p.with_suffix('.sha256'); f=p.open('rb'); print(json.dumps(dict(sha256=hashlib.file_digest(f,'sha256').hexdigest(),sidecar=s.read_text().split()[0] if s.exists() else None)))"
                source=remote(code)
                digest=source['sha256']
                if source['sidecar'] is not None and source['sidecar']!=digest:
                    status('waiting-for-build-checksum',path=path);continue
                if digest==args.current_sha256:ignored.add(identity);continue
                status('copying',path=path,sha256=digest)
                partial=base/('replacement-'+digest[:12]+'.iso.part')
                final=partial.with_suffix('')
                if not final.exists():
                    partial.unlink(missing_ok=True)
                    transfer=subprocess.run(['scp',*options,host+':'+path,str(partial)],capture_output=True,text=True,timeout=600)
                    transfer.check_returncode()
                    with partial.open('rb') as stream:actual=hashlib.file_digest(stream,'sha256').hexdigest()
                    if actual!=digest:raise RuntimeError('Replacement copy checksum mismatch')
                    after=remote(inventory)
                    if row not in after:raise RuntimeError('Source changed during transfer; retain current VM')
                    partial.rename(final)
                with final.open('rb') as stream:
                    if hashlib.file_digest(stream,'sha256').hexdigest()!=digest:
                        raise RuntimeError('Retained replacement bytes changed')
                switching=True
                status('switching',path=str(final),sha256=digest)
                previous=json.loads((root/'launch.json').read_text())
                vm.save(base/('prior-launch-'+str(previous['pid'])+'.json'),previous)
                q=vm.QMP(root/'qmp.sock')
                if q.call('query-name').get('name')!=json.loads((root/'config.json').read_text())['name']:
                    raise RuntimeError('VM ownership changed; refusing switch')
                q.call('system_powerdown');q.close()
                for attempt in range(30):
                    time.sleep(1)
                    try:
                        q=vm.QMP(root/'qmp.sock');q.close()
                    except (FileNotFoundError,ConnectionRefusedError):break
                else:raise RuntimeError('Guest did not shut down cleanly; manual review required')
                p=subprocess.run(['python3',str(base/'admin_vm.py'),'start','--root',str(root),'--firmware','uefi','--iso',str(final)],capture_output=True,text=True,timeout=30)
                p.check_returncode()
                vm.save(base/('replacement-launch-'+digest[:12]+'.json'),json.loads(p.stdout))
                status('replacement-booted',path=str(final),sha256=digest,firmware='uefi',guest_ssh='NOT_YET_RETESTED',installation='NOT_RUN')
                return 0
            status('watching',candidates=len(rows),ignored_unchanged=len(ignored))
        except Exception as error:
            status('needs-review',error=type(error).__name__+': '+str(error)[:1200])
            # After a switch starts, never cycle or repeat an uncertain effect.
            if switching:return 1
        time.sleep(30)
    status('watch-expired',hours=6)
    return 2


if __name__=='__main__':
    raise SystemExit(main())
