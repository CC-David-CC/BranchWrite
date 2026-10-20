"""Regression for mixed-schema token accounting in the smoke harness."""
from pathlib import Path
import tempfile,unittest
from validation.run_workflow_smoke import prefix_token_count
class PrefixAccountingTests(unittest.TestCase):
 def test_actual_mixed_schema_text_root_counts_tokens_not_spans(self):
  from context_time_travel.store import Store
  with tempfile.TemporaryDirectory() as directory:
   store=Store(directory)
   snapshot=store.create_input_root('model',[dict(kind='text',tokens=[1,2,3,4,5,6,7,8])],{})
   self.assertEqual(prefix_token_count(store,snapshot),8)
 def test_actual_legacy_text_root_uses_same_canonical_input_read(self):
  from context_time_travel.store import Store
  with tempfile.TemporaryDirectory() as directory:
   store=Store(directory);snapshot=store.create_root('model',(1,2,3),{})
   self.assertEqual(prefix_token_count(store,snapshot),3)

class ProgressFinalizationTests(unittest.TestCase):
 def test_actual_tracker_finishes_and_closes_with_terminal_pass(self):
  from validation.run_workflow_smoke import finish_progress
  from run_cow_client_recovery import ProgressTracker
  import os,json
  with tempfile.TemporaryDirectory() as directory:
   tracker=ProgressTracker(Path(directory),'smoke',interval_seconds=0.01).start();fd=tracker.events_fd
   report=finish_progress(tracker,None)
   self.assertEqual(report['status'],'PASS');self.assertFalse(tracker.thread.is_alive())
   with self.assertRaises(OSError):os.fstat(fd)
 def test_actual_tracker_records_failure_and_closes(self):
  from validation.run_workflow_smoke import finish_progress
  from run_cow_client_recovery import ProgressTracker
  with tempfile.TemporaryDirectory() as directory:
   tracker=ProgressTracker(Path(directory),'smoke',interval_seconds=0.01).start()
   report=finish_progress(tracker,RuntimeError('failure retained'))
   self.assertEqual(report['status'],'FAIL');self.assertEqual(report['error'],'failure retained');self.assertFalse(tracker.thread.is_alive())
