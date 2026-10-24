"""Host-selected verified lessons; no model tool can approve its own training."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import uuid

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def digest(value):return hashlib.sha256(canonical(value)).hexdigest()

def _run_evidence(state,passed):
    from .coding_status import inspect_run
    from .records import RuntimeLog,Artifact,decode
    from .kernel import FrameKernel
    from .coding_cli import read_launch
    config=read_launch(state)['config']
    commands={row['command'] for row in config.get('verification',{}).get('commands',[])}
    summary=inspect_run(state)
    if summary['state']!='Closed' or (passed and summary['recorded_verified'] is not True) or summary['pending_operations']:
        raise ValueError('Select a settled run with recorded '+('passing' if passed else 'failing')+' checks')
    with RuntimeLog(Path(state)/'ledger',read_only=True) as log:
        kernel=FrameKernel(log);root=kernel.frame('program');checks=[];positions=[]
        returned={entry['event'].get('frame'):index for index,entry in enumerate(log.events) if entry['event']['kind']=='returned'}
        inputs=decode(log.read_artifact(Artifact(*root['inputs'])))
        config_hash=hashlib.sha256(json.dumps(config,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()
        if inputs.get('bindings',{}).get('host-config-sha256')!=('Text',config_hash):raise ValueError('Run configuration differs from its canonical input')
        for frame in kernel.frames():
            if frame['state']!='Closed' or frame['contract']!=('ToolOutcome','record'):continue
            result=decode(log.read_artifact(Artifact(*frame['result'])))[2]
            plan=decode(log.read_artifact(Artifact(*frame['inputs'])))
            tool=result.get('tool')
            eligible=tool=='run_tests' or (tool=='run_check' and config.get('verification',{}).get('selected_checks') is True)
            if tool=='run_shell' and isinstance(plan,tuple) and len(plan)==8:
                eligible=plan[4].get('command') in commands
            if (eligible and result.get('disposition')=='exited'
                    and type(result.get('exit_code')) is int and 0<=result['exit_code']<126 and (result['exit_code']==0) is passed):
                checks.append(frame['result'])
                positions.append(returned[frame['id']])
        if not checks:raise ValueError('An actual completed host test result is required; infrastructure errors are not lessons')
        return dict(result_sha256=root['result'][0] if passed else checks[-1][0],checks=checks,check_positions=positions,
                    program_sha256=root['definition'][0],model_contract_id=config['cow']['model_contract_id'])

def create_lesson(failed_state,corrected_state,prompt,completion,title,rationale,model_contract_id):
    from .coding_review import inspect_changes
    failed=_run_evidence(failed_state,False)
    corrected=_run_evidence(corrected_state,True)
    if Path(failed_state).resolve()==Path(corrected_state).resolve() and max(failed['check_positions'])>=max(corrected['check_positions']):
        raise ValueError('Correction must have passing checks after the recorded failure')
    if failed['model_contract_id']!=model_contract_id or corrected['model_contract_id']!=model_contract_id:
        raise ValueError('Selected BW runs belong to another model')
    review=inspect_changes(corrected_state)  # Includes current inventory/drift validation.
    if not prompt.strip() or not completion.strip():raise ValueError('Write explicit teaching input and checked completion')
    return dict(schema=1,title=title,model_contract_id=model_contract_id,prompt=prompt,completion=completion,
        rationale=rationale,scope='owned-training',evidence=dict(method='bw-verified-correction-v1',
        failed_result_sha256=failed['result_sha256'],corrected_result_sha256=corrected['result_sha256'],
        verification_sha256=digest(dict(failed=failed,corrected=corrected,review=review))))

def _client(args,connection_override=None):
    from .client_setup import connection_path,read_connection,key_for_connection
    from .cow_client import CowClient,OperationJournal
    connection=(connection_override if connection_override is not None and args.connection is None else read_connection(args.connection or connection_path()))
    state=Path(args.state_dir or Path(os.environ.get('XDG_STATE_HOME',Path.home()/'.local/state'))/'branchwrite/training-requests')
    return connection,CowClient.http(connection['endpoint_url'],api_key=key_for_connection(connection),
        endpoint_pin=connection['endpoint_pin'],journal=OperationJournal(state))

def _submit_training(client,args,identity,ids,*,single=False,steps=None):
    guarded=args.skill_guard
    payload=dict(lesson_ids=ids,mode=args.mode,batch_size=args.batch_size if guarded or not single else 1,
        steps=(args.steps if args.steps is not None else 16) if guarded else (1 if single else steps),
        learning_rate=args.learning_rate,rank=args.rank,parent_job_id=args.parent_job_id)
    if args.optimizer_profile_id is not None:
        payload['optimizer_profile_id']=args.optimizer_profile_id
        if single and args.steps is not None:payload['steps']=args.steps
    if guarded:
        record=client.journal.read(identity)
        prior=json.loads(client.journal.decode_body(record)) if record is not None and record['path']=='/cow/training/jobs' else None
        payload['skill_guard']=prior['skill_guard'] if prior is not None and 'skill_guard' in prior else dict(policy_id=client.training_read('skills')['policy_id'])
    return client.training_submit('jobs',payload,identity)

def main(argv=None,*,output=print,connection_override=None,session_history=None):
    parser=argparse.ArgumentParser(prog='branchwrite lesson',description='Write checked lessons, queue them, and request native training candidates.')
    parser.add_argument('--connection',type=Path);parser.add_argument('--state-dir',type=Path)
    subs=parser.add_subparsers(dest='action',required=True)
    p=subs.add_parser('create',help='Write a private teaching example bound to failed/passing BW runs.')
    failed=p.add_mutually_exclusive_group();failed.add_argument('--failed-state',type=Path);failed.add_argument('--failed-turn',type=int)
    corrected=p.add_mutually_exclusive_group();corrected.add_argument('--corrected-state',type=Path);corrected.add_argument('--turn',type=int,help='Interactive history number; default is the latest Work result.')
    prompt=p.add_mutually_exclusive_group(required=True);prompt.add_argument('--prompt-file',type=Path);prompt.add_argument('--prompt')
    completion=p.add_mutually_exclusive_group(required=True);completion.add_argument('--completion-file',type=Path);completion.add_argument('--completion')
    p.add_argument('--title',default='Checked correction');p.add_argument('--rationale',default='Host-selected correction after recorded failing and passing checks.')
    p.add_argument('--output',type=Path);p.add_argument('--operation-id');p.add_argument('--queue',action='store_true');p.add_argument('--train-now',action='store_true');p.add_argument('--parent-job-id');p.add_argument('--optimizer-profile-id');p.add_argument('--skill',dest='skill_id')
    p.add_argument('--skill-guard',action='store_true');p.add_argument('--batch-size',type=int,default=8);p.add_argument('--steps',type=int,help='Guarded training step budget; default 16')
    p.add_argument('--learning-rate',type=float,default=.0001);p.add_argument('--rank',type=int,default=4);p.add_argument('--mode',choices=('lora','full'),default='lora')
    p=subs.add_parser('submit',help='Queue one authored lesson; --train-now also requests a single-example update.')
    p.add_argument('file',type=Path);p.add_argument('--operation-id',required=True);p.add_argument('--train-now',action='store_true')
    p.add_argument('--parent-job-id');p.add_argument('--optimizer-profile-id')
    p.add_argument('--skill-guard',action='store_true');p.add_argument('--batch-size',type=int,default=8);p.add_argument('--steps',type=int,help='Guarded training step budget; default 16')
    p.add_argument('--learning-rate',type=float,default=.0001);p.add_argument('--rank',type=int,default=4);p.add_argument('--mode',choices=('lora','full'),default='lora')
    subs.add_parser('list')
    subs.add_parser('skills')
    subs.add_parser('optimizers',help='List owner-registered native optimizer policies.')
    subs.add_parser('exports',help='List privately preserved standalone model checkpoints.')
    p=subs.add_parser('preserve',help='Name a completed PCC full-weight checkpoint without uploading it.')
    p.add_argument('job_id');p.add_argument('--operation-id',required=True);p.add_argument('--name',required=True)
    p.add_argument('--expected-sha256',required=True);p.add_argument('--notes-file',type=Path);p.add_argument('--report-sha256')
    p=subs.add_parser('show');p.add_argument('lesson_id')
    p=subs.add_parser('status');p.add_argument('job_id')
    p=subs.add_parser('train',help='Train an explicit lesson selection now or a frozen selection of queued lessons.')
    p.add_argument('lesson_ids',nargs='*');selection=p.add_mutually_exclusive_group();selection.add_argument('--all',action='store_true');selection.add_argument('--pending',action='store_true')
    p.add_argument('--operation-id',required=True);p.add_argument('--mode',choices=('lora','full'),default='lora')
    p.add_argument('--batch-size',type=int,default=4);p.add_argument('--steps',type=int,help='Default: enough mini-batches to cover the selected lessons once.')
    p.add_argument('--learning-rate',type=float,default=.0001);p.add_argument('--rank',type=int,default=4);p.add_argument('--parent-job-id');p.add_argument('--optimizer-profile-id')
    p.add_argument('--skill-guard',action='store_true')
    args=parser.parse_args(argv)
    from .cow_client import CowClientError
    try:
        connection,client=_client(args,connection_override)
        profile=getattr(args,'optimizer_profile_id',None)
        if profile is not None:
            if not re.fullmatch(r'[a-f0-9]{64}',profile):raise ValueError('Choose an owner-registered optimizer profile SHA-256')
            if args.mode!='full':raise ValueError('Native optimizer profiles require full-weight mode')
            if args.skill_guard:raise ValueError('Native optimizer profiles currently use explicit lesson blocks, not the legacy skill guard')
            if args.action in ('create','submit') and not args.train_now:raise ValueError('Optimizer selection requires --train-now')
        if args.action=='create':
            def workflow(number):
                if session_history is None:raise ValueError('Supply --corrected-state outside an interactive session')
                if number is None:
                    rows=[row for row in session_history if row.get('input',{}).get('mode') in ('work','edit','explore','continue') or (row.get('result') or {}).get('mode')=='work']
                    if not rows:raise ValueError('No completed Work task is available for a lesson')
                    result=rows[-1].get('result') or {}
                    if not result.get('workflow') or result.get('checks_passed') is not True:raise ValueError('Finish and verify the latest Work task, or explicitly select an earlier --turn')
                    return Path(result['workflow'])
                if not 1<=number<=len(session_history):raise ValueError('Choose a valid /history number')
                path=(session_history[number-1].get('result') or {}).get('workflow')
                if not path:raise ValueError('That turn has no completed coding workflow')
                return Path(path)
            corrected=args.corrected_state or workflow(args.turn)
            failed=args.failed_state or (workflow(args.failed_turn) if args.failed_turn is not None else corrected)
            lesson=create_lesson(failed,corrected,args.prompt_file.read_text() if args.prompt_file else args.prompt,
                args.completion_file.read_text() if args.completion_file else args.completion,args.title,args.rationale,connection['model_contract_id'])
            if args.skill_id is not None:
                if not re.fullmatch(r'[a-z][a-z0-9_.-]{0,95}',args.skill_id):raise ValueError('Invalid skill identifier')
                lesson['skill_id']=args.skill_id
            if (args.queue or args.train_now) and not args.operation_id:raise ValueError('Use --operation-id NAME when queuing or training a lesson')
            identity=args.operation_id or 'draft-'+uuid.uuid4().hex
            if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,119}',identity):raise ValueError('Use a bounded operation name')
            if args.output is None:
                folder=client.journal.directory/'drafts';folder.mkdir(mode=0o700,parents=True,exist_ok=True);args.output=folder/(identity+'.json')
            if args.output.exists():
                if json.loads(args.output.read_bytes())!=lesson:raise ValueError('Existing lesson draft has different bytes')
            else:
                fd=os.open(args.output,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
                with os.fdopen(fd,'wb') as stream:stream.write(canonical(lesson)+b'\n');stream.flush();os.fsync(stream.fileno())
            value=dict(lesson_file=str(args.output),submitted=False)
            if args.queue or args.train_now:
                value['acceptance']=client.training_submit('lessons',dict(lesson=lesson),identity);value['submitted']=True
                if args.train_now:value['training']=_submit_training(client,args,identity+'-train',[value['acceptance']['lesson_id']],single=True)
        elif args.action=='submit':
            lesson=json.loads(args.file.read_bytes())
            if lesson.get('model_contract_id')!=connection['model_contract_id']:raise ValueError('Lesson does not match the selected connection')
            value=client.training_submit('lessons',dict(lesson=lesson),args.operation_id)
            if args.train_now:
                value=dict(lesson=value,training=_submit_training(client,args,args.operation_id+'-train',[value['lesson_id']],single=True))
        elif args.action=='skills':value=client.training_read('skills')
        elif args.action=='optimizers':value=client.training_read('optimizer-profiles')
        elif args.action=='exports':value=client.training_read('exports')
        elif args.action=='preserve':
            notes='' if args.notes_file is None else args.notes_file.read_text(encoding='utf-8')
            value=client.training_submit('exports',dict(job_id=args.job_id,name=args.name,
                expected_sha256=args.expected_sha256,notes=notes,report_sha256=args.report_sha256),args.operation_id)
        elif args.action in ('list','show','status'):
            value=client.training_read('jobs' if args.action=='status' else 'lessons',getattr(args,'job_id',getattr(args,'lesson_id',None)))
        else:
            if (args.all or args.pending) and args.lesson_ids:raise ValueError('Choose explicit lesson IDs or a queue selection')
            saved=client.journal.read(args.operation_id)
            frozen=json.loads(client.journal.decode_body(saved)) if saved is not None and saved['path']=='/cow/training/jobs' else None
            ids=(frozen['lesson_ids'] if frozen is not None and not args.lesson_ids else
                 [row['lesson_id'] for row in client.training_read('lessons')['lessons'] if not args.pending or row['pending']]
                 if args.all or args.pending else args.lesson_ids)
            if not ids:raise ValueError('Select at least one queued lesson')
            if args.batch_size<=0:raise ValueError('Batch size must be positive')
            steps=args.steps if args.steps is not None else frozen['steps'] if frozen else (len(ids)+args.batch_size-1)//args.batch_size
            value=_submit_training(client,args,args.operation_id,ids,steps=steps)
        output(json.dumps(value,sort_keys=True));return 0
    except (ValueError,OSError,RuntimeError,CowClientError) as error:
        output('branchwrite lesson: '+ascii(str(error)));return 2
