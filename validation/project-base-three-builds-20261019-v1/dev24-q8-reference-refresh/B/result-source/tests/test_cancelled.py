import unittest
from outcomes import summarize
from formatter import render_summary
class Cancellation(unittest.TestCase):
 def test_mixed_cancel(self):
  x=[{"exit_code":0},{"exit_code":2},{"exit_code":None,"cancelled":True}]
  self.assertEqual(summarize(x,include_cancelled=True),dict(total=3,passed=1,failed=1,cancelled=1))
  self.assertEqual(render_summary(x,include_cancelled=True),"3 runs: 1 passed, 1 failed, 1 cancelled")
 def test_empty(self):self.assertEqual(summarize([],include_cancelled=True),dict(total=0,passed=0,failed=0,cancelled=0))
 def test_bad_cancel(self):
  for x in [[{"exit_code":0,"cancelled":True}],[{"exit_code":None}],[{"exit_code":0,"cancelled":1}]]:
   with self.subTest(x=x),self.assertRaises(ValueError):summarize(x,include_cancelled=True)
