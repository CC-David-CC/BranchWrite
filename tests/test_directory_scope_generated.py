import unittest,tempfile,random,os
from pathlib import Path
from unittest.mock import patch
from branchwrite.project_scope import expand_directories
class IndependentScopeTests(unittest.TestCase):
 def test_seeded_scope_unions_and_minimal_walks(self):
  rng=random.Random(141019)
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp)
   files=['a/x.py','a/sub/y.py','a/sub/deep/z.py','a_extra/q.py','雪/r.py','雪/sub/s.py','b/t.py']
   for name in files:
    p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('pass')
   choices=['.','a','a/sub','a/sub/deep','a_extra','雪','雪/sub','b']
   for case in range(100):
    scopes=rng.choices(choices,k=rng.randrange(0,14))
    selected=set(scopes)
    minimal=[s for s in selected if not any(s!=p and (p=='.' or Path(p) in Path(s).parents) for p in selected)]
    expected=sorted(f for f in files if any(s=='.' or Path(s) in Path(f).parents for s in scopes))
    calls=[];walk=os.fwalk
    def observed(*args,**kwargs):
     calls.append(1);yield from walk(*args,**kwargs)
    with self.subTest(case=case),patch('branchwrite.project_scope.os.fwalk',side_effect=observed):
     self.assertEqual(expand_directories(root,scopes),expected)
     self.assertEqual(len(calls),len(minimal))
 def test_covered_invalid_scope_still_rejected(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);(root/'a').mkdir();(root/'a/x').write_text('x')
   for bad in ['a/../a','../no','/tmp','.git','a/.git']:
    with self.subTest(bad=bad),self.assertRaises((ValueError,OSError)):
     expand_directories(root,['.',bad])
