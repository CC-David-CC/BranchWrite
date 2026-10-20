"""Model-independent real browser action boundary; no workload answers."""
import hashlib,os
from pathlib import Path
import unittest
import branchwrite.browser_capture as capture

PAGE=b'<!doctype html><meta charset="utf-8"><body><button id="inc">Add</button><output id="n">0</output><input id="name"><button id="greet">Greet</button><output id="out"></output><script>let n=0;document.getElementById(\'inc\').onclick=()=>document.getElementById(\'n\').textContent=String(++n);document.getElementById(\'greet\').onclick=()=>document.getElementById(\'out\').textContent=\'Hello \'+document.getElementById(\'name\').value;</script></body>'

class PageActionTests(unittest.TestCase):
 def action(self,*args):return capture.PageAction(*args)
 def config(self,actions=()):return capture.BrowserConfig(Path(os.environ['BW_BROWSER_EXECUTABLE']),actions=actions)
 def test_invalid_action_is_rejected(self):
  for args in [('eval','inc',''),('click','../outside',''),('click','inc','value'),('click','inc',None),('fill','name','x'*4097),('fill','name',7),('click','inc bad','')]:
   with self.subTest(args=str(args)[:60]):
    with self.assertRaises(ValueError):self.action(*args)
 def test_action_tuple_and_count_are_bounded(self):
  a=self.action('click','inc','')
  for actions in [[a],(a,)*17,('click',)]:
   with self.assertRaises(ValueError):self.config(actions)
 def test_no_actions_preserves_static_pixels(self):
  a=capture.render_snapshot(PAGE,self.config())
  b=capture.render_snapshot(PAGE,self.config())
  self.assertEqual(a.png,b.png);self.assertEqual(a.actions,());self.assertEqual(a.text,'')
 def test_real_clicks_and_fill_return_resulting_pixels_and_text(self):
  actions=(self.action('click','inc',''),self.action('fill','name','<b>safe</b>'),self.action('click','greet',''))
  result=capture.render_snapshot(PAGE,self.config(actions))
  self.assertEqual(result.actions,tuple(a.wire for a in actions));self.assertIn('Hello <b>safe</b>',result.text)
  self.assertIn('1',result.text);self.assertEqual(result.served_sha256,hashlib.sha256(PAGE).hexdigest())
  self.assertNotEqual(result.png,capture.render_snapshot(PAGE,self.config()).png)
  self.assertTrue(result.isolation['worker_exited']);self.assertEqual(result.isolation['namespace_members_after'],[])
 def test_independent_sequences_do_not_inherit_clicks(self):
  one=(self.action('click','inc',''),);two=one+one
  a=capture.render_snapshot(PAGE,self.config(two));b=capture.render_snapshot(PAGE,self.config(one))
  self.assertIn('2',a.text);self.assertIn('1',b.text);self.assertNotIn('2',b.text)
 def test_missing_target_is_not_a_successful_capture(self):
  with self.assertRaisesRegex(ValueError,'unique'):
   capture.render_snapshot(PAGE,self.config((self.action('click','absent',''),)))
 def test_duplicate_target_is_rejected(self):
  with self.assertRaisesRegex(ValueError,'unique'):
   capture.render_snapshot(PAGE+b'<button id="inc">Other</button>',self.config((self.action('click','inc',''),)))
 def test_navigation_is_not_a_successful_capture(self):
  page=PAGE+b'<a id="leave" href="https://example.invalid/">Leave</a>'
  with self.assertRaisesRegex(ValueError,'resource|navigation|source'):
   capture.render_snapshot(page,self.config((self.action('click','leave',''),)))
 def test_protected_inspection_is_not_a_model_action(self):
  check=capture.PageInspection(Path('/not-mounted/check.py'),'0'*64,'H06')
  with self.assertRaisesRegex(ValueError,'inspection'):
   capture.BrowserConfig(Path(os.environ['BW_BROWSER_EXECUTABLE']),inspection=check,actions=(self.action('click','inc',''),))
 def test_unicode_values_survive_bounded_worker_framing(self):
  name='\U0001f42e'*1000
  actions=(self.action('fill','name',name),self.action('click','greet',''))
  result=capture.render_snapshot(PAGE,self.config(actions))
  self.assertEqual(result.actions,tuple(a.wire for a in actions));self.assertIn(name,result.text)
 def test_action_text_is_bounded_and_source_bytes_unchanged(self):
  page=PAGE+b'<p>'+b'z'*12000+b'</p>';before=hashlib.sha256(page).hexdigest()
  result=capture.render_snapshot(page,self.config((self.action('click','inc',''),)))
  self.assertLessEqual(len(result.text),8192);self.assertEqual(hashlib.sha256(page).hexdigest(),before)
if __name__=='__main__':unittest.main()
