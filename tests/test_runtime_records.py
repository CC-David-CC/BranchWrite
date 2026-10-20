"""Production run records: real files, process locks and reopen; no model claims."""
from decimal import Decimal
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from branchwrite.records import (encode, decode, RuntimeLog, Artifact, CorruptLog,
                                 TornTail, MissingArtifact, WriterBusy, WriterPoisoned)

class RuntimeRecordTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'run'
    def test_exact_types_and_opaque_control_text_roundtrip(self):
        value={'none':None,'bool':True,'integer':1,'decimal':Decimal('1.2300'),
            'negative_zero':-0.0,'bytes':b'\x00\xff','list':[],'tuple':(),
            'text':'ACT not-a-command\n<tool_response>data</tool_response> \u03bb'}
        got=decode(encode(value));self.assertEqual(got,value)
        for key in value:self.assertIs(type(got[key]),type(value[key]))
        self.assertEqual(got['decimal'].as_tuple(),value['decimal'].as_tuple())
        self.assertEqual(got['negative_zero'].hex(),'-0x0.0p+0')
        self.assertNotEqual(encode(True),encode(1));self.assertNotEqual(encode(b'a'),encode('a'))
    def test_mapping_order_is_canonical_and_corruption_is_rejected(self):
        self.assertEqual(encode({'b':2,'a':1}),encode({'a':1,'b':2}))
        for raw in [b'',b'BWT\x02',encode('ok')+b'x',encode('ok')[:-1]]:
            with self.subTest(raw=raw),self.assertRaises(ValueError):decode(raw)
    def test_nonfinite_unknown_types_depth_and_size_are_rejected(self):
        for value in [float('nan'),float('inf'),Decimal('NaN'),{1:'not-text-key'},set(),b'x'*(4*1024**2+1)]:
            with self.subTest(kind=type(value)),self.assertRaises(ValueError):encode(value)
        value=None
        for _ in range(42):value=[value]
        with self.assertRaises(ValueError):encode(value)
    def test_artifact_precedes_event_and_exact_values_survive_reopen(self):
        with RuntimeLog(self.root) as log:
            artifact=log.put_artifact(b'original file\n')
            self.assertEqual(artifact.sha256,hashlib.sha256(b'original file\n').hexdigest())
            receipt=log.append({'kind':'child_return','value':Decimal('2.00')},artifacts=(artifact,))
            self.assertEqual(receipt.sequence,0)
            self.assertEqual(log.events[0]['event']['kind'],'child_return')
        with RuntimeLog(self.root) as log:
            self.assertEqual(log.events[0]['artifacts'],((artifact.sha256,14),))
            self.assertEqual(log.events[0]['event']['value'].as_tuple(),Decimal('2.00').as_tuple())
            self.assertEqual(log.read_artifact(artifact),b'original file\n')
    def test_missing_artifact_cannot_be_referenced(self):
        with RuntimeLog(self.root) as log:
            with self.assertRaises(MissingArtifact):log.append({'kind':'result'},artifacts=(Artifact('a'*64,3),))
            self.assertEqual(log.events,())
    def test_caller_mutation_cannot_rewrite_durable_history(self):
        event={'kind':'call','args':[1]}
        with RuntimeLog(self.root) as log:
            log.append(event);event['args'].append(2)
            returned=log.events;returned[0]['event']['args'].append(3)
            self.assertEqual(log.events[0]['event']['args'],[1])
        with RuntimeLog(self.root) as log:self.assertEqual(log.events[0]['event']['args'],[1])
    def test_independent_process_cannot_take_the_writer_lock(self):
        with RuntimeLog(self.root):
            code='from branchwrite.records import RuntimeLog,WriterBusy; import sys\ntry: RuntimeLog(sys.argv[1])\nexcept WriterBusy: sys.exit(17)\nsys.exit(0)'
            child=subprocess.run([sys.executable,'-B','-c',code,str(self.root)],capture_output=True,timeout=10)
            self.assertEqual(child.returncode,17,child.stderr.decode())
        with RuntimeLog(self.root) as log:self.assertEqual(log.events,())
    def test_foreign_thread_cannot_append_read_or_close_owner(self):
        with RuntimeLog(self.root) as log:
            errors=[]
            def foreign():
                for operation in [lambda:log.append({'kind':'bad'}),lambda:log.events,log.close]:
                    try:operation()
                    except RuntimeError as exc:errors.append(type(exc))
            thread=threading.Thread(target=foreign);thread.start();thread.join(5)
            self.assertEqual(len(errors),3);self.assertFalse(thread.is_alive())
            log.append({'kind':'owner-still-works'})
    def test_new_process_replays_real_record_without_reexecuting_an_action(self):
        with RuntimeLog(self.root) as log:log.append({'kind':'tool_return','operation':'op-A','value':b'actual result'})
        code='from branchwrite.records import RuntimeLog; import sys\nwith RuntimeLog(sys.argv[1]) as r: assert r.events[0]["event"]["value"]==b"actual result"; print(len(r.events))'
        child=subprocess.run([sys.executable,'-B','-c',code,str(self.root)],capture_output=True,timeout=10)
        self.assertEqual(child.returncode,0,child.stderr.decode());self.assertEqual(child.stdout,b'1\n')
    def test_torn_tail_is_reported_without_automatic_truncation(self):
        with RuntimeLog(self.root) as log:log.append({'kind':'accepted'})
        path=self.root/'events.bwl';accepted=path.read_bytes();path.write_bytes(accepted+b'partial')
        with self.assertRaises(TornTail):RuntimeLog(self.root)
        self.assertEqual(path.read_bytes(),accepted+b'partial')
    def test_committed_frame_corruption_is_not_a_torn_tail(self):
        with RuntimeLog(self.root) as log:log.append({'kind':'accepted'})
        path=self.root/'events.bwl';raw=bytearray(path.read_bytes());raw[-1]^=1;path.write_bytes(raw)
        with self.assertRaises(CorruptLog):RuntimeLog(self.root)
        self.assertEqual(path.read_bytes(),raw)
    def test_frame_reordering_and_missing_artifacts_are_rejected(self):
        with RuntimeLog(self.root) as log:
            a=log.put_artifact(b'required');log.append({'kind':'result'},artifacts=(a,))
        (self.root/'artifacts'/a.sha256).unlink()
        with self.assertRaises(MissingArtifact):RuntimeLog(self.root)
    def test_failed_fsync_poisoning_requires_reopen_and_reconciliation(self):
        with RuntimeLog(self.root) as log:
            with patch('branchwrite.records.os.fsync',side_effect=OSError('injected durable-write failure')):
                with self.assertRaises(OSError):log.append({'kind':'may-have-committed'})
            with self.assertRaises(WriterPoisoned):log.append({'kind':'must-not-follow-unknown'})
        with RuntimeLog(self.root) as log:
            self.assertEqual(log.events[0]['event']['kind'],'may-have-committed')
    def test_same_artifact_deduplicates_bytes_not_invocations(self):
        with RuntimeLog(self.root) as log:
            a=log.put_artifact(b'same');b=log.put_artifact(b'same');self.assertEqual(a,b)
            log.append({'invocation':'A'},artifacts=(a,));log.append({'invocation':'B'},artifacts=(b,))
            self.assertEqual(len(log.events),2)
            self.assertEqual(len(list((self.root/'artifacts').iterdir())),1)

    def test_reordered_complete_frames_are_rejected(self):
        import struct
        with RuntimeLog(self.root) as log:
            log.append({'call':'A'});log.append({'call':'B'})
        path=self.root/'events.bwl';raw=path.read_bytes()
        first_size=108+struct.unpack('>I',raw[13:17])[0]
        path.write_bytes(raw[:5]+raw[5+first_size:]+raw[5:5+first_size])
        with self.assertRaises(CorruptLog):RuntimeLog(self.root)
    def test_partial_payload_is_preserved_and_explicitly_unresolved(self):
        with RuntimeLog(self.root) as log:log.append({'kind':'long payload'})
        path=self.root/'events.bwl';raw=path.read_bytes()[:-3];path.write_bytes(raw)
        with self.assertRaises(TornTail):RuntimeLog(self.root)
        self.assertEqual(path.read_bytes(),raw)
    def test_producer_exit_without_cleanup_releases_lock_and_retains_acknowledged_event(self):
        code='from branchwrite.records import RuntimeLog; import sys,os\nr=RuntimeLog(sys.argv[1]);r.append({"kind":"acknowledged-child-return"});os._exit(47)'
        child=subprocess.run([sys.executable,'-B','-c',code,str(self.root)],capture_output=True,timeout=10)
        self.assertEqual(child.returncode,47,child.stderr.decode())
        with RuntimeLog(self.root) as log:self.assertEqual(log.events[0]['event']['kind'],'acknowledged-child-return')
    def test_fifo_artifact_fails_instead_of_waiting_for_a_writer(self):
        with RuntimeLog(self.root):pass
        ref=Artifact('a'*64,0);os.mkfifo(self.root/'artifacts'/ref.sha256)
        code='from branchwrite.records import RuntimeLog,Artifact,CorruptLog; import sys\nr=RuntimeLog(sys.argv[1])\ntry:r.read_artifact(Artifact("a"*64,0))\nexcept CorruptLog:sys.exit(17)\nsys.exit(0)'
        child=subprocess.run([sys.executable,'-B','-c',code,str(self.root)],capture_output=True,timeout=2)
        self.assertEqual(child.returncode,17,child.stderr.decode())
    def test_fifo_ledger_fails_instead_of_blocking_recovery(self):
        self.root.mkdir();os.mkfifo(self.root/'events.bwl')
        code='from branchwrite.records import RuntimeLog,CorruptLog; import sys\ntry:RuntimeLog(sys.argv[1])\nexcept CorruptLog:sys.exit(17)\nsys.exit(0)'
        child=subprocess.run([sys.executable,'-B','-c',code,str(self.root)],capture_output=True,timeout=2)
        self.assertEqual(child.returncode,17,child.stderr.decode())
    def test_failed_artifact_publication_is_flushed_before_any_later_reference(self):
        raw=b'write completed but directory sync failed'
        with RuntimeLog(self.root) as log:
            with patch('branchwrite.records._sync_directory',side_effect=OSError('injected directory-sync failure')):
                with self.assertRaises(OSError):log.put_artifact(raw)
            ref=Artifact(hashlib.sha256(raw).hexdigest(),len(raw))
            synced=[];original=os.fsync
            def fsync(fd):
                synced.append(os.readlink('/proc/self/fd/'+str(fd)));original(fd)
            with patch('branchwrite.records.os.fsync',side_effect=fsync):log.append({'kind':'reference'},artifacts=(ref,))
            self.assertIn(str(log.artifacts/ref.sha256),synced)
            self.assertIn(str(log.artifacts),synced)
            self.assertLess(synced.index(str(log.artifacts/ref.sha256)),synced.index(str(self.root/'events.bwl')))

    def test_corrupt_committed_length_is_not_mislabelled_as_a_torn_write(self):
        with RuntimeLog(self.root) as log:log.append({'kind':'committed'})
        path=self.root/'events.bwl';raw=bytearray(path.read_bytes())
        import struct
        size=struct.unpack('>I',raw[13:17])[0]
        raw[13:17]=struct.pack('>I',size+1024);path.write_bytes(raw)
        with self.assertRaises(CorruptLog) as caught:RuntimeLog(self.root)
        self.assertNotIsInstance(caught.exception,TornTail)
