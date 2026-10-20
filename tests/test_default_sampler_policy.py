"""Owner's greedy-first policy for new runs; explicit saved settings stay exact."""
import unittest
from branchwrite.coding_defaults import generation_profile

class DefaultSamplerPolicyTests(unittest.TestCase):
 def test_new_generation_is_greedy_without_repetition_or_probability_filters(self):
  self.assertEqual(generation_profile()['settings'],dict(temperature=0.0,min_p=0.0,top_k=0,top_p=1.0,dry_multiplier=0.0,dry_base=1.75,dry_allowed_length=2,dry_penalty_last_n=256))
 def test_min_p_fallback_is_explicit_and_has_no_dry_top_k_or_top_p(self):
  self.assertEqual(generation_profile('min-p')['settings'],dict(temperature=0.7,min_p=0.05,top_k=0,top_p=1.0,dry_multiplier=0.0,dry_base=1.75,dry_allowed_length=2,dry_penalty_last_n=256))
 def test_explicit_dry_fallback_preserves_the_previously_selected_preset(self):
  self.assertEqual(generation_profile('dry-min-p')['settings'],dict(temperature=0.7,min_p=0.05,top_k=60,top_p=0.95,dry_multiplier=0.8,dry_base=1.75,dry_allowed_length=2,dry_penalty_last_n=256))
 def test_profiles_are_fresh_and_unknown_names_do_not_silently_choose_a_sampler(self):
  p=generation_profile();p['settings']['temperature']=9
  self.assertEqual(generation_profile()['settings']['temperature'],0)
  with self.assertRaises(ValueError):generation_profile('unknown')
