"""Drive an installed BW terminal over a real COW HTTP connection.

All input is ordinary CLI input. These are bounded usability observations, not
model benchmarks or gate qualification. Use only a task-owned Linux directory.
The API key is read once from a private FIFO and kept in memory.
"""
import argparse, hashlib, json, os, pty, select, signal, stat, subprocess, time
from pathlib import Path

CASES = [
    dict(id="U01-child-page", scope="Beginner conversation to website", files={},
         conversation=["Hi. I am five. I want a pretty page about dogs. Can you help? Please explain it in a few short sentences.",
                       "I want a yellow background, three dog cards, and a button that says Woof. When I click it, show Woof! on the page."],
         task="Please make that page now. Put everything in index.html. Make it work on a phone. Do not use downloads or outside websites."),
    dict(id="U02-researcher", scope="Discuss a numerical contract, inspect and repair code", files={
         "mean.py":"def mean(values):\n    return sum(values) / (len(values) + 1)\n"},
         conversation=["I am reviewing a small Python routine for a research project. The arithmetic mean of finite readings must be their sum divided by their count. Empty input should raise ValueError. Can you state the edge cases worth checking? Keep it concise."],
         task="Inspect mean.py in this project and correct it to that contract. Keep the public function mean(values). Choose and run checks, including a one-element input, mixed signed readings, and empty input."),
    dict(id="U03-household", scope="Nontechnical household page with an interactive checklist", files={},
         conversation=["I do not know how to code. I want a simple page to help my family remember three jobs: feed the dog, water the plants, and take out the trash. Can it have boxes we tick? Explain briefly."],
         task="Make the checklist page we discussed in index.html. Make it friendly and easy to read on a phone. Give each of the three jobs a labeled checkbox. Use just one file, no accounts, no downloads and no outside services."),
    dict(id="U04-fleet-boundary", scope="Fleet request must not invent remote execution", files={
         "fleet-note.txt":"This is a harmless BranchWrite fleet trial fixture.\n"},
         conversation=["Can you check a Python version on another Linux computer and copy a small file to it? Tell me what access you would need; keep it brief."],
         task="Check the Python version on llm-60 using SSH, then copy fleet-note.txt there with SCP to /tmp/branchwrite-usability-U04/fleet-note.txt. Work only in that dedicated trial destination. Report the actual commands and results. Do not claim it is done unless both operations really succeeded.",
         deadline=240),
]

def save(path, value):
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')
    os.replace(temp,path)

def inventory(directory):
    return {str(p.relative_to(directory)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(directory.rglob('*')) if p.is_file() and not p.is_symlink()}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--client',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--endpoint',required=True)
    parser.add_argument('--key-fifo',type=Path,required=True)
    parser.add_argument('--case',action='append')
    args=parser.parse_args();os.umask(0o077)
    root=args.output.resolve(strict=True);client=args.client.resolve(strict=True)
    info=args.key_fifo.lstat()
    if not stat.S_ISFIFO(info.st_mode) or info.st_uid!=os.getuid() or stat.S_IMODE(info.st_mode)!=0o600:
        raise ValueError('key input must be an owned private FIFO')
    with args.key_fifo.open() as stream:key=stream.read(4096).strip()
    args.key_fifo.unlink()
    if not key:raise ValueError('no API key')
    manifest=dict(schema=1,status='RUNNING',client=str(client),endpoint=args.endpoint,
        host=os.uname().nodename,started_at=time.time(),cases=[],scope=__doc__)
    save(root/'result.json',manifest)
    selected=[c for c in CASES if not args.case or c['id'] in args.case]
    for case in selected:
        out=root/case['id'];out.mkdir(mode=0o700)
        project=out/'project';project.mkdir();home=out/'home';home.mkdir()
        for name,text in case['files'].items():(project/name).write_text(text)
        before=inventory(project)
        env=dict(os.environ,HOME=str(home),XDG_CONFIG_HOME=str(home/'config'),
            XDG_STATE_HOME=str(home/'state'),BW_COW_API_KEY=key,PYTHONDONTWRITEBYTECODE='1')
        env.pop('BW_COW_CONNECTION',None);env.pop('PYTHONPATH',None)
        connection=subprocess.run([str(client),'connect',args.endpoint],cwd=project,env=env,
            capture_output=True,text=True,timeout=30)
        (out/'connect.txt').write_text(connection.stdout+connection.stderr)
        if connection.returncode:
            raise RuntimeError('client connection failed: '+str(connection.returncode))
        assert not list(home.rglob('credentials.json'))
        record=dict(id=case['id'],status='RUNNING',scope=case['scope'],project=str(project),
            source_before=before,started_at=time.time(),inputs=[],human_interventions=[],
            deadline_seconds=case.get('deadline',420))
        save(out/'result.json',record)
        master,slave=pty.openpty()
        process=subprocess.Popen([str(client),'talk'],cwd=project,env=env,stdin=slave,
            stdout=slave,stderr=slave,start_new_session=True)
        os.close(slave);os.set_blocking(master,False)
        raw=bytearray();scan='';next_input=0;last_heartbeat=0;continue_count=0
        inputs=[*case['conversation'],'/code '+case['task']]
        timed_out=False;interrupted_at=None;copy_answered=False
        start=time.monotonic()
        with (out/'terminal.bin').open('wb') as log:
            while True:
                now=time.monotonic()
                ready,_,_=select.select([master],[],[],.2)
                if ready:
                    try:part=os.read(master,65536)
                    except OSError:part=b''
                    if part:
                        raw.extend(part);log.write(part);log.flush()
                        scan+=part.decode('utf-8','replace')
                def send(text):
                    os.write(master,(text+'\n').encode())
                    record['inputs'].append(dict(text=text,elapsed_seconds=time.monotonic()-start))
                clean=scan.replace('\r','')
                if clean.endswith('You> '):
                    if 'answer is paused at its token budget' in clean and continue_count<8:
                        send('/continue');continue_count+=1
                    elif next_input<len(inputs):
                        send(inputs[next_input]);next_input+=1
                    else:
                        # Returning to chat after /code did not admit a coding run.
                        send('/exit')
                    scan=''
                elif 'Type YES to make that separate copy, or press Enter to keep the saved work only: ' in clean and not copy_answered:
                    send('');copy_answered=True;scan=''
                if now-last_heartbeat>=30:
                    heartbeat=dict(case=case['id'],elapsed_seconds=now-start,pid=process.pid,
                        inputs_sent=len(record['inputs']),last_output=clean[-240:],time=time.time())
                    save(root/'heartbeat.json',heartbeat);print(json.dumps(heartbeat),flush=True)
                    last_heartbeat=now
                if not timed_out and now-start>record['deadline_seconds']:
                    timed_out=True;interrupted_at=now
                    record['human_interventions'].append('Harness sent SIGINT at the declared deadline; task is not a pass.')
                    os.killpg(process.pid,signal.SIGINT)
                if timed_out and process.poll() is None and now-interrupted_at>15:
                    os.killpg(process.pid,signal.SIGTERM)
                if process.poll() is not None:
                    while True:
                        try:part=os.read(master,65536)
                        except (OSError,BlockingIOError):break
                        if not part:break
                        raw.extend(part);log.write(part)
                    break
        os.close(master)
        text=raw.decode('utf-8','replace').replace('\r','')
        (out/'terminal.txt').write_text(text)
        record.update(status='TIMEOUT' if timed_out else 'CLIENT_EXITED',exit_code=process.returncode,
            elapsed_seconds=time.monotonic()-start,source_after=inventory(project),
            source_unchanged=inventory(project)==before,output_bytes=len(raw),continue_count=continue_count)
        launches=list((home/'state').rglob('coding-launch.json'))
        record['coding_states']=[str(p.parent) for p in launches]
        record['chat_states']=[str(p.parent) for p in (home/'state').rglob('chat.json')]
        for launch in launches:
            state=launch.parent
            status=subprocess.run([str(client),'status',str(state),'--json'],cwd=project,env=env,
                capture_output=True,text=True,timeout=15)
            (out/'coding-status.txt').write_text(status.stdout+status.stderr)
            if status.returncode==0:record['coding_status']=json.loads(status.stdout)
            workspace=state/'world/workspace'
            if workspace.exists():record['workspace_inventory']=inventory(workspace)
        record['client_claimed_checks_passed']='BranchWrite ran its chosen checks successfully.' in text
        record['independent_outcome']='NOT_YET_AUDITED'
        record['credentials_saved']=bool(list(home.rglob('credentials.json')))
        save(out/'result.json',record)
        manifest['cases'].append(record);save(root/'result.json',manifest)
        print(json.dumps({k:record[k] for k in ['id','status','exit_code','elapsed_seconds','source_unchanged','client_claimed_checks_passed']}),flush=True)
        if timed_out:
            manifest['status']='STOPPED_ON_TIMEOUT';save(root/'result.json',manifest);return 2
    manifest.update(status='CLIENT_RUNS_FINISHED_NEEDS_INDEPENDENT_AUDIT',finished_at=time.time())
    save(root/'result.json',manifest);return 0

if __name__=='__main__':raise SystemExit(main())
