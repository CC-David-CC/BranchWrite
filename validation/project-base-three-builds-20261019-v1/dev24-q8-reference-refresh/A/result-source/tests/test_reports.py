import unittest
from outcomes import summarize
from formatter import render_summary
class Reports(unittest.TestCase):
 def test_mixed(self):self.assertEqual(summarize([{"exit_code":0},{"exit_code":2},{"exit_code":-9}]),dict(total=3,passed=1,failed=2))
 def test_empty(self):self.assertEqual(summarize([]),dict(total=0,passed=0,failed=0))
 def test_render(self):self.assertEqual(render_summary([{"exit_code":0}]),"1 runs: 1 passed, 0 failed")
 def test_invalid(self):
  for x in [None,{},[{}],[{"exit_code":True}],[{"exit_code":"0"}]]:
   with self.subTest(x=x),self.assertRaises(ValueError):summarize(x)
 def test_no_mutation(self):
  x=[{"exit_code":1,"extra":[4]}];self.assertEqual(summarize(x),dict(total=1,passed=0,failed=1));self.assertEqual(x,[{"exit_code":1,"extra":[4]}])
