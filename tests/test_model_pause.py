"""Host request control is separate from durable model settlement."""
import json,tempfile,threading,unittest
from pathlib import Path
from unittest.mock import patch
from branchwrite.cow_client import CowClient,OperationJournal,HTTPTransport,_Response,CowClientError,RequestRejected,OperationIndeterminate

class PauseClientTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.client=CowClient.http('http://127.0.0.1:1',journal=OperationJournal(self.tmp.name),api_key='private-test-key',endpoint_pin='pin')
 def test_control_uses_original_id_short_separate_transport_and_no_journal_mutation(self):
  calls=[]
  def request(transport,method,path,body,**options):
   calls.append((transport,method,path,json.loads(body)))
   return _Response(json_value=dict(operation_id='original-op',active=True,pause_requested=True))
  with patch.object(HTTPTransport,'request',request):result=self.client.pause_generation('original-op')
  self.assertTrue(result['pause_requested']);transport,method,path,body=calls[0]
  self.assertEqual((method,path,body),('POST','/cow/pause',{'operation_id':'original-op'}))
  self.assertIsNot(transport,self.client.transport);self.assertLessEqual(transport.timeout,2)
  self.assertEqual(self.client.transport.timeout,1800);self.assertEqual(transport.api_key,'private-test-key')
  self.assertIsNone(self.client.journal.read('original-op'))
 def test_mismatched_or_impossible_pause_ack_is_rejected(self):
  for value in (dict(operation_id='wrong',active=True,pause_requested=True),dict(operation_id='original-op',active=False,pause_requested=True),dict(operation_id='original-op',active=1,pause_requested=True)):
   with self.subTest(value=value),patch.object(HTTPTransport,'request',return_value=_Response(json_value=value)):
    with self.assertRaises(CowClientError):self.client.pause_generation('original-op')

class PauseWatcherTests(unittest.TestCase):
 def watcher(self,control,pause,notices):
  from branchwrite.model_pause import PauseWatcher
  return PauseWatcher('original-op',control,pause,notices.append,interval=.01)
 def test_no_control_request_until_host_signal_and_ack_does_not_finish_generation(self):
  signal=threading.Event();called=threading.Event();calls=[];notices=[]
  def pause(op):calls.append(op);called.set();return dict(active=True,pause_requested=True)
  with self.watcher(signal.is_set,pause,notices) as watcher:
   self.assertFalse(called.wait(.03));signal.set();self.assertTrue(called.wait(1))
   watcher.thread.join(1);self.assertFalse(watcher.thread.is_alive())
   self.assertEqual(calls,['original-op'])
   # Still inside the original generation call; pause control returns no answer.
   self.assertTrue(watcher.requested)
  self.assertFalse(watcher.thread.is_alive())
 def test_pending_registration_can_be_polled_without_resubmitting_generation(self):
  calls=[];done=threading.Event()
  def pause(op):
   calls.append(op)
   if len(calls)<3:return dict(active=False,pause_requested=False)
   done.set();return dict(active=True,pause_requested=True)
  with self.watcher(lambda:True,pause,[]) as watcher:self.assertTrue(done.wait(1))
  self.assertEqual(calls,['original-op']*3);self.assertTrue(watcher.requested)
 def test_lost_control_reply_retries_only_same_id(self):
  calls=[];done=threading.Event()
  def pause(op):
   calls.append(op)
   if len(calls)==1:raise OperationIndeterminate('lost pause reply')
   done.set();return dict(active=True,pause_requested=True)
  with self.watcher(lambda:True,pause,[]):self.assertTrue(done.wait(1))
  self.assertEqual(calls,['original-op','original-op'])
 def test_old_server_rejection_falls_back_once_without_aborting_model(self):
  called=threading.Event();notices=[]
  def pause(op):called.set();raise RequestRejected('404 old server')
  with self.watcher(lambda:True,pause,notices) as watcher:self.assertTrue(called.wait(1))
  self.assertFalse(watcher.requested);self.assertEqual(len(notices),1);self.assertIn('waiting',notices[0].lower())
 def test_generation_exception_is_preserved_and_watcher_is_joined(self):
  watcher=self.watcher(lambda:False,lambda _:None,[])
  with self.assertRaisesRegex(RuntimeError,'original generation failed'):
   with watcher:raise RuntimeError('original generation failed')
  self.assertFalse(watcher.thread.is_alive())
 def test_observer_failure_is_visible_without_claiming_pause_or_durability(self):
  notices=[];called=threading.Event()
  def control():called.set();raise ValueError('host observer error')
  with self.watcher(control,lambda _:self.fail('must not send'),notices) as watcher:self.assertTrue(called.wait(1))
  self.assertFalse(watcher.requested);self.assertEqual(len(notices),1)


class PauseAdapterIntegrationTests(unittest.TestCase):
 def test_ack_does_not_close_kernel_slot_and_original_receipt_still_wins(self):
  import test_model_dispatch as fixtures
  from branchwrite.model_dispatch import ModelAdapter,step_model,_flow
  f=fixtures.ModelFlowTests();f.setUp();self.addCleanup(f.doCleanups)
  signal=threading.Event();ack=threading.Event();ids=[]
  f.adapter=ModelAdapter(f.client,run_id='model-flow-run',model_contract_id='flow-model',
    execution_profile_id='flow-profile',eos_tokens=(299,),model_pause=signal.is_set)
  f.model.plans=fixtures.defaultdict(lambda:(257,299));f.admit()
  frame,plan=_flow(f.kernel,f.adapter,'model-flow')
  request=f.adapter.native(frame,plan,0,plan['source'],0)[2]
  expected_body=request['body'];original=f.client.answer
  def pause(op):ids.append(op);ack.set();return dict(operation_id=op,active=True,pause_requested=True)
  def answer(*args,**kwargs):
   signal.set();self.assertTrue(ack.wait(2))
   self.assertEqual(f.kernel.frame('root')['state'],'Waiting')
   with self.assertRaises(KeyError):f.kernel.slot_value('root',1,'proposal')
   return original(*args,**kwargs)
  with patch.object(f.client,'pause_generation',side_effect=pause),patch.object(f.client,'answer',side_effect=answer):
   final=step_model(f.kernel,f.adapter,'model-flow')
  self.assertEqual(final.status,'complete');self.assertEqual(len(f.native_frames()),1)
  self.assertEqual(ids,[request['frame_key']['operation_id']])
  self.assertEqual(request['body'],expected_body)
  self.assertEqual(f.kernel.slot_value('root',1,'proposal'),final.value)
