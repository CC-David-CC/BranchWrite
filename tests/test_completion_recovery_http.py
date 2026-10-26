"""Actual BW HTTP owner driver against explicitly opted-in PCC NONMODEL saved evidence.

No fixture/native service is imported unless BW_PCC_COMPLETION_HTTP_FIXTURE=1.
The separate PCC worktree must be frozen/reviewed before enabling this suite.
"""
from contextlib import ExitStack
from pathlib import Path
import copy,hashlib,json,os,tempfile,threading,unittest
from unittest import mock
from branchwrite.cow_client import HTTPTransport,OperationIndeterminate,OperationJournal
from branchwrite.lesson_cli import main


@unittest.skipUnless(os.environ.get('BW_PCC_COMPLETION_HTTP_FIXTURE')=='1','explicit frozen PCC saved-evidence fixture required')
class ActualPCCCompletionHTTP(unittest.TestCase):
    def setUp(self):
        from tools import test_native_completion as fixtures
        from serve.cow_http import make_server
        self.fixtures=fixtures;self.make_server=make_server
        self.temp=tempfile.TemporaryDirectory(prefix='bw-pcc-owner-http-nonmodel-');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.guards=ExitStack();self.addCleanup(self.guards.close)
        self.dispatch=[]
        def forbidden(*args,**kwargs):
            self.dispatch.append(True);raise AssertionError('native/model/process dispatch forbidden in owner metadata recovery')
        for name in ('Popen','run','check_output'):
            self.guards.enter_context(mock.patch('subprocess.'+name,side_effect=forbidden))
        for name in ('tools.pcc_native_training.execute_native','tools.pcc_lessons.execute_native','tools.pcc_native_completion.reload_gate'):
            self.guards.enter_context(mock.patch(name,side_effect=forbidden))
        self.servers=[];self.fixture_cleanups=[]
        self.addCleanup(self.close_servers)
    def close_servers(self):
        for server,thread in reversed(self.servers):
            server.shutdown();server.server_close();thread.join(5);self.assertFalse(thread.is_alive())
        for cleanup in reversed(self.fixture_cleanups):cleanup()
        self.assertEqual(self.dispatch,[])
    def serve(self,fixture,name='owner'):
        # Deliberately fixed, temporary loopback-fixture credential; never a fleet credential.
        server=self.make_server(object(),api_key='controlled-nonmodel-owner-only',training_service=fixture.service)
        thread=threading.Thread(target=server.serve_forever);thread.start();self.servers.append((server,thread))
        connection=dict(endpoint_url='http://127.0.0.1:'+str(server.server_port),endpoint_pin='controlled-owner-'+name,
            model_contract_id=fixture.service.model,execution_profile_id='9'*64,eos_tokens=[1])
        return connection,self.root/(name+'-journal')
    def fixture(self,name='original',**kwargs):
        value=self.fixtures.SavedEvidence(self.root/name,**kwargs);self.fixture_cleanups.append(value.close);return value
    def cli(self,connection,journal,args):
        output=[]
        with mock.patch.dict(os.environ,{'BW_COW_API_KEY':'controlled-nonmodel-owner-only'}):
            code=main(['--state-dir',str(journal)]+args,output=output.append,connection_override=connection)
        return code,json.loads(output[-1])
    def inspect_file(self,fixture,connection,journal,name='inspection'):
        file=self.root/(name+'.json')
        code,value=self.cli(connection,journal,['inspect-completion',fixture.job,'--output',str(file)])
        self.assertEqual(code,0,value);return file,value
    def adopt_args(self,fixture,file,operation='owner-adopt'):
        return ['adopt-completion',fixture.job,'--inspection-file',str(file),'--operation-id',operation,'--approve-original-completion']
    def test_full_and_lora_actual_routes_preserve_original_job_and_never_dispatch(self):
        for mode in ('full','lora'):
            with self.subTest(mode=mode):
                fixture=self.fixture(mode,mode=mode);connection,journal=self.serve(fixture,mode)
                original=fixture.service.job(fixture.job);file,value=self.inspect_file(fixture,connection,journal,mode)
                self.assertEqual(value['inspection']['state'],'eligible')
                self.assertEqual(value['inspection']['native_jobs_started'],0)
                args=self.adopt_args(fixture,file,mode+'-adopt');code,ack=self.cli(connection,journal,args)
                self.assertEqual(code,0,ack);self.assertTrue(ack['adopted']);self.assertFalse(ack['promoted'])
                self.assertEqual(self.cli(connection,journal,args),(0,ack))
                after=fixture.service.job(fixture.job);self.assertEqual(after['job_id'],original['job_id']);self.assertEqual(after['state'],'complete')
                code,current=self.cli(connection,journal,['inspect-completion',fixture.job]);self.assertEqual(code,0,current)
                self.assertEqual(current['inspection']['state'],'adopted');self.assertFalse(current['inspection']['eligible'])
                self.assertEqual(current['inspection']['next_actions'],['reconcile_learning_run'])
    def test_actual_changed_candidate_and_missing_provenance_hold_without_approval(self):
        fixture=self.fixture();connection,journal=self.serve(fixture)
        file,_=self.inspect_file(fixture,connection,journal)
        candidate=Path(fixture.native['candidate']);candidate.write_bytes(candidate.read_bytes()+b' changed')
        code,value=self.cli(connection,journal,self.adopt_args(fixture,file));self.assertEqual(code,2,value)
        self.assertEqual(value['next_actions'],['hold']);self.assertEqual(OperationJournal(journal).read('owner-adopt')['state'],'pending')
        code,value=self.cli(connection,journal,['inspect-completion',fixture.job]);self.assertEqual(code,0,value)
        self.assertEqual(value['inspection']['state'],'ineligible');self.assertEqual(value['inspection']['reason_code'],'original_evidence_invalid')
        legacy=self.fixture('legacy');legacy_conn,legacy_journal=self.serve(legacy,'legacy')
        (legacy.folder/'completion-intent.json').unlink()
        code,value=self.cli(legacy_conn,legacy_journal,['inspect-completion',legacy.job]);self.assertEqual(code,0,value)
        self.assertEqual(value['inspection']['next_actions'],['hold']);self.assertFalse(value['inspection']['eligible'])
    def test_actual_adoption_ack_lost_keeps_original_metadata_operation(self):
        fixture=self.fixture();connection,journal=self.serve(fixture);file,_=self.inspect_file(fixture,connection,journal)
        original=HTTPTransport.request;calls=[];lost=[False];lost_get=[False]
        def request(transport,method,path,body=None,**kwargs):
            calls.append((method,path))
            if method=='GET' and path=='/cow/training/operations/owner-adopt' and lost[0] and not lost_get[0]:
                lost_get[0]=True;raise OperationIndeterminate('Controlled first acknowledgment read unavailable')
            result=original(transport,method,path,body,**kwargs)
            if method=='POST' and path=='/cow/training/job-reconciliations' and not lost[0]:
                lost[0]=True;raise OperationIndeterminate('Controlled original adoption acknowledgment loss')
            return result
        args=self.adopt_args(fixture,file)
        with mock.patch.object(HTTPTransport,'request',request):
            code,value=self.cli(connection,journal,args);self.assertEqual(code,2,value)
            self.assertEqual(OperationJournal(journal).read('owner-adopt')['state'],'pending')
            code,ack=self.cli(connection,journal,args);self.assertEqual(code,0,ack);self.assertEqual(ack['operation_id'],'owner-adopt')
        self.assertEqual(fixture.service.job(fixture.job)['state'],'complete')
        self.assertEqual([p for m,p in calls if m=='POST'],['/cow/training/job-reconciliations']*2)
        self.assertEqual(self.dispatch,[])
    def test_normal_complete_job_needs_no_adoption_even_when_recovery_disabled(self):
        from tools import pcc_native_completion as nc
        for enabled in (True,False):
            with self.subTest(recovery_enabled=enabled):
                name='normal-'+str(enabled);fixture=self.fixture(name)
                path=fixture.service.root/'operations'/(fixture.job+'.json');record=fixture.service._read(path)
                record.update(state='complete',candidate=nc.envelope(fixture.native,fixture.raw));fixture.service._write(path,record)
                if not enabled:
                    config=copy.deepcopy(fixture.runner.config);config.pop('completion_recovery');fixture.runner.config=config
                connection,journal=self.serve(fixture,name);file,value=self.inspect_file(fixture,connection,journal,name)
                view=value['inspection'];self.assertEqual(view['state'],'ineligible')
                self.assertEqual(view['reason_code'],'original_job_already_complete')
                self.assertEqual(view['next_actions'],['inspect_original_job','learning_status'])
                self.assertFalse(view['current_evidence_verified']);self.assertNotIn('candidate_sha256',view)
                code,value=self.cli(connection,journal,self.adopt_args(fixture,file));self.assertEqual(code,2,value)
                self.assertEqual(value['inspection']['reason_code'],'original_job_already_complete')
                self.assertIsNone(OperationJournal(journal).read('owner-adopt'))
    def test_malformed_original_receipts_remain_typed_hold_without_dispatch(self):
        for malformed in ('steps','gradients','timing','checkpoint','top-level'):
            with self.subTest(malformed=malformed):
                fixture=self.fixture('bad-'+malformed);raw=copy.deepcopy(fixture.raw)
                if malformed=='steps':raw['steps']=[1]
                elif malformed=='gradients':raw['steps'][0]['gradients']=[1]
                elif malformed=='timing':raw['steps'][0]['timing']=1
                elif malformed=='checkpoint':raw['optimizer_checkpoint']=[1]
                else:raw=[1]
                (fixture.folder/'stdout-private.json').write_text(json.dumps(raw)+'\n')
                connection,journal=self.serve(fixture,malformed)
                code,value=self.cli(connection,journal,['inspect-completion',fixture.job]);self.assertEqual(code,0,value)
                view=value['inspection'];self.assertEqual(view['state'],'ineligible');self.assertEqual(view['reason_code'],'original_evidence_invalid')
                self.assertEqual(view['next_actions'],['hold']);self.assertFalse(view['current_evidence_verified'])
                self.assertEqual(fixture.service.job(fixture.job)['state'],'interrupted');self.assertIsNone(OperationJournal(journal).read('owner-adopt'))

    def test_actual_busy_worker_returns_typed_hold(self):
        import fcntl
        fixture=self.fixture();connection,journal=self.serve(fixture)
        with (fixture.service.root/'worker.lock').open('r+b') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            code,value=self.cli(connection,journal,['inspect-completion',fixture.job])
        self.assertEqual(code,0,value);view=value['inspection']
        self.assertEqual(view['state'],'unavailable');self.assertEqual(view['reason_code'],'training_boundary_busy');self.assertEqual(view['next_actions'],['hold'])
    def test_actual_learning_reconcile_lost_ack_uses_same_step_before_changed_phase(self):
        harness=self.fixtures.NativeCompletionTests('test_original_complete_evidence_inspection_and_explicit_adoption_never_dispatch')
        harness.setUp();self.fixture_cleanups.append(harness.doCleanups)
        fixture=harness.learning_fixture('bw-original-learning');connection,journal=self.serve(fixture,'learning')
        code,status=self.cli(connection,journal,['learning-status','bw-original-learning']);self.assertEqual(code,0,status)
        self.assertEqual(status['phase'],'needs_operator');self.assertEqual(status['revision'],5)
        original=HTTPTransport.request;calls=[];lost=[False];lost_get=[False]
        def request(transport,method,path,body=None,**kwargs):
            calls.append((method,path))
            if method=='GET' and path=='/cow/training/operations/original-recovery-step' and lost[0] and not lost_get[0]:
                lost_get[0]=True;raise OperationIndeterminate('Controlled first metadata status unavailable')
            result=original(transport,method,path,body,**kwargs)
            if method=='POST' and path=='/cow/training/learning-steps' and not lost[0]:
                lost[0]=True;raise OperationIndeterminate('Controlled committed original learning acknowledgment loss')
            return result
        args=['reconcile-completion','bw-original-learning','--operation-id','original-recovery-step','--expected-revision','5']
        with mock.patch.object(HTTPTransport,'request',request):
            code,value=self.cli(connection,journal,args);self.assertEqual(code,2,value)
            self.assertEqual(OperationJournal(journal).read('original-recovery-step')['state'],'pending')
            self.assertEqual(fixture.service.learning_run('bw-original-learning')['phase'],'candidate_pending')
            count=len(calls);code,ack=self.cli(connection,journal,args);self.assertEqual(code,0,ack)
            self.assertEqual(calls[count:],[('GET','/cow/training/operations/original-recovery-step')])
        self.assertEqual(sum(m=='POST' for m,p in calls),1);self.assertEqual(ack['step_id'],'original-recovery-step')
        code,status=self.cli(connection,journal,['learning-status','bw-original-learning']);self.assertEqual(code,0,status)
        self.assertEqual(status['phase'],'candidate_pending');self.assertEqual(status['training_job_id'],fixture.job)
        self.assertEqual(self.dispatch,[])


if __name__=='__main__':unittest.main()
