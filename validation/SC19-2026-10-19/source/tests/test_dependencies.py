import unittest
from dependencies import build_order
class OrderTests(unittest.TestCase):
 def test_empty(self): self.assertEqual(build_order({}),[])
 def test_chain(self): self.assertEqual(build_order({'app':['lib'],'lib':['base'],'base':[]}),['base','lib','app'])
 def test_ready_tie(self): self.assertEqual(build_order({'z':[],'b':['a'],'a':[]}),['a','b','z'])
 def test_dependency_only(self): self.assertEqual(build_order({'app':['lib']}),['lib','app'])
 def test_duplicates(self): self.assertEqual(build_order({'b':['a','a'],'a':[]}),['a','b'])
 def test_cycle(self):
  with self.assertRaises(ValueError): build_order({'a':['b'],'b':['a']})
 def test_self_cycle(self):
  with self.assertRaises(ValueError): build_order({'a':['a']})
 def test_no_mutation(self):
  g={'b':['a','a'],'a':[]};build_order(g);self.assertEqual(g,{'b':['a','a'],'a':[]})
