"""Actual local CPU coordinator/HTTP replay tests; not GPU qualification."""
import unittest,json
from dataclasses import replace
import test_cow_client_flow as fixture
from branchwrite.cow_client import OperationIndeterminate,ReceiptError,COWSourceBinding

class CowRetryReplayTests(unittest.TestCase):
    def setUp(self):
        self.case=fixture.CowClientFlowTests();self.addCleanup(self.case.doCleanups);self.case.setUp()
        # This byte-token CPU fixture predates replay's explicit vocabulary check.
        for model in self.case.models.values():model.vocab_size=300
        self.client=self.case._client('http','retry')
        n=self.client.create_namespace('Retry tests','retry-namespace')['namespace_id']
        p=self.client.prepare('main',n,'Question','retry-prepare')
        self.answer=self.client.answer('main',p.receipt.branch.revision,'ask-a',2)

    def test_saved_answer_retry_keeps_revision_and_reopens_locally(self):
        c=self.client;head=c.head('main');trace=list(self.case.trace)
        value=c.retry_saved('ask-a','main',head.revision,'same-answer-retry')
        self.assertEqual(value.answer['text'],self.answer.answer['text'])
        self.assertEqual(value.receipt.snapshot,self.answer.receipt.snapshot)
        self.assertEqual(c.head('main'),head);self.assertEqual(self.case.trace,trace)
        saved=c.read_completed_generation('same-answer-retry')
        self.assertEqual(saved.answer,value.answer)
        self.assertEqual(saved.receipt.snapshot,value.receipt.snapshot)

    def test_replay_old_answer_does_not_rewind_an_advanced_branch(self):
        c=self.client;head=c.head('main')
        c.append_user('main',head.revision,'user-op','Another question',2)
        head=c.head('main');trace=list(self.case.trace)
        value=c.retry_saved('ask-a','main',head.revision,'old-answer-retry')
        self.assertEqual(value.receipt.snapshot,self.answer.receipt.snapshot)
        self.assertEqual(c.head('main'),head);self.assertEqual(self.case.trace,trace)
        self.assertEqual(c.read_completed_generation('old-answer-retry').answer,value.answer)

    def test_lost_replay_ack_recovers_original_bytes_without_new_compute(self):
        c=self.client;head=c.head('main');trace=list(self.case.trace);original=c.transport.request
        def lose(method,path,body=None,**kwargs):
            response=original(method,path,body,**kwargs)
            if method=='POST' and path=='/cow/text/retry':raise OperationIndeterminate('lost completion')
            return response
        c.transport.request=lose
        with self.assertRaises(OperationIndeterminate):c.retry_saved('ask-a','main',head.revision,'lost-retry')
        c.transport.request=original
        recovered=c.reconcile_generation('lost-retry')
        self.assertEqual(recovered.answer['text'],self.answer.answer['text'])
        self.assertEqual(c.head('main'),head);self.assertEqual(self.case.trace,trace)

    def test_replayed_flag_cannot_substitute_a_different_snapshot_or_root(self):
        c=self.client;head=c.head('main');request=c.transport.request
        for field in ['snapshot','root']:
            def corrupt(method,path,body=None,**kw):
                response=request(method,path,body,**kw)
                if method=='POST' and path=='/cow/text/retry':
                    events=json.loads(json.dumps(response.events));receipt=events[0]['receipt']
                    if field=='snapshot':receipt['snapshot']='d'*64;receipt['branch']['tip']='d'*64
                    else:receipt['branch']['root']='d'*64
                    response=replace(response,events=tuple(events))
                return response
            c.transport.request=corrupt
            with self.subTest(field=field),self.assertRaises(ReceiptError):
                c.retry_saved('ask-a','main',head.revision,'bad-'+field)
            self.assertEqual(c.journal.read('bad-'+field)['state'],'pending')
        c.transport.request=request
        self.assertEqual(c.head('main'),head)

    def test_changed_unknown_retry_is_not_resent_during_reconciliation(self):
        c=self.client;head=c.head('main');op='changed-unknown'
        body=dict(from_operation='ask-a',operation_id=op,branch='main',revision=head.revision,
                  stream=True,settings=dict(temperature=.7))
        binding=COWSourceBinding(op,'main','main',head.revision,head.tip,c.endpoint_pin)
        intent=c._intent(op,'POST','/cow/text/retry',body,'main',head.revision,None,binding)
        c.journal.begin(intent,c.endpoint_url);request=c.transport.request;posts=[]
        def record(method,path,body=None,**kw):
            if method=='POST':posts.append(path)
            return request(method,path,body,**kw)
        c.transport.request=record
        with self.assertRaises(OperationIndeterminate):c.reconcile_generation(op)
        self.assertEqual(posts,[]);self.assertEqual(c.journal.read(op)['state'],'pending')
