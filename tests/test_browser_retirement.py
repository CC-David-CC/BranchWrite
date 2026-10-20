"""A bounded wait must prove actual namespace absence, never assume it."""
import unittest
from unittest.mock import patch

class RetirementTests(unittest.TestCase):
 def test_immediate_absence_needs_no_sleep(self):
  from branchwrite.browser_isolation import await_namespace_retirement
  with patch('branchwrite.browser_isolation.namespace_members',return_value=[]),patch('branchwrite.browser_isolation.time.sleep',side_effect=AssertionError('already absent')):
   self.assertEqual(await_namespace_retirement('pid:[123]'),[])
 def test_delayed_kernel_retirement_is_observed_before_success(self):
  from branchwrite.browser_isolation import await_namespace_retirement
  clock=[0.]
  def sleep(n):clock[0]+=n
  with patch('branchwrite.browser_isolation.namespace_members',side_effect=[[42],[42],[]]) as scan,patch('branchwrite.browser_isolation.time.monotonic',side_effect=lambda:clock[0]),patch('branchwrite.browser_isolation.time.sleep',side_effect=sleep):
   self.assertEqual(await_namespace_retirement('pid:[123]'),[])
   self.assertEqual(scan.call_count,3)
   self.assertGreaterEqual(clock[0],.02)
 def test_persistent_member_is_returned_as_failure_within_bound(self):
  from branchwrite.browser_isolation import await_namespace_retirement
  clock=[0.]
  def sleep(n):clock[0]+=n
  with patch('branchwrite.browser_isolation.namespace_members',return_value=[42]),patch('branchwrite.browser_isolation.time.monotonic',side_effect=lambda:clock[0]),patch('branchwrite.browser_isolation.time.sleep',side_effect=sleep):
   self.assertEqual(await_namespace_retirement('pid:[123]',timeout=.05),[42])
   self.assertLessEqual(clock[0],.051)

if __name__=='__main__':unittest.main()
