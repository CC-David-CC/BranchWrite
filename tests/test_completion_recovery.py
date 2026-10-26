"""Owner metadata recovery contracts and real journal/files; no native/model jobs."""
from pathlib import Path
import copy,hashlib,json,os,tempfile,unittest
from unittest import mock
from branchwrite.cow_client import (CowClient,OperationJournal,OperationIndeterminate,OperationReuseError,
    ReceiptError,RequestRejected,_Response,_canonical,validate_completion_inspection)
from branchwrite.lesson_cli import digest,main

MODEL='a'*64
APPROVAL='adopt-completed-original-native-v1'
ROUTE='/cow/training/job-reconciliations'


def inspection(state='eligible'):
    reasons={'eligible':'original_completion_verified','adoption_pending':'original_adoption_pending','adopted':'original_adoption_verified',
             'unavailable':'original_process_live','ineligible':'legacy_provenance_missing'}
    actions={'eligible':'adopt_original_completion','adoption_pending':'resume_original_adoption','adopted':'reconcile_learning_run',
             'unavailable':'hold','ineligible':'hold'}
    verified=state in ('eligible','adoption_pending','adopted')
    value=dict(schema=1,kind='pcc.native-completion-recovery.v1',job_id='original-job',model_contract_id=MODEL,state=state,
        reason_code=reasons[state],next_actions=[actions[state]],eligible=state=='eligible',current_evidence_verified=verified,
        message='Controlled owner metadata fixture',model_calls_started=0,native_jobs_started=0,promoted=False)
    if verified:
        value.update(job_record_sha256='b'*64,evidence_sha256='c'*64,candidate_sha256='d'*64,
            native_configuration_sha256='e'*64,source_closure_sha256='f'*64,runtime_environment_sha256='0'*64)
    if state=='adoption_pending':
        value.update(pending_operation_id='adopt-original',pending_request=dict(operation_id='adopt-original',**approval_payload()))
    if state=='adopted':value['adoption_operation_id']='adopt-original'
    return value


def approval_payload():
    return dict(job_id='original-job',expected_job_record_sha256='b'*64,expected_evidence_sha256='c'*64,
                expected_candidate_sha256='d'*64,approval=APPROVAL)


def ack(path,body):
    return dict(schema=1,operation_id=body['operation_id'],request_sha256=hashlib.sha256(_canonical([path,body])).hexdigest(),
                job_id=body['job_id'],candidate_sha256=body['expected_candidate_sha256'],adopted=True,promoted=False)


class MetadataTransport:
    name='controlled-owner-metadata-only'
    def __init__(self):self.calls=[];self.view=inspection();self.saved=None;self.lose_committed=False;self.leave_pending=False;self.reject=False;self.bad_ack=None
    def request(self,method,path,body=None,**kwargs):
        self.calls.append((method,path,body))
        if method=='GET' and path.endswith('/completion-recovery'):
            return _Response(json_value=copy.deepcopy(self.view),transport=self.name)
        if method=='GET' and path.startswith('/cow/training/operations/'):
            if self.saved is None:raise RequestRejected('Original metadata approval is pending',status_code=409)
            return _Response(json_value=dict(self.saved),transport=self.name)
        if method!='POST' or path!=ROUTE:raise AssertionError('Unexpected native/training or unrelated route '+path)
        value=json.loads(body)
        if self.reject:raise RequestRejected('Original evidence CAS changed',status_code=400)
        result=ack(path,value)
        if self.leave_pending:
            self.leave_pending=False;raise OperationIndeterminate('Approval intent saved; response lost before commit')
        self.saved=result
        if self.lose_committed:
            self.lose_committed=False;raise OperationIndeterminate('Committed metadata response lost')
        if self.bad_ack:self.bad_ack(result)
        return _Response(json_value=result,transport=self.name)


class CompletionRecovery(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='bw-owner-recovery-');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.transport=MetadataTransport();self.journal=OperationJournal(self.root/'journal')
        self.client=CowClient(self.transport,journal=self.journal,endpoint_url='http://127.0.0.1:8099',endpoint_pin='owner-endpoint')
        self.connection=dict(endpoint_url=self.client.endpoint_url,endpoint_pin=self.client.endpoint_pin,model_contract_id=MODEL,
                             execution_profile_id='9'*64,eos_tokens=[1])

    def cli(self,args):
        lines=[]
        with mock.patch('branchwrite.lesson_cli._client',return_value=(self.connection,self.client)):
            result=main(args,output=lines.append)
        return result,json.loads(lines[-1])

    def save(self,state='eligible',name='inspection.json'):
        self.transport.view=inspection(state);path=self.root/name
        result,value=self.cli(['inspect-completion','original-job','--output',str(path)])
        self.assertEqual(result,0,value);return path,value

    def adopt_args(self,path,op='adopt-original',approve=True):
        args=['adopt-completion','original-job','--inspection-file',str(path),'--operation-id',op]
        if approve:args.append('--approve-original-completion')
        return args

    def test_all_typed_inspection_states_and_next_actions_validate(self):
        for state in ('eligible','adoption_pending','adopted','unavailable','ineligible'):
            with self.subTest(state=state):
                value=inspection(state)
                self.assertEqual(validate_completion_inspection(value,job_id='original-job',model_contract_id=MODEL),value)
        self.client.inspect_completion('original-job',model_contract_id=MODEL)
        self.assertEqual(self.transport.calls[0][:2],('GET','/cow/training/jobs/original-job/completion-recovery'))

    def test_normal_complete_job_reports_no_adoption_needed_with_original_next_actions(self):
        value=inspection('ineligible');value.update(reason_code='original_job_already_complete',next_actions=['inspect_original_job','learning_status'])
        self.assertEqual(validate_completion_inspection(value,job_id='original-job',model_contract_id=MODEL),value)
        self.transport.view=value;file,document=self.save_normal_complete(value)
        code,result=self.cli(self.adopt_args(file));self.assertEqual(code,2,result)
        self.assertEqual(result['inspection']['reason_code'],'original_job_already_complete')
        self.assertEqual(result['inspection']['next_actions'],['inspect_original_job','learning_status'])
        self.assertFalse(any(c[0]=='POST' for c in self.transport.calls))
        wrong=dict(value,next_actions=['hold'])
        with self.assertRaises(ReceiptError):validate_completion_inspection(wrong,job_id='original-job',model_contract_id=MODEL)
    def save_normal_complete(self,value):
        self.transport.view=value;path=self.root/'normal-complete.json'
        code,document=self.cli(['inspect-completion','original-job','--output',str(path)])
        self.assertEqual(code,0,document);return path,document

    def test_inspection_rejects_wrong_identity_actions_types_and_unverified_ready_state(self):
        alterations=[lambda v:v.update(job_id='other-job'),lambda v:v.update(model_contract_id='1'*64),lambda v:v.update(schema=True),
            lambda v:v.update(native_jobs_started=False),lambda v:v.update(promoted=0),lambda v:v.update(eligible=1),
            lambda v:v.update(current_evidence_verified=False),lambda v:v.update(next_actions=['train_again']),
            lambda v:v.update(reason_code='unknown'),lambda v:v.update(extra='unqualified'),lambda v:v.pop('source_closure_sha256'),
            lambda v:v.update(candidate_sha256='bad')]
        for alter in alterations:
            value=inspection();alter(value)
            with self.assertRaises(ReceiptError):validate_completion_inspection(value,job_id='original-job',model_contract_id=MODEL)

    def test_pending_inspection_binds_the_exact_original_request(self):
        for key,value in [('operation_id','different-operation'),('job_id','other-job'),('expected_candidate_sha256','1'*64),('approval','approve-anything')]:
            view=inspection('adoption_pending');view['pending_request'][key]=value
            with self.assertRaises(ReceiptError):validate_completion_inspection(view,job_id='original-job',model_contract_id=MODEL)

    def test_explicit_owner_metadata_commit_and_cached_retry_never_posts_training(self):
        result=self.client.training_submit('job-reconciliations',approval_payload(),'adopt-original')
        again=self.client.training_submit('job-reconciliations',approval_payload(),'adopt-original')
        self.assertEqual(result,again);self.assertTrue(result['adopted']);self.assertFalse(result['promoted'])
        self.assertEqual([x[:2] for x in self.transport.calls],[('POST',ROUTE)])
        self.assertEqual(self.journal.read('adopt-original')['state'],'complete')

    def test_lost_committed_ack_reads_original_without_second_post(self):
        self.transport.lose_committed=True
        result=self.client.training_submit('job-reconciliations',approval_payload(),'adopt-original')
        self.assertEqual([x[0] for x in self.transport.calls],['POST','GET'])
        self.assertEqual(self.client.training_submit('job-reconciliations',approval_payload(),'adopt-original'),result)
        self.assertEqual([x[0] for x in self.transport.calls],['POST','GET'])

    def test_pending_approval_has_no_complete_ack_exact_metadata_post_can_resume(self):
        self.transport.leave_pending=True
        with self.assertRaises(OperationIndeterminate):self.client.training_submit('job-reconciliations',approval_payload(),'adopt-original')
        self.assertEqual(self.journal.read('adopt-original')['state'],'pending')
        result=self.client.training_submit('job-reconciliations',approval_payload(),'adopt-original')
        self.assertTrue(result['adopted'])
        posts=[x for x in self.transport.calls if x[0]=='POST']
        self.assertEqual(len(posts),2);self.assertEqual(posts[0],posts[1])
        self.assertEqual({x[1] for x in posts},{ROUTE})

    def test_changed_pending_body_or_endpoint_cannot_resume_original_approval(self):
        self.transport.leave_pending=True
        with self.assertRaises(OperationIndeterminate):self.client.training_submit('job-reconciliations',approval_payload(),'adopt-original')
        original_calls=len(self.transport.calls)
        changed=dict(approval_payload(),expected_evidence_sha256='1'*64)
        with self.assertRaises(OperationReuseError):self.client.training_submit('job-reconciliations',changed,'adopt-original')
        other=CowClient(self.transport,journal=self.journal,endpoint_url='http://127.0.0.1:9999',endpoint_pin='other-owner')
        with self.assertRaises(OperationReuseError):other.training_submit('job-reconciliations',approval_payload(),'adopt-original')
        self.assertEqual(len(self.transport.calls),original_calls)

    def test_explicit_operation_id_cannot_be_replaced_inside_payload(self):
        with self.assertRaises(ValueError):self.client.training_submit('job-reconciliations',dict(approval_payload(),operation_id='other'),'adopt-original')
        self.assertFalse(self.transport.calls)

    def test_forged_or_pending_ack_cannot_complete_owner_journal(self):
        alterations=[lambda v:v.update(job_id='wrong'),lambda v:v.update(candidate_sha256='1'*64),lambda v:v.update(request_sha256='0'*64),
            lambda v:v.update(adopted=False),lambda v:v.update(adopted=1),lambda v:v.update(promoted=True),lambda v:v.update(schema=True),
            lambda v:v.update(state='pending')]
        for i,alter in enumerate(alterations):
            self.transport.bad_ack=alter;op='bad-ack-'+str(i)
            with self.assertRaises(ReceiptError):self.client.training_submit('job-reconciliations',approval_payload(),op)
            self.assertEqual(self.journal.read(op)['state'],'pending')

    def test_inspection_file_replaces_hash_copying_and_binds_owner_endpoint_and_model(self):
        path,document=self.save();self.assertEqual(path.stat().st_mode&0o777,0o600)
        self.assertEqual(document['inspection']['state'],'eligible');self.assertEqual(document['model_contract_id'],MODEL)
        self.transport.calls.clear()
        result,value=self.cli(self.adopt_args(path))
        self.assertEqual(result,0,value);self.assertTrue(value['adopted'])
        self.assertEqual([x[:2] for x in self.transport.calls],[('POST',ROUTE)])

    def test_owner_approval_is_explicit_and_missing_approval_never_sends_request(self):
        path,_=self.save();self.transport.calls.clear()
        result,value=self.cli(self.adopt_args(path,approve=False))
        self.assertEqual(result,2);self.assertEqual(value['state'],'hold');self.assertEqual(value['next_actions'],['hold'])
        self.assertFalse(self.transport.calls);self.assertIsNone(self.journal.read('adopt-original'))

    def test_hold_and_already_adopted_views_never_start_new_adoption(self):
        for state in ('unavailable','ineligible','adopted'):
            path,document=self.save(state,name=state+'.json');self.transport.calls.clear()
            result,value=self.cli(self.adopt_args(path,op='must-not-submit-'+state))
            self.assertEqual(result,2);self.assertEqual(value['inspection']['state'],state)
            self.assertFalse(self.transport.calls);self.assertIsNone(self.journal.read('must-not-submit-'+state))

    def test_pending_inspection_resumes_original_id_and_refuses_new_id(self):
        path,_=self.save('adoption_pending');self.transport.calls.clear()
        result,value=self.cli(self.adopt_args(path,op='new-id'))
        self.assertEqual(result,2);self.assertEqual(value['state'],'hold');self.assertFalse(self.transport.calls)
        result,value=self.cli(self.adopt_args(path))
        self.assertEqual(result,0,value);self.assertTrue(value['adopted'])
        self.assertEqual(json.loads(self.transport.calls[-1][2])['operation_id'],'adopt-original')

    def test_file_tamper_and_recomputed_cross_endpoint_file_are_refused(self):
        path,document=self.save();self.transport.calls.clear();original=path.read_bytes()
        document['inspection']['candidate_sha256']='1'*64;path.write_bytes(_canonical(document))
        result,value=self.cli(self.adopt_args(path));self.assertEqual(result,2);self.assertFalse(self.transport.calls)
        document=json.loads(original);document['endpoint_pin']='another-owner'
        document['document_id']=digest({k:v for k,v in document.items() if k!='document_id'});path.write_bytes(_canonical(document))
        result,value=self.cli(self.adopt_args(path));self.assertEqual(result,2);self.assertFalse(self.transport.calls)

    def test_wrong_job_argument_or_mixed_hash_sources_are_refused_before_post(self):
        path,_=self.save();self.transport.calls.clear()
        args=self.adopt_args(path);args[1]='other-job'
        result,value=self.cli(args);self.assertEqual(result,2);self.assertFalse(self.transport.calls)
        result,value=self.cli(self.adopt_args(path)+['--expected-candidate-sha256','d'*64])
        self.assertEqual(result,2);self.assertFalse(self.transport.calls)

    def test_inspection_file_cannot_be_overwritten_or_used_with_broad_permissions(self):
        path,_=self.save();original=path.read_bytes()
        result,value=self.cli(['inspect-completion','original-job','--output',str(path)])
        self.assertEqual(result,2);self.assertEqual(path.read_bytes(),original)
        path.chmod(0o644);self.transport.calls.clear()
        result,value=self.cli(self.adopt_args(path));self.assertEqual(result,2);self.assertFalse(self.transport.calls)

    def test_inspection_open_races_validate_actual_descriptor_and_original_identity(self):
        original_open=os.open
        for race in ('broader-permissions','replacement'):
            with self.subTest(race=race):
                path,_=self.save(name=race+'.json');self.transport.calls.clear();triggered=[]
                def raced_open(candidate,flags,*args,**kwargs):
                    if Path(candidate)==path and not triggered:
                        triggered.append(True)
                        if race=='broader-permissions':path.chmod(0o644)
                        else:
                            replacement=self.root/'replacement.json';replacement.write_bytes(path.read_bytes());replacement.chmod(0o600)
                            os.replace(replacement,path)
                    return original_open(candidate,flags,*args,**kwargs)
                with mock.patch('branchwrite.lesson_cli.os.open',side_effect=raced_open):
                    code,value=self.cli(self.adopt_args(path))
                self.assertEqual(code,2,value);self.assertEqual(value['next_actions'],['hold']);self.assertTrue(triggered)
                self.assertFalse(self.transport.calls);self.assertIsNone(self.journal.read('adopt-original'))

    def test_inspection_metadata_change_during_read_is_refused(self):
        path,_=self.save();self.transport.calls.clear();original_fdopen=os.fdopen
        class ChangingReader:
            def __init__(self,stream):self.stream=stream
            def __enter__(self):return self
            def __exit__(self,*args):return self.stream.__exit__(*args)
            def fileno(self):return self.stream.fileno()
            def read(self,size):
                raw=self.stream.read(size);path.chmod(0o400);return raw
        with mock.patch('branchwrite.lesson_cli.os.fdopen',side_effect=lambda fd,mode:ChangingReader(original_fdopen(fd,mode))):
            code,value=self.cli(self.adopt_args(path))
        self.assertEqual(code,2,value);self.assertIn('changed while',value['message'])
        self.assertFalse(self.transport.calls);self.assertIsNone(self.journal.read('adopt-original'))

    def test_stale_evidence_is_server_refusal_and_remains_uncommitted(self):
        path,_=self.save();self.transport.reject=True
        result,value=self.cli(self.adopt_args(path))
        self.assertEqual(result,2);self.assertEqual(value['state'],'hold');self.assertEqual(self.journal.read('adopt-original')['state'],'pending')
        self.assertEqual([x[1] for x in self.transport.calls if x[0]=='POST'],[ROUTE])

    def test_manual_hash_mode_checks_fresh_inspection_and_requires_all_pins(self):
        args=['adopt-completion','original-job','--operation-id','manual-approval','--approve-original-completion',
            '--expected-job-record-sha256','b'*64,'--expected-evidence-sha256','c'*64,'--expected-candidate-sha256','d'*64]
        result,value=self.cli(args);self.assertEqual(result,0,value)
        self.assertEqual([x[0] for x in self.transport.calls],['GET','POST'])
        self.transport.calls.clear();result,value=self.cli(['adopt-completion','original-job','--operation-id','no-pins','--approve-original-completion'])
        self.assertEqual(result,2);self.assertFalse(self.transport.calls)

    def test_transport_unknown_is_typed_hold_and_retains_original_operation_id(self):
        path,_=self.save();self.transport.leave_pending=True
        result,value=self.cli(self.adopt_args(path))
        self.assertEqual(result,2);self.assertEqual(value['kind'],'bw.owner-completion-hold.v1')
        self.assertEqual(value['reason_code'],'original_adoption_unresolved');self.assertEqual(value['operation_id'],'adopt-original')
        self.assertEqual(value['next_actions'],['hold']);self.assertFalse(value['receipt_verified'])





class LearningMetadataTransport(MetadataTransport):
    def __init__(self):
        super().__init__()
        self.run=dict(schema=1,run_id='original-run',revision=7,phase='needs_operator',model_contract_id=MODEL,promoted=False,
            operator_reason_code='native_job_unresolved',available_actions=[dict(action='reconcile',required_fields=[])])
    def request(self,method,path,body=None,**kwargs):
        if method=='GET' and path.startswith('/cow/training/learning-runs/'):
            self.calls.append((method,path,body));return _Response(json_value=copy.deepcopy(self.run),transport=self.name)
        if method=='POST' and path=='/cow/training/learning-steps':
            self.calls.append((method,path,body));value=json.loads(body)
            result=dict(schema=1,operation_id=value['operation_id'],request_sha256=hashlib.sha256(_canonical([path,value])).hexdigest(),
                run_id=value['run_id'],step_id=value['operation_id'])
            if self.leave_pending:
                self.leave_pending=False;raise OperationIndeterminate('Controlled metadata boundary before commit')
            self.saved=result;self.run.update(phase='candidate_pending',revision=8)
            if self.lose_committed:
                self.lose_committed=False;raise OperationIndeterminate('Controlled committed step acknowledgment loss')
            if self.bad_ack:self.bad_ack(result)
            return _Response(json_value=result,transport=self.name)
        return super().request(method,path,body,**kwargs)


class CompletionLearningRecovery(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.transport=LearningMetadataTransport()
        self.client=CowClient(self.transport,journal=OperationJournal(Path(self.temp.name)/'journal'),endpoint_url='http://127.0.0.1:8099',endpoint_pin='owner-endpoint')
        self.connection=dict(endpoint_url=self.client.endpoint_url,endpoint_pin=self.client.endpoint_pin,model_contract_id=MODEL,execution_profile_id='9'*64,eos_tokens=[1])
    def reconcile(self,revision=7,operation='original-step'):
        return self.client.reconcile_completion('original-run',operation,revision,model_contract_id=MODEL)
    def cli(self,args):
        lines=[]
        with mock.patch('branchwrite.lesson_cli._client',return_value=(self.connection,self.client)):
            result=main(args,output=lines.append)
        return result,json.loads(lines[-1])
    def test_explicit_cli_runs_only_metadata_step_then_cached_same_request(self):
        result,value=self.cli(['reconcile-completion','original-run','--operation-id','original-step','--expected-revision','7'])
        self.assertEqual(result,0,value);self.assertEqual(value['step_id'],'original-step')
        self.assertEqual(self.reconcile(),value)
        self.assertEqual([c[:2] for c in self.transport.calls],[('GET','/cow/training/learning-runs/original-run'),('POST','/cow/training/learning-steps')])
        self.assertEqual(json.loads(self.transport.calls[-1][2]),dict(operation_id='original-step',run_id='original-run',expected_revision=7,action='reconcile'))
    def test_status_cli_is_model_bound_and_read_only(self):
        result,value=self.cli(['learning-status','original-run']);self.assertEqual(result,0,value);self.assertEqual(value,self.transport.run)
        self.assertTrue(all(c[0]=='GET' for c in self.transport.calls))
        self.transport.run['model_contract_id']='1'*64
        result,value=self.cli(['learning-status','original-run']);self.assertEqual(result,2);self.assertEqual(value['next_actions'],['hold']);self.assertEqual(value['run_id'],'original-run')
    def test_ack_lost_after_commit_gets_same_operation_not_new_post(self):
        self.transport.lose_committed=True
        value=self.reconcile();self.assertEqual(value['step_id'],'original-step')
        self.assertEqual([c[:2] for c in self.transport.calls][-2:],[('POST','/cow/training/learning-steps'),('GET','/cow/training/operations/original-step')])
        self.assertEqual(self.transport.run['phase'],'candidate_pending')
    def test_pending_retry_reads_original_ack_before_phase_preflight(self):
        self.transport.leave_pending=True
        with self.assertRaises(OperationIndeterminate):self.reconcile()
        body=json.loads(self.client.journal.decode_body(self.client.journal.read('original-step')))
        self.transport.saved=dict(schema=1,operation_id='original-step',request_sha256=hashlib.sha256(_canonical(['/cow/training/learning-steps',body])).hexdigest(),run_id='original-run',step_id='original-step')
        self.transport.run.update(phase='candidate_pending',revision=8);before=len(self.transport.calls)
        self.assertEqual(self.reconcile(),self.transport.saved)
        self.assertEqual([c[:2] for c in self.transport.calls[before:]],[('GET','/cow/training/operations/original-step')])
    def test_pending_without_ack_replays_only_exact_verified_boundary(self):
        self.transport.leave_pending=True
        with self.assertRaises(OperationIndeterminate):self.reconcile()
        self.assertEqual(self.reconcile()['step_id'],'original-step')
        self.assertEqual(sum(c[0]=='POST' for c in self.transport.calls),2)
    def test_unknown_changed_or_generic_training_boundary_stays_hold(self):
        changes=[dict(phase='training_pending'),dict(phase='candidate_pending'),dict(revision=8),dict(revision=True),dict(schema=True),
            dict(operator_reason_code='unrelated_failure'),dict(available_actions=[]),dict(model_contract_id='1'*64),dict(promoted=True)]
        for change in changes:
            original=dict(self.transport.run);self.transport.run.update(change)
            with self.subTest(change=change),self.assertRaises(ReceiptError):self.reconcile(operation='hold-'+str(len(self.transport.calls)))
            self.transport.run=original
        self.assertFalse(any(c[0]=='POST' for c in self.transport.calls))
    def test_pending_changed_phase_without_ack_never_posts(self):
        self.transport.leave_pending=True
        with self.assertRaises(OperationIndeterminate):self.reconcile()
        self.transport.run.update(phase='candidate_pending',revision=8);before=sum(c[0]=='POST' for c in self.transport.calls)
        with self.assertRaises(ReceiptError):self.reconcile()
        self.assertEqual(sum(c[0]=='POST' for c in self.transport.calls),before)
        self.assertEqual(self.client.journal.read('original-step')['state'],'pending')
    def test_explicit_original_revision_id_endpoint_and_ack_cannot_change(self):
        self.transport.leave_pending=True
        with self.assertRaises(OperationIndeterminate):self.reconcile()
        before=len(self.transport.calls)
        with self.assertRaises(OperationReuseError):self.reconcile(revision=8)
        self.client.endpoint_pin='different-owner'
        with self.assertRaises(OperationReuseError):self.reconcile()
        self.assertEqual(len(self.transport.calls),before)
    def test_bad_ack_retains_pending_intent(self):
        self.transport.bad_ack=lambda v:v.update(step_id='forged-step')
        with self.assertRaises(ReceiptError):self.reconcile()
        self.assertEqual(self.client.journal.read('original-step')['state'],'pending')


if __name__=='__main__':unittest.main()
