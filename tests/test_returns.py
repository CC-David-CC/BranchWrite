import unittest, tempfile
from pathlib import Path
from reference.codec import encode, decode
from reference.returns import reduce

class ReturnTests(unittest.TestCase):
    def setUp(self):
        self.wait=('wait','parent',1,'a','child-a','ObservedResult')
        self.ret=('return','parent',1,'a','child-a','ObservedResult','digest-a',True)
        self.resume=('resume','parent',1)
    def test_wait_not_result(self):self.assertEqual(reduce((self.wait,)).slots,())
    def test_named_return(self):self.assertEqual(reduce((self.wait,self.ret)).slots,((('parent',1,'a'),'digest-a'),))
    def test_identical_return_idempotent(self):
        a=reduce((self.wait,self.ret));b=reduce((self.wait,self.ret,self.ret));self.assertEqual(a.slots,b.slots)
    def test_duplicate_resume_once(self):
        p=reduce((self.wait,self.ret,self.resume,self.resume));self.assertEqual(len(p.resumed),1)
    def test_retired_child_history_retained(self):
        p=reduce((self.wait,self.ret,self.resume));self.assertIn(self.ret,p.history)
    def test_crash_boundary_codec_and_reconstruction(self):
        events=(self.wait,self.ret)
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'reference-events.bwl';path.write_bytes(encode(events))
            restored=decode(path.read_bytes())
            self.assertEqual(restored,events)
            before=reduce(restored);self.assertFalse(before.resumed)
            after=reduce(restored+(self.resume,))
            self.assertEqual(len(after.resumed),1);self.assertEqual(after.history.count(self.ret),1)
    def test_siblings_reverse_completion(self):
        w2=('wait','parent',1,'b','child-b','ObservedResult')
        r2=('return','parent',1,'b','child-b','ObservedResult','digest-b',True)
        a=reduce((self.wait,w2,self.ret,r2,self.resume));b=reduce((self.wait,w2,r2,self.ret,self.resume))
        self.assertEqual(a.slots,b.slots);self.assertEqual(a.resumed,b.resumed)
    def test_parent_waits_for_both(self):
        w2=('wait','parent',1,'b','child-b','ObservedResult')
        with self.assertRaises(ValueError):reduce((self.wait,w2,self.ret,self.resume))
    def test_late_old_epoch_quarantined(self):
        new=('wait','parent',2,'a','new-child','ObservedResult')
        p=reduce((self.wait,new,self.ret));self.assertEqual(p.slots,());self.assertEqual(p.quarantined,(self.ret,))
    def test_conflicting_return(self):
        bad=self.ret[:-2]+('different',True)
        with self.assertRaises(ValueError):reduce((self.wait,self.ret,bad))
    def test_wrong_child(self):
        bad=list(self.ret);bad[4]='evil'
        with self.assertRaises(ValueError):reduce((self.wait,tuple(bad)))
    def test_wrong_type(self):
        bad=list(self.ret);bad[5]='ModelClaim'
        with self.assertRaises(ValueError):reduce((self.wait,tuple(bad)))
    def test_wrong_slot(self):
        bad=list(self.ret);bad[3]='another'
        with self.assertRaises(ValueError):reduce((self.wait,tuple(bad)))
    def test_unsettled_resources_cannot_return(self):
        with self.assertRaises(ValueError):reduce((self.wait,self.ret[:-1]+(False,)))
    def test_bool_integer_settlement_not_equivalent(self):
        with self.assertRaises(ValueError):reduce((self.wait,self.ret[:-1]+(1,)))
    def test_no_resume_without_wait(self):
        with self.assertRaises(ValueError):reduce((self.resume,))
    def test_unknown_event_rejected(self):
        with self.assertRaises(ValueError):reduce((('fake_success',),))
