"""Host-selected verified lessons; no model tool can approve its own training."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import stat
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
    expected=getattr(args,'expected_parent_sha256',None)
    if expected is not None:payload['expected_parent_sha256']=expected
    if args.optimizer_profile_id is not None:
        payload['optimizer_profile_id']=args.optimizer_profile_id
        if single and args.steps is not None:payload['steps']=args.steps
    if guarded:
        record=client.journal.read(identity)
        prior=json.loads(client.journal.decode_body(record)) if record is not None and record['path']=='/cow/training/jobs' else None
        payload['skill_guard']=prior['skill_guard'] if prior is not None and 'skill_guard' in prior else dict(policy_id=client.training_read('skills')['policy_id'])
    return client.training_submit('jobs',payload,identity)

class _CompletionHold(ValueError):
    def __init__(self,document):
        self.document=document
        super().__init__('Original completion is not actionable; follow the typed inspection next action')


def _strict_document(raw):
    def pairs(items):
        value={}
        for key,item in items:
            if key in value:raise ValueError('Duplicate inspection field')
            value[key]=item
        return value
    def reject(value):raise ValueError('Nonfinite inspection JSON is not supported')
    return json.loads(raw.decode('utf-8'),object_pairs_hook=pairs,parse_constant=reject)


def _inspection_document(client,connection,job_id,inspection):
    from .cow_client import validate_completion_inspection
    value=validate_completion_inspection(inspection,job_id=job_id,model_contract_id=connection['model_contract_id'])
    document=dict(schema=1,kind='bw.completion-inspection.v1',endpoint_url=client.endpoint_url,
        endpoint_pin=client.endpoint_pin,model_contract_id=connection['model_contract_id'],job_id=job_id,
        inspection=value,inspection_sha256=digest(value))
    document['document_id']=digest(document)
    return document


def _read_inspection(path,client,connection,job_id):
    from .cow_client import validate_completion_inspection
    before=path.lstat()
    if not stat.S_ISREG(before.st_mode):raise ValueError('Use an original regular private inspection file')
    # Path metadata is only an identity observation. Security/size checks apply
    # to the descriptor actually opened, including a replacement before open.
    def identity(info):
        return (info.st_dev,info.st_ino,info.st_mode,info.st_uid,info.st_gid,
                info.st_size,info.st_mtime_ns,info.st_ctime_ns)
    fd=os.open(path,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_NONBLOCK',0))
    with os.fdopen(fd,'rb') as stream:
        opened=os.fstat(stream.fileno())
        if (not stat.S_ISREG(opened.st_mode) or not 0<=opened.st_size<=1<<20
                or (os.name!='nt' and (opened.st_uid!=os.getuid() or opened.st_mode&0o077))):
            raise ValueError('Inspection file must be private, owned and at most1MiB; use inspect-completion --output')
        if identity(before)!=identity(opened):raise ValueError('Inspection file changed before it was opened')
        raw=stream.read((1<<20)+1)
        if (len(raw)!=opened.st_size or identity(opened)!=identity(os.fstat(stream.fileno()))
                or identity(opened)!=identity(path.lstat())):
            raise ValueError('Inspection file changed while it was read')
    value=_strict_document(raw)
    fields={'schema','kind','endpoint_url','endpoint_pin','model_contract_id','job_id','inspection','inspection_sha256','document_id'}
    if (type(value) is not dict or set(value)!=fields or type(value.get('schema')) is not int or value['schema']!=1
            or value.get('kind')!='bw.completion-inspection.v1' or value.get('endpoint_url')!=client.endpoint_url
            or value.get('endpoint_pin')!=client.endpoint_pin or value.get('model_contract_id')!=connection['model_contract_id']
            or value.get('job_id')!=job_id or value.get('inspection_sha256')!=digest(value.get('inspection'))
            or value.get('document_id')!=digest({k:v for k,v in value.items() if k!='document_id'})):
        raise ValueError('Inspection file does not bind the selected job/model/endpoint and exact original view')
    validate_completion_inspection(value['inspection'],job_id=job_id,model_contract_id=connection['model_contract_id'])
    return value


def _write_inspection(path,value):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb') as stream:
        stream.write(canonical(value)+b'\n');stream.flush();os.fsync(stream.fileno())
    if os.name!='nt':
        directory=os.open(path.parent,os.O_RDONLY)
        try:os.fsync(directory)
        finally:os.close(directory)


def _completion_command(args,connection,client):
    from .cow_client import _COMPLETION_APPROVAL
    if args.action=='inspect-completion':
        value=client.inspect_completion(args.job_id,model_contract_id=connection['model_contract_id'])
        document=_inspection_document(client,connection,args.job_id,value)
        if args.output is not None:_write_inspection(args.output,document)
        return document
    if not args.approve_original_completion:raise ValueError('Explicit --approve-original-completion owner approval is required')
    manual=[args.expected_job_record_sha256,args.expected_evidence_sha256,args.expected_candidate_sha256]
    if args.inspection_file is not None:
        if any(v is not None for v in manual):raise ValueError('Choose the inspection file or explicit CAS hashes, not both')
        document=_read_inspection(args.inspection_file,client,connection,args.job_id)
    else:
        if any(v is None for v in manual):raise ValueError('Use --inspection-file from inspect-completion --output, or supply all original CAS hashes')
        value=client.inspect_completion(args.job_id,model_contract_id=connection['model_contract_id'])
        document=_inspection_document(client,connection,args.job_id,value)
    inspection=document['inspection'];state=inspection['state']
    if state not in ('eligible','adoption_pending'):raise _CompletionHold(document)
    if state=='adoption_pending':
        body=dict(inspection['pending_request'])
        if args.operation_id!=inspection['pending_operation_id']:raise ValueError('Pending adoption must retain its original pending_operation_id; a new ID cannot retry it')
    else:
        body=dict(operation_id=args.operation_id,job_id=args.job_id,approval=_COMPLETION_APPROVAL,
            expected_job_record_sha256=inspection['job_record_sha256'],expected_evidence_sha256=inspection['evidence_sha256'],
            expected_candidate_sha256=inspection['candidate_sha256'])
    if args.inspection_file is None and any(body[key]!=value for key,value in zip(
            ('expected_job_record_sha256','expected_evidence_sha256','expected_candidate_sha256'),manual)):
        raise ValueError('Explicit hashes differ from the current verified original inspection')
    operation_id=body.pop('operation_id')
    return client.training_submit('job-reconciliations',body,operation_id)


def main(argv=None,*,output=print,connection_override=None,session_history=None):
    parser=argparse.ArgumentParser(prog='branchwrite lesson',description='Write checked lessons, queue them, and request native training candidates.')
    parser.add_argument('--connection',type=Path);parser.add_argument('--state-dir',type=Path)
    subs=parser.add_subparsers(dest='action',required=True)
    p=subs.add_parser('capture-failure',help='Archive a settled current BW boundary; no independent grade or training approval.')
    p.add_argument('run',type=Path);p.add_argument('--output',type=Path,required=True)
    p=subs.add_parser('capture-correction',help='Archive a checked/finished correction linked to an existing failure capture.')
    p.add_argument('run',type=Path);p.add_argument('--failure-capture',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p=subs.add_parser('capture-show',help='Validate and inspect immutable private workflow evidence without model calls.')
    p.add_argument('capture',type=Path);p.add_argument('--expected-capture-id')
    p=subs.add_parser('create',help='Write a private teaching example bound to failed/passing BW runs.')
    failed=p.add_mutually_exclusive_group();failed.add_argument('--failed-state',type=Path);failed.add_argument('--failed-turn',type=int)
    corrected=p.add_mutually_exclusive_group();corrected.add_argument('--corrected-state',type=Path);corrected.add_argument('--turn',type=int,help='Interactive history number; default is the latest Work result.')
    prompt=p.add_mutually_exclusive_group(required=True);prompt.add_argument('--prompt-file',type=Path);prompt.add_argument('--prompt')
    completion=p.add_mutually_exclusive_group(required=True);completion.add_argument('--completion-file',type=Path);completion.add_argument('--completion')
    p.add_argument('--title',default='Checked correction');p.add_argument('--rationale',default='Host-selected correction after recorded failing and passing checks.')
    p.add_argument('--output',type=Path);p.add_argument('--operation-id');p.add_argument('--queue',action='store_true');p.add_argument('--train-now',action='store_true');p.add_argument('--parent-job-id');p.add_argument('--optimizer-profile-id');p.add_argument('--skill',dest='skill_id')
    p.add_argument('--skill-guard',action='store_true');p.add_argument('--batch-size',type=int,default=8);p.add_argument('--steps',type=int,help='Update count with a guard or registered optimizer policy; guard default 16')
    p.add_argument('--learning-rate',type=float,default=.0001);p.add_argument('--rank',type=int,default=4);p.add_argument('--mode',choices=('lora','full'),default='lora')
    p=subs.add_parser('submit',help='Queue one authored lesson; --train-now also requests a single-example update.')
    p.add_argument('file',type=Path);p.add_argument('--operation-id',required=True);p.add_argument('--train-now',action='store_true')
    p.add_argument('--parent-job-id');p.add_argument('--optimizer-profile-id')
    p.add_argument('--skill-guard',action='store_true');p.add_argument('--batch-size',type=int,default=8);p.add_argument('--steps',type=int,help='Update count with a guard or registered optimizer policy; guard default 16')
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
    p=subs.add_parser('learning-status',help='Read the original PCC learning run and its available owner actions.')
    p.add_argument('run_id')
    p=subs.add_parser('reconcile-completion',help='Return a freshly adopted original completion to its original learning round; never starts training.')
    p.add_argument('run_id');p.add_argument('--operation-id',required=True);p.add_argument('--expected-revision',type=int,required=True)
    p=subs.add_parser('inspect-completion',help='Owner read of original native completion; no model or training calls.')
    p.add_argument('job_id');p.add_argument('--output',type=Path,help='Save a private job/model/endpoint-bound inspection for explicit approval.')
    p=subs.add_parser('adopt-completion',help='Owner-approved original metadata recovery; never repeats training or promotes weights.')
    p.add_argument('job_id');p.add_argument('--operation-id',required=True);p.add_argument('--inspection-file',type=Path)
    p.add_argument('--expected-job-record-sha256');p.add_argument('--expected-evidence-sha256');p.add_argument('--expected-candidate-sha256')
    p.add_argument('--approve-original-completion',action='store_true')
    p=subs.add_parser('train',help='Train an explicit lesson selection now or a frozen selection of queued lessons.')
    p.add_argument('lesson_ids',nargs='*');selection=p.add_mutually_exclusive_group();selection.add_argument('--all',action='store_true');selection.add_argument('--pending',action='store_true')
    p.add_argument('--operation-id',required=True);p.add_argument('--mode',choices=('lora','full'),default='lora')
    p.add_argument('--batch-size',type=int,default=4);p.add_argument('--steps',type=int,help='Default: enough mini-batches to cover the selected lessons once.')
    p.add_argument('--learning-rate',type=float,default=.0001);p.add_argument('--rank',type=int,default=4);p.add_argument('--parent-job-id');p.add_argument('--optimizer-profile-id')
    p.add_argument('--skill-guard',action='store_true')
    for name in ('create','submit','train'):
        subs.choices[name].add_argument('--expected-parent-sha256',help='Require this exact native full-weight or adapter parent, not only its job label')
    args=parser.parse_args(argv)
    from .cow_client import CowClientError
    try:
        if args.action in ('capture-failure','capture-correction','capture-show'):
            from .lesson_capture import capture_failure,capture_correction,read_capture
            if args.action=='capture-failure':value=capture_failure(args.run,args.output)
            elif args.action=='capture-correction':value=capture_correction(args.run,args.output,args.failure_capture)
            else:value=read_capture(args.capture,expected_capture_id=args.expected_capture_id)
            output(json.dumps(dict(capture_directory=str(value.directory),capture_id=value.capture_id,
                manifest=value.manifest,independently_verified=False,training_approved=False),sort_keys=True))
            return 0
        connection,client=_client(args,connection_override)
        if args.action in ('inspect-completion','adopt-completion'):
            value=_completion_command(args,connection,client);output(json.dumps(value,sort_keys=True));return 0
        if args.action in ('learning-status','reconcile-completion'):
            if args.action=='learning-status':value=client.completion_learning_status(args.run_id,model_contract_id=connection['model_contract_id'])
            else:value=client.reconcile_completion(args.run_id,args.operation_id,args.expected_revision,model_contract_id=connection['model_contract_id'])
            output(json.dumps(value,sort_keys=True));return 0
        expected=getattr(args,'expected_parent_sha256',None)
        if expected is not None:
            if not re.fullmatch(r'[a-f0-9]{64}',expected) or args.parent_job_id is None:
                raise ValueError('Expected parent SHA256 requires --parent-job-id and a SHA256')
            if args.action in ('create','submit') and not args.train_now:
                raise ValueError('Expected parent selection requires --train-now')
        profile=getattr(args,'optimizer_profile_id',None)
        if profile is not None:
            if not re.fullmatch(r'[a-f0-9]{64}',profile):raise ValueError('Choose an owner-registered optimizer profile SHA-256')
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
    except _CompletionHold as error:
        output(json.dumps(error.document,sort_keys=True));return 2
    except (ValueError,OSError,RuntimeError,CowClientError) as error:
        if args.action in ('inspect-completion','adopt-completion','learning-status','reconcile-completion'):
            from .cow_client import OperationIndeterminate
            value=dict(schema=1,kind='bw.owner-completion-hold.v1',state='hold',
                reason_code='original_adoption_unresolved' if isinstance(error,OperationIndeterminate) else 'owner_completion_refused',
                next_actions=['hold'],message=ascii(str(error))[:512],receipt_verified=False)
            value['job_id' if hasattr(args,'job_id') else 'run_id']=getattr(args,'job_id',getattr(args,'run_id',None))
            if hasattr(args,'operation_id'):value['operation_id']=args.operation_id
            output(json.dumps(value,sort_keys=True));return 2
        output('branchwrite lesson: '+ascii(str(error)));return 2
