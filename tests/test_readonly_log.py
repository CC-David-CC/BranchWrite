"""Read existing canonical ledgers without creating or repairing their files."""
import tempfile,unittest,hashlib,os
from pathlib import Path
from branchwrite.records import RuntimeLog,WriterBusy,CorruptLog
class ReadOnlyLogTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)/'ledger'
 def make(self):
  with RuntimeLog(self.root) as log:
   ref=log.put_artifact(b'immutable source')
   log.append({'kind':'sample'},artifacts=(ref,))
   events=log.events
  return ref,events
 def snapshot(self):
  return {str(p.relative_to(self.root)):(hashlib.sha256(p.read_bytes()).hexdigest(),p.stat().st_mode) for p in self.root.rglob('*') if p.is_file()}
 def test_existing_log_and_artifacts_are_read_without_changes(self):
  ref,events=self.make();before=self.snapshot()
  with RuntimeLog(self.root,read_only=True) as log:
   self.assertEqual(log.events,events);self.assertEqual(log.event_count,1)
   self.assertEqual(log.read_artifact(ref),b'immutable source')
  self.assertEqual(self.snapshot(),before)
 def test_missing_log_is_not_created(self):
  with self.assertRaises(FileNotFoundError):RuntimeLog(self.root,read_only=True)
  self.assertFalse(self.root.exists())
 def test_empty_existing_events_are_not_initialized(self):
  self.make();(self.root/'events.bwl').write_bytes(b'')
  before=self.snapshot()
  with self.assertRaises(CorruptLog):RuntimeLog(self.root,read_only=True)
  self.assertEqual(self.snapshot(),before)
 def test_readers_share_lock_and_exclude_writer(self):
  self.make()
  with RuntimeLog(self.root,read_only=True),RuntimeLog(self.root,read_only=True):
   with self.assertRaises(WriterBusy):RuntimeLog(self.root)
  with RuntimeLog(self.root) as log:self.assertEqual(log.event_count,1)
 def test_active_writer_excludes_reader(self):
  self.make()
  with RuntimeLog(self.root):
   with self.assertRaises(WriterBusy):RuntimeLog(self.root,read_only=True)
 def test_reader_cannot_publish_artifact_or_event(self):
  self.make();before=self.snapshot()
  with RuntimeLog(self.root,read_only=True) as log:
   with self.assertRaises(PermissionError):log.put_artifact(b'forbidden')
   with self.assertRaises(PermissionError):log.append({'kind':'forbidden'})
  self.assertEqual(self.snapshot(),before)
