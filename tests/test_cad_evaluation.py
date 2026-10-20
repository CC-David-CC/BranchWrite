"""Actual separate check/render process consuming captured STEP only."""
import hashlib,tempfile,unittest
from pathlib import Path
from branchwrite.cad_execution import CadRuntime,build_candidate,evaluate_candidate
from test_cad_execution import RUNTIME,SOURCE
from test_cad_geometry import spec
LIBS=Path('/home/dflanag3/spatial-artifacts/bw-build123d-20261020/osmesa-runtime/root/usr/lib/x86_64-linux-gnu')
class CadEvaluationTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.runtime=CadRuntime(RUNTIME,timeout=30,osmesa=LIBS)
  cls.step=build_candidate((('model.py',SOURCE),),'model.py',cls.runtime)['step']
 def test_checked_and_rendered_same_export_in_retired_independent_worker(self):
  r=evaluate_candidate(self.step,spec(),self.runtime)
  self.assertEqual(r['status'],'PASS',r)
  self.assertEqual(r['geometry']['status'],'PASS')
  self.assertEqual(r['artifact_sha256'],hashlib.sha256(self.step).hexdigest())
  self.assertEqual(r['render']['artifact_sha256'],r['artifact_sha256'])
  self.assertEqual(r['isolation']['namespace_members_after'],[])
  self.assertTrue(r['isolation']['worker_exited'])
  self.assertIn('views.png',r['assets']);self.assertEqual(r['assets']['views.png'][:8],b'\x89PNG\r\n\x1a\n')
 def test_bad_geometry_is_failure_not_execution_success(self):
  r=evaluate_candidate(b'not a STEP',spec(),self.runtime)
  self.assertEqual(r['status'],'FAIL');self.assertIsNone(r['render'])
  self.assertIn('error',r)
 def test_render_library_configuration_required_before_execution(self):
  with self.assertRaises(ValueError):evaluate_candidate(self.step,spec(),CadRuntime(RUNTIME))
 def test_spec_cannot_include_unrecognized_fields_or_loosen_contract(self):
  from branchwrite.cad_requirements import PlateSpec
  d=spec().document();d['additional_features']=True
  with self.assertRaises(ValueError):PlateSpec.from_document(d)
  d=spec().document();d['dimensions']['tolerance']=2
  with self.assertRaises(ValueError):PlateSpec.from_document(d)

 def test_infeasible_requirement_is_reported_without_tolerance_changes(self):
  from dataclasses import replace
  r=evaluate_candidate(self.step,replace(spec(),width_x=90),self.runtime)
  self.assertEqual(r['status'],'FAIL');self.assertEqual(r['geometry']['status'],'INFEASIBLE')
  self.assertEqual(r['geometry']['feasibility']['minimum_width_mm'],97)
