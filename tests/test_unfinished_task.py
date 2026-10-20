"""Short steering notes retain an unfinished original request at a prefix-only tip."""
import unittest

PREFIX=dict(branch='branch',tip='a'*64,root='a'*64,mode='context',model_contract_id='m',execution_profile_id='e',revision=0)
def row(id,message,prior=None,*,mode='work',status='interrupted',context=None):
 return dict(id=id,input=dict(message=message,mode=mode,source=dict(turn=prior)),
  result=dict(status=status,context=dict(PREFIX) if context is None else context))
class UnfinishedTaskTests(unittest.TestCase):
 def compose(self,history,message='Make it purple.',context=None,turn=None):
  from branchwrite.session_controls import unfinished_task
  source=dict(turn=turn or history[-1]['id'],context=dict(PREFIX) if context is None else context)
  return unfinished_task(history,source,message)
 def test_first_thought_keeps_original_goal_and_short_update(self):
  result=self.compose([row('one','Make a bird website.')])
  self.assertIn('Make a bird website.',result);self.assertIn('Make it purple.',result)
 def test_repeated_early_steering_keeps_notes_once_in_order(self):
  h=[row('one','Make a bird website.'),row('two','Make it purple.','one')]
  text=self.compose(h,'Make the button bigger.')
  for phrase in ('Make a bird website.','Make it purple.','Make the button bigger.'):
   self.assertEqual(text.count(phrase),1)
  self.assertLess(text.index('website'),text.index('purple'));self.assertLess(text.index('purple'),text.index('bigger'))
 def test_completed_model_context_does_not_repeat_original_request(self):
  self.assertEqual(self.compose([row('one','Old task')],context=dict(PREFIX,mode='append_user')),'Make it purple.')
 def test_different_saved_prefix_does_not_pull_in_unrelated_goal(self):
  h=[row('one','Unrelated task',context=dict(PREFIX,tip='b'*64)),row('two','New task','one')]
  text=self.compose(h);self.assertIn('New task',text);self.assertNotIn('Unrelated task',text)
 def test_edit_replacement_starts_its_own_intent_chain(self):
  h=[row('one','Old task'),row('two','1 Replacement task','one',mode='edit')]
  text=self.compose(h);self.assertIn('Replacement task',text);self.assertNotIn('Old task',text);self.assertNotIn('1 Replacement',text)
 def test_cycle_in_retained_source_pointers_is_rejected(self):
  with self.assertRaisesRegex(ValueError,'cycle'):self.compose([row('one','Task','one')])

 def test_existing_context_still_needs_the_new_unfinished_request(self):
  context=dict(PREFIX,mode='append_user')
  h=[row('one','Build a bird website.',context=context)]
  h[0]['result']['unfinished_request']=True
  text=self.compose(h,'Make it purple.',context=context)
  self.assertIn('Build a bird website.',text);self.assertIn('Make it purple.',text)
 def test_explicit_completed_task_origin_wins_over_prefix_mode(self):
  h=[row('one','Already included in model context')];h[0]['result']['unfinished_request']=False
  self.assertEqual(self.compose(h),'Make it purple.')


class UnfinishedTaskSessionTests(unittest.TestCase):
 def test_reopen_retains_unfinished_goal_before_short_steering_note(self):
  import tests.test_interactive_session as fixtures
  f=fixtures.InteractiveSessionTests();f.setUp();self.addCleanup(f.doCleanups)
  def driver(*args):
   result=f.driver(*args)
   if len(f.driver.calls)==1:
    result.update(status='interrupted',unfinished_request=True,
      context=dict(branch='prepared-prefix',tip='a'*64,root='a'*64,revision=0,
       model_contract_id='model',execution_profile_id='profile',mode='append_user'))
   else:result['unfinished_request']=False
   return result
  f.service.runner=driver
  f.service.submit('Build a bird website.',mode='work',kind='send');f.finished(1)
  first=f.service.snapshot['history'][0]
  self.assertTrue(first['result']['unfinished_request'])
  f.service.close();f.service=f.open();f.addCleanup(f.service.close);f.service.runner=driver
  f.wait(lambda:f.service.snapshot['status']=='ready')
  f.service.submit('Make it purple.',mode='work',kind='send');f.finished(2)
  task=f.driver.calls[1][1]['config']['bindings']['task']['value']
  self.assertIn('Build a bird website.',task);self.assertIn('Make it purple.',task)
  self.assertEqual(f.service.snapshot['history'][0],first)
  self.assertEqual(f.service.snapshot['history'][1]['input']['message'],'Make it purple.')
