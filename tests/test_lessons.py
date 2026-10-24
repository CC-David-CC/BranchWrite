"""Real BW lesson provenance and transport reconciliation; no GPU claims."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from branchwrite.cow_client import CowClient,OperationJournal,OperationIndeterminate,OperationReuseError,ReceiptError,_Response
from branchwrite.lesson_cli import create_lesson
from tests.lesson_flow_harness import task

class Lessons(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.connection=dict(endpoint_url='http://127.0.0.1:1',endpoint_pin='test',model_contract_id='a'*64,execution_profile_id='c'*64,eos_tokens=[256])
    def test_real_failed_check_correction_and_stale_inventory(self):
        failed=task(self.root/'failed',self.connection,corrected=False)
        corrected=task(self.root/'corrected',self.connection,corrected=True)
        lesson=create_lesson(failed,corrected,'double(n) = ','2*n','double','Use multiplication',self.connection['model_contract_id'])
        self.assertEqual(lesson['evidence']['method'],'bw-verified-correction-v1')
        self.assertNotEqual(lesson['evidence']['failed_result_sha256'],lesson['evidence']['corrected_result_sha256'])
        self.assertNotIn('9217',json.dumps(lesson))
        (corrected/'world/workspace/app.py').write_text('changed after verification')
        with self.assertRaises(ValueError):create_lesson(failed,corrected,'p','a','t','r','a'*64)
    def test_unverified_or_wrong_model_runs_cannot_be_used(self):
        failed=task(self.root/'failed',self.connection,corrected=False)
        with self.assertRaises(ValueError):create_lesson(failed,failed,'p','a','t','r','a'*64)
    def test_failure_and_repair_in_one_completed_bw_task(self):
        state=task(self.root/'loop',self.connection,corrected=True,include_failed_check=True)
        lesson=create_lesson(state,state,'Python double(n):',' 2*n','double','Checked correction','a'*64)
        self.assertNotEqual(lesson['evidence']['failed_result_sha256'],lesson['evidence']['corrected_result_sha256'])
    def test_interactive_default_never_selects_old_work_behind_an_unfinished_task(self):
        from branchwrite.lesson_cli import main
        output=[]
        history=[dict(input=dict(mode='work'),result=dict(workflow='/must-not-read',checks_passed=True,mode='work')),
                 dict(input=dict(mode='work'),result=None)]
        result=main(['--state-dir',str(self.root/'journal'),'create','--prompt','p','--completion','a'],
            output=output.append,connection_override=self.connection,session_history=history)
        self.assertEqual(result,2);self.assertIn('latest Work task',output[0])
    def test_interactive_author_uses_real_completed_work_and_writes_private_draft(self):
        from branchwrite.lesson_cli import main
        state=task(self.root/'loop',self.connection,corrected=True,include_failed_check=True);output=[]
        history=[dict(input=dict(mode='work'),result=dict(workflow=str(state),checks_passed=True,mode='work'))]
        result=main(['--state-dir',str(self.root/'journal'),'create','--prompt','Python double(n):','--completion',' 2*n','--operation-id','draft-one'],
            output=output.append,connection_override=self.connection,session_history=history)
        self.assertEqual(result,0,output);record=json.loads(output[0]);draft=Path(record['lesson_file'])
        self.assertEqual(draft.stat().st_mode&0o777,0o600);self.assertFalse(record['submitted'])
    def test_lost_acceptance_reads_original_and_never_posts_twice(self):
        calls=[];saved={}
        class Transport:
            name='injected-lost-response'
            def request(self,method,path,body=None,**kwargs):
                calls.append(method)
                if method=='POST':
                    value=json.loads(body)
                    from branchwrite.lesson_cli import digest
                    saved.update(schema=1,operation_id=value['operation_id'],request_sha256=digest([path,value]),lesson_id=digest(value['lesson']))
                    raise OperationIndeterminate('accepted, response lost')
                return _Response(json_value=dict(saved),transport='test')
        client=CowClient(Transport(),journal=OperationJournal(self.root/'journal'),endpoint_url='http://127.0.0.1:1')
        receipt=client.training_submit('lessons',dict(lesson={'owned':'fixture'}),'owned-lesson')
        self.assertEqual(calls,['POST','GET'])
        self.assertEqual(client.training_submit('lessons',dict(lesson={'owned':'fixture'}),'owned-lesson'),receipt)
        self.assertEqual(calls,['POST','GET'])
    def test_forged_training_acceptance_is_rejected(self):
        class Transport:
            name='forged'
            def request(self,*args,**kwargs):return _Response(json_value=dict(schema=1,operation_id='op',request_sha256='0'*64,job_id='op'),transport='test')
        client=CowClient(Transport(),journal=OperationJournal(self.root/'journal'),endpoint_url='http://127.0.0.1:1')
        with self.assertRaises(ReceiptError):client.training_submit('jobs',{},'op')

    def test_lost_model_preservation_acceptance_reconciles_without_second_post(self):
        calls=[];saved={}
        class Transport:
            name='owned-export-lost-response'
            def request(self,method,path,body=None,**kwargs):
                calls.append(method)
                if method=='POST':
                    value=json.loads(body)
                    from branchwrite.lesson_cli import digest
                    saved.update(schema=1,operation_id=value['operation_id'],request_sha256=digest([path,value]),
                        export_id='f'*64,name=value['name'],file=value['name']+'.gguf',
                        model_sha256=value['expected_sha256'],weights_published=False)
                    raise OperationIndeterminate('preserved, response lost')
                return _Response(json_value=dict(saved),transport='test')
        client=CowClient(Transport(),journal=OperationJournal(self.root/'journal'),endpoint_url='http://127.0.0.1:1')
        payload=dict(job_id='owned-job',name='OwnedModel',expected_sha256='a'*64,notes='Owned experiment',report_sha256=None)
        receipt=client.training_submit('exports',payload,'preserve')
        self.assertEqual(calls,['POST','GET'])
        self.assertEqual(client.training_submit('exports',payload,'preserve'),receipt)
        self.assertEqual(calls,['POST','GET'])
        with self.assertRaises(OperationReuseError):
            client.training_submit('exports',dict(payload,name='DifferentModel'),'preserve')
        self.assertEqual(calls,['POST','GET'])
    def test_forged_model_preservation_cannot_hide_different_weights(self):
        class Transport:
            name='forged-export'
            def request(self,method,path,body=None,**kwargs):
                value=json.loads(body)
                from branchwrite.lesson_cli import digest
                return _Response(json_value=dict(schema=1,operation_id=value['operation_id'],
                    request_sha256=digest([path,value]),export_id='e'*64,name=value['name'],
                    file=value['name']+'.gguf',model_sha256='b'*64,weights_published=False),transport='test')
        client=CowClient(Transport(),journal=OperationJournal(self.root/'journal'),endpoint_url='http://127.0.0.1:1')
        with self.assertRaises(ReceiptError):
            client.training_submit('exports',dict(job_id='owned-job',name='OwnedModel',
                expected_sha256='a'*64,notes='',report_sha256=None),'preserve')

if __name__=='__main__':unittest.main()
