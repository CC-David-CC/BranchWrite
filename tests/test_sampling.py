import unittest, math
from reference.sampling import *

def cs(ps):return tuple(Candidate(i,math.log(p)) for i,p in enumerate(ps))
class SamplingTests(unittest.TestCase):
    def setUp(self):self.c=cs([.60,.25,.10,.04,.01])
    def test_minp_example(self):self.assertEqual([c.token for c in min_p(self.c,.05)],[0,1,2,3])
    def test_minp_zero_identity(self):self.assertEqual(min_p(self.c,0),self.c)
    def test_minp_one_keeps_maxima(self):self.assertEqual(len(min_p(cs([.5,.5]),1)),2)
    def test_minp_argmax_preserved(self):self.assertEqual(greedy(min_p(self.c,.9)),greedy(self.c))
    def test_temperature_argmax_preserved(self):
        for t in [.01,.2,.7,2,100]:self.assertEqual(greedy(temperature(self.c,t)),0)
    def test_typical_can_remove_modal(self):
        out=typical(cs([.4,.2,.2,.2]),.5)
        self.assertNotIn(0,[c.token for c in out])
        self.assertNotEqual(greedy(out),0)
    def test_typical_one_identity(self):self.assertEqual(typical(self.c,1),self.c)
    def test_typical_positive_keeps_something(self):self.assertGreaterEqual(len(typical(self.c,.00001)),1)
    def test_typical_ignores_underflow_zeros(self):self.assertTrue(typical((Candidate(0,0),Candidate(1,-1e6)),.5))
    def test_dynatemp_uniform_at_max(self):
        _,t=dynatemp(cs([.25]*4),.55,.35,1)
        self.assertAlmostEqual(t,.9)
    def test_dynatemp_peaked_at_min(self):
        _,t=dynatemp((Candidate(0,0),Candidate(1,-1000)),.55,.35,1)
        self.assertAlmostEqual(t,.2)
    def test_dynatemp_singleton_defined(self):
        out,t=dynatemp((Candidate(7,0),),.55,.35,1)
        self.assertEqual(out,(Candidate(7,0),));self.assertAlmostEqual(t,.2)
    def test_dynatemp_exponent(self):
        _,a=dynatemp(self.c,.55,.35,1);_,b=dynatemp(self.c,.55,.35,2)
        self.assertLess(b,a)
    def test_dynatemp_span_zero_fixed(self):
        out,t=dynatemp(self.c,.7,0,1)
        self.assertEqual(out,temperature(self.c,.7));self.assertEqual(t,.7)
    def test_xtc_zero_no_draw(self):self.assertEqual(xtc(self.c,0,.15,None),self.c)
    def test_xtc_gate_not_triggered(self):self.assertEqual(xtc(self.c,.12,.15,.12),self.c)
    def test_xtc_excludes_top_choices(self):
        out=xtc(cs([.5,.3,.15,.05]),1,.14,0)
        self.assertEqual([c.token for c in out],[2,3])
    def test_xtc_insufficient_high_choices(self):self.assertEqual(xtc(self.c,1,.4,0),self.c)
    def test_xtc_minimum_floor(self):self.assertEqual(xtc(cs([.5,.3,.15,.05]),1,.14,0,min_keep=3),cs([.5,.3,.15,.05]))
    def test_xtc_threshold_equality(self):
        out=xtc(cs([.5,.5]),1,.5,0)
        self.assertEqual([c.token for c in out],[1])
    def test_xtc_singleton_survives(self):self.assertEqual(xtc((Candidate(8,0),),1,.1,None),(Candidate(8,0),))
    def test_distribution_cdf(self):
        c=cs([.5,.3,.2])
        self.assertEqual([distribution_select(c,x) for x in [0,.49,.51,.79,.81,.999]],[0,0,1,1,2,2])
    def test_mask_never_resurrects(self):
        c=mask({0:100,1:1,2:0},{1,2})
        a,_=dynatemp(c,.55,.35,1)
        for stage in [min_p(a,.05),typical(a,.95),xtc(a,1,.01,0)]:
            self.assertLessEqual({x.token for x in stage},{1,2})
    def test_temperature_and_minp_order_differs(self):
        c=cs([.8,.2])
        self.assertEqual(len(temperature(min_p(c,.1),.2)),2)
        self.assertEqual(len(min_p(temperature(c,.2),.1)),1)
    def test_greedy_tie_stable_id(self):self.assertEqual(greedy((Candidate(7,0),Candidate(2,0))),2)
    def test_probability_total(self):self.assertAlmostEqual(sum(p for _,p in probabilities(self.c)),1)
    def test_zero_probability_not_selected_roundoff(self):
        c=(Candidate(0,0),Candidate(1,-1e6))
        self.assertEqual(distribution_select(c,.99999999999),0)

BAD=[('minp_negative',lambda:min_p(cs([.5,.5]),-.1)),('minp_nan',lambda:min_p(cs([.5,.5]),math.nan)),
('minp_large',lambda:min_p(cs([.5,.5]),1.1)),('typical_zero',lambda:typical(cs([.5,.5]),0)),
('temperature_zero',lambda:temperature(cs([.5,.5]),0)),('temperature_inf',lambda:temperature(cs([.5,.5]),math.inf)),
('dynatemp_zero_bound',lambda:dynatemp(cs([.5,.5]),.3,.3,1)),('dynatemp_exponent',lambda:dynatemp(cs([.5,.5]),.7,.2,0)),
('xtc_bad_draw',lambda:xtc(cs([.5,.5]),1,.2,1)),('xtc_bad_minimum',lambda:xtc(cs([.5,.5]),1,.2,0,min_keep=0)),
('empty_candidates',lambda:greedy(())),('duplicate_tokens',lambda:greedy((Candidate(0,1),Candidate(0,2)))),
('nan_logits',lambda:mask({0:math.nan},{0})),('all_masked',lambda:mask({0:-math.inf},{0})),
('dist_draw_one',lambda:distribution_select(cs([.5,.5]),1)),('boolean_token',lambda:greedy((Candidate(True,1),)))]
for name,fn in BAD:
    def check(self,fn=fn):
        with self.assertRaises(ValueError):fn()
    setattr(SamplingTests,'test_reject_'+name,check)
