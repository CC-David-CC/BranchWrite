"""The interactive client admits user intents through FrameKernel, not a shadow transcript."""
import tempfile,unittest
from pathlib import Path

class SessionLedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.project=self.root/'project';self.project.mkdir()
        from branchwrite.session_ledger import SessionLedger,Inbox
        self.Session=SessionLedger;self.inbox=Inbox(self.root/'session')
        self.connection=dict(endpoint_url='http://127.0.0.1:1',endpoint_pin='test',model_contract_id='m',execution_profile_id='p',eos_tokens=[1])
    def open(self):return self.Session(self.project,self.root/'session',self.connection)
    def test_queue_is_durable_and_combines_followups_in_order(self):
        self.inbox.put('one','Make it blue.',mode='work',kind='queue')
        self.inbox.put('two','And larger. ?',mode='work',kind='queue')
        with self.open() as session:
            frame=session.admit()
            self.assertEqual(frame['input']['message'],'Make it blue.\n\nAnd larger. ?')
            self.assertEqual(frame['input']['item_ids'],['one','two'])
            self.assertEqual(self.inbox.rows(),[])
        with self.open() as session:
            resumed=session.pending()
            self.assertEqual(resumed['id'],frame['id'])
            self.assertEqual(resumed['input'],frame['input'])
    def test_same_id_never_means_different_work(self):
        self.inbox.put('same','First',mode='work',kind='queue')
        self.inbox.put('same','First',mode='work',kind='queue')
        self.assertEqual(len(self.inbox.rows()),1)
        with self.assertRaisesRegex(ValueError,'different'):
            self.inbox.put('same','Second',mode='work',kind='queue')
    def test_aside_completion_cannot_move_current_tip_files_or_mode(self):
        self.inbox.put('main','Build it',mode='work',kind='send')
        with self.open() as session:
            f=session.admit();session.finish(f['id'],dict(status='finished',context={'tip':'a'},file_commit='one',mode='work',workdir=str(self.project),answer='Done'))
            before=session.current()
            self.inbox.put('aside','What is CSS?',mode='aside',kind='send')
            f=session.admit();session.finish(f['id'],dict(status='finished',context={'tip':'other'},file_commit='other',mode='aside',workdir='/other',answer='Styling'))
            self.assertEqual(session.current(),before)
            self.assertEqual(len(session.history()),2)
    def test_modes_do_not_blend_or_reorder_queue(self):
        self.inbox.put('plan','Explain first',mode='plan',kind='queue')
        self.inbox.put('work','Then build',mode='work',kind='queue')
        with self.open() as session:
            f=session.admit();self.assertEqual(f['input']['mode'],'plan')
            self.assertEqual([r['id'] for r in self.inbox.rows()],['work'])
            with self.assertRaisesRegex(ValueError,'pending'):
                session.admit()
    def test_connection_change_refused_on_resume(self):
        with self.open():pass
        changed=dict(self.connection,execution_profile_id='new')
        with self.assertRaisesRegex(ValueError,'different'):
            with self.Session(self.project,self.root/'session',changed):pass
    def test_search_is_read_only_and_never_dispatches(self):
        self.inbox.put('first','Make a blue heading',mode='work',kind='send')
        with self.open() as session:
            f=session.admit();session.finish(f['id'],{'status':'finished','answer':'Done'})
            before=session.log.event_count
            found=session.search('blue')
            self.assertEqual(len(found),1);self.assertIn('blue',found[0]['input']['message'])
            self.assertEqual(session.log.event_count,before)
    def test_pending_receipt_replays_without_duplicate_completion(self):
        self.inbox.put('first','Build',mode='work',kind='send')
        with self.open() as session:
            f=session.admit();session.finish(f['id'],{'status':'finished','answer':'Done'})
            count=session.log.event_count
            session.finish(f['id'],{'status':'finished','answer':'Done'})
            self.assertEqual(session.log.event_count,count)
            with self.assertRaises(ValueError):session.finish(f['id'],{'status':'finished','answer':'Changed'})
