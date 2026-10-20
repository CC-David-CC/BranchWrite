"""Do not advance a workload from unverified or changed predecessor bytes."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from validation.run_basic_loop_edit import verified_predecessor

class WorkloadLineageTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.source=self.root/'source';self.source.mkdir()
        (self.source/'index.html').write_bytes(b'actual verified page')
        self.record=self.root/'result.json'
        self.value=dict(target='H05',status='H05_EDIT_RENDER_OBSERVE_PASS',observer_quality='PASS',
            source_unchanged_after_observation=True,after=dict(cli_exit=0,cli_absent=True,capture=dict(
                inspection_status='PASS',source_sha256=hashlib.sha256(b'actual verified page').hexdigest())))
        self.save()
    def save(self):self.record.write_text(json.dumps(self.value))
    def test_advance_binds_exact_verified_source(self):
        receipt=verified_predecessor(self.source,self.record,'H06')
        self.assertEqual(receipt['target'],'H05')
        self.assertEqual(receipt['source_sha256'],self.value['after']['capture']['source_sha256'])
        self.assertEqual(receipt['result_sha256'],hashlib.sha256(self.record.read_bytes()).hexdigest())
    def test_changed_source_does_not_inherit_previous_pass(self):
        (self.source/'index.html').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'predecessor'):verified_predecessor(self.source,self.record,'H06')
    def test_failed_or_unsettled_observation_does_not_advance(self):
        for field,value in [('observer_quality','FAIL'),('status','RUNNING'),('target','H04')]:
            original=self.value[field];self.value[field]=value;self.save()
            with self.subTest(field=field),self.assertRaises(ValueError):verified_predecessor(self.source,self.record,'H06')
            self.value[field]=original
        self.value['after']['cli_absent']=False;self.save()
        with self.assertRaises(ValueError):verified_predecessor(self.source,self.record,'H06')
