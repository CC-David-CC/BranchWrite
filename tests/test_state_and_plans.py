import unittest
from dataclasses import replace, FrozenInstanceError
from reference.state import DecodeState, draw
from reference.plans import freeze, compatible, eligible_together
from reference.codec import encode

class StateTests(unittest.TestCase):
    def setUp(self):
        self.s=DecodeState('native-1','grammar-1',b'ACT ','explore',b'seed',dry_history=(1,2,1))
    def test_exact_clone_draws_match(self):self.assertEqual(draw(self.s.clone(),'dist'),draw(self.s.clone(),'dist'))
    def test_advancing_a_does_not_advance_b(self):
        a,b=self.s.clone(),self.s.clone();expected=draw(b,'dist')
        for _ in range(20):_,a=draw(a,'dist')
        self.assertEqual(draw(b,'dist'),expected)
    def test_seed_split_distinct(self):self.assertNotEqual(self.s.explore('a').rng_key,self.s.explore('b').rng_key)
    def test_seed_split_stable(self):self.assertEqual(self.s.explore('a'),self.s.explore('a'))
    def test_profile_change_recorded(self):self.assertEqual(self.s.explore('a',profile='xtc').profile_ref,'xtc')
    def test_dry_history_preserved(self):self.assertEqual(self.s.explore('a').dry_history,(1,2,1))
    def test_feedback_preserved(self):
        s=replace(self.s,mirostat_mu=4.1,adaptive_ema=.3)
        self.assertEqual(DecodeState.unpack(s.packed()),s)
    def test_consumed_rng_roundtrip(self):
        _,s=draw(self.s,'xtc');_,s=draw(s,'dist')
        restored=DecodeState.unpack(s.packed())
        self.assertEqual(draw(restored,'dist'),draw(s,'dist'))
    def test_component_streams_separate(self):
        before,_=draw(self.s,'dist');_,advanced=draw(self.s,'xtc')
        after,_=draw(advanced,'dist');self.assertEqual(before,after)
    def test_probe_draw_is_provisional(self):
        _,a=draw(self.s,'dist');_,b=draw(self.s,'dist')
        self.assertEqual(a,b);self.assertEqual(self.s.counters,())
    def test_invariant_under_interleaving(self):
        def run(order):
            state={k:self.s.explore(k) for k in 'ab'};out={'a':[],'b':[]}
            for k in order:
                x,state[k]=draw(state[k],'dist');out[k].append(x)
            return out,state
        self.assertEqual(run('aaaabbbb'),run('abababab'))
    def test_snapshot_immutable(self):
        with self.assertRaises(FrozenInstanceError):self.s.prefix=b'new'
    def test_stop_blocks_draw(self):
        with self.assertRaises(ValueError):draw(replace(self.s,stop_state='stopped'),'dist')
    def test_bad_version_rejected(self):
        with self.assertRaises(ValueError):DecodeState.unpack(encode(('wrong',)))
    def test_bad_prefix_type(self):
        with self.assertRaises(ValueError):replace(self.s,prefix='ACT ')
    def test_bool_not_rng_counter(self):
        with self.assertRaises(ValueError):replace(self.s,counters=(('dist',True),))
    def test_unknown_state_rejected(self):
        with self.assertRaises(ValueError):replace(self.s,stop_state='unknown')
    def test_empty_split_rejected(self):
        with self.assertRaises(ValueError):self.s.explore('')

class PlanTests(unittest.TestCase):
    def setUp(self):
        self.v={'source':'S0','a':'A0','b':'B0','policy':'P0'}
        self.a=freeze('ACT','world-a','none',self.v,('source','a','policy'),(('world-a/src/x','write'),))
        self.b=freeze('ACT','world-b','none',self.v,('source','b','policy'),(('world-b/src/x','write'),))
        self.grants={self.a.digest,self.b.digest};self.scopes={'world-a','world-b'}
    def test_unrelated_sibling_progress_not_stale(self):
        v=dict(self.v,a='A1',global_head='event-77');self.assertTrue(self.b.fresh(v))
    def test_shared_source_change_stales_both(self):
        v=dict(self.v,source='S1');self.assertFalse(self.a.fresh(v));self.assertFalse(self.b.fresh(v))
    def test_missing_dependency_stale(self):self.assertFalse(self.a.fresh({}))
    def test_order_independent_plan_digest(self):
        p=freeze('ACT','world-a','none',dict(reversed(list(self.v.items()))),('policy','a','source'),(('world-a/src/x','write'),))
        self.assertEqual(p.digest,self.a.digest)
    def test_profile_changes_identity(self):self.assertNotEqual(replace(self.a,profile='changed').digest,self.a.digest)
    def test_same_relative_path_compatible(self):self.assertTrue(compatible(self.a,self.b))
    def test_shared_physical_write_conflict(self):
        self.assertFalse(compatible(replace(self.a,claims=(('db','write'),)),replace(self.b,claims=(('db','read'),))))
    def test_shared_reads_compatible(self):
        self.assertTrue(compatible(replace(self.a,claims=(('source','read'),)),replace(self.b,claims=(('source','read'),))))
    def test_eligible_parallel(self):self.assertTrue(eligible_together((self.a,self.b),self.v,self.grants,self.scopes,2))
    def test_capacity_not_multiplied(self):self.assertFalse(eligible_together((self.a,self.b),self.v,self.grants,self.scopes,1))
    def test_unknown_reservation_retained(self):self.assertFalse(eligible_together((self.a,self.b),self.v,self.grants,self.scopes,2,reserved=1))
    def test_missing_grant(self):self.assertFalse(eligible_together((self.a,self.b),self.v,{self.a.digest},self.scopes,2))
    def test_unqualified_scope(self):self.assertFalse(eligible_together((self.a,self.b),self.v,self.grants,{'world-a'},2))
    def test_duplicate_dispatch_rejected(self):self.assertFalse(eligible_together((self.a,self.a),self.v,self.grants,self.scopes,2))
    def test_unknown_future_dependency(self):
        with self.assertRaises(ValueError):freeze('ACT','world','none',self.v,('future',))
    def test_duplicate_dependency_rejected(self):
        with self.assertRaises(ValueError):freeze('ACT','world','none',self.v,('source','source'))
    def test_invalid_claim_rejected(self):
        with self.assertRaises(ValueError):freeze('ACT','world','none',self.v,('source',),(('x','grant'),))
    def test_negative_capacity_rejected(self):
        with self.assertRaises(ValueError):eligible_together((self.a,),self.v,self.grants,self.scopes,-1)
