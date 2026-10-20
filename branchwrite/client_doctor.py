"""Explicit client installation probe; no model, credentials or workflow journal."""
import json,tempfile
from pathlib import Path

def command():
    from .execution import Executor,Grant
    from .terminal import ShellConfig
    result=dict(status='FAIL',inference='NOT_RUN',scope='Client file creation and read-only shell isolation only; no server, browser or adversarial security qualification')
    try:
        with tempfile.TemporaryDirectory(prefix='branchwrite-doctor-') as directory:
            root=Path(directory);source=root/'source';source.mkdir()
            literal='snow ? $HOME\n'.encode()
            (source/'note.txt').write_bytes(literal)
            executor=Executor.create(source,root/'world',shell=ShellConfig(timeout=3))
            grant=Grant((),False,read_paths=('note.txt','new.txt'),create_paths=('new.txt',),allow_shell=True)
            created=executor.create_file('doctor-create',grant,'new.txt',b'created\n')
            observed=executor.run_shell('doctor-shell',grant,'cat note.txt new.txt')
            checks=dict(literal_bytes=observed.stdout.read_bytes()==literal+b'created\n',original_unchanged=not (source/'new.txt').exists() and (source/'note.txt').read_bytes()==literal,created=created.disposition=='created',shell_exit=observed.exit_code==0)
            isolation=observed.details['isolation']
            result.update(checks=checks,isolation=isolation)
            if not all(checks.values()) or not isolation['worker_exited'] or isolation['namespace_members_after']:
                raise ValueError('client probe failed its output or retirement checks')
            result['status']='PASS'
    except (OSError,ValueError,RuntimeError) as exc:
        result['error']=str(exc)[:512]
    print(json.dumps(result,sort_keys=True));return 0 if result['status']=='PASS' else 2
