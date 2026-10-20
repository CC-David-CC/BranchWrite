"""Protected feature acceptance: avoid repeated subtree walks, retain exact grants."""
import tempfile,unittest,os
from pathlib import Path
from unittest.mock import patch
from branchwrite.project_scope import expand_directories
class ScopeOverlapTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup)
  self.root=Path(self.t.name)
  for n in ['pkg/a.py','pkg/sub/b.py','pkg/sub/deep/c.py','pkg_extra/d.py']:
   p=self.root/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('pass')
 def measured(self,scopes):
  original=os.fwalk;calls=[]
  def walk(*args,**kwargs):
   calls.append((args,kwargs))
   yield from original(*args,**kwargs)
  with patch('branchwrite.project_scope.os.fwalk',side_effect=walk):
   result=expand_directories(self.root,scopes)
  return result,len(calls)
 def test_ancestor_scopes_walk_the_union_once(self):
  result,calls=self.measured(['pkg/sub/deep','pkg','pkg/sub','pkg'])
  self.assertEqual(result,['pkg/a.py','pkg/sub/b.py','pkg/sub/deep/c.py'])
  self.assertEqual(calls,1)
 def test_root_scope_covers_all_named_children(self):
  result,calls=self.measured(['pkg/sub','pkg_extra','.','pkg'])
  self.assertEqual(result,['pkg/a.py','pkg/sub/b.py','pkg/sub/deep/c.py','pkg_extra/d.py'])
  self.assertEqual(calls,1)
 def test_sibling_name_prefix_is_not_ancestry(self):
  result,calls=self.measured(['pkg_extra','pkg'])
  self.assertEqual(result,['pkg/a.py','pkg/sub/b.py','pkg/sub/deep/c.py','pkg_extra/d.py'])
  self.assertEqual(calls,2)
 def test_invalid_explicit_scope_is_not_hidden_by_root(self):
  for bad in ['../outside','/tmp','.git','pkg/../pkg']:
   with self.subTest(bad=bad),self.assertRaises((ValueError,OSError)):
    expand_directories(self.root,['.',bad])
 def test_empty_scopes_do_no_walk(self):
  self.assertEqual(self.measured([]),([],0))
