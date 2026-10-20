"""Real OpenCascade fixtures, round-trip exports and adversarial CAD shapes."""
import dataclasses,json,math,tempfile,unittest
from pathlib import Path
import build123d as b
from branchwrite.cad_requirements import PlateSpec
from branchwrite.cad_inspect import inspect_step

def spec(width=100):return PlateSpec(width,60,4,5,76,36,8,6,10)
def fixture(width=100,diameter=5,spacing=76,notch_x=None,depth=4,missing=False,extra=False):
 s=b.Box(width,60,4,align=(b.Align.CENTER,b.Align.CENTER,b.Align.MIN))
 for i,(x,y) in enumerate(((-spacing/2,-18),(-spacing/2,18),(spacing/2,-18),(spacing/2,18))):
  if missing and i==3:continue
  s-=b.Pos(x,y,4-depth)*b.Cylinder(diameter/2,depth,align=(b.Align.CENTER,b.Align.CENTER,b.Align.MIN))
 s-=b.Pos(width/2-3 if notch_x is None else notch_x,0)*b.Box(6,10,4,align=(b.Align.CENTER,b.Align.CENTER,b.Align.MIN))
 if extra:s+=b.Pos(0,0,8)*b.Box(1,1,1)
 return s
class CadGeometryTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
 def inspect(self,shape,requirements=None):
  p=self.root/'part.step';b.export_step(shape,p);return inspect_step(p,requirements or spec())
 def assert_failure(self,report,check):
  self.assertEqual(report['status'],'FAIL');self.assertFalse(report['checks'][check]['pass'])
 def test_roundtrip_valid_plate(self):
  r=self.inspect(fixture());self.assertEqual(r['status'],'PASS');self.assertEqual(len(r['measurements']['holes']),4)
 def test_width_revision_moves_notch_preserves_pattern(self):
  r=self.inspect(fixture(110),spec(110));self.assertEqual(r['status'],'PASS')
 def test_exact_minimum_width_passes(self):self.assertEqual(self.inspect(fixture(97),spec(97))['status'],'PASS')
 def test_mirrored_notch_same_bbox_and_volume_is_rejected(self):self.assert_failure(self.inspect(fixture(notch_x=-47)),'locating_notch')
 def test_widened_plate_with_floating_old_notch_rejected(self):self.assert_failure(self.inspect(fixture(110,notch_x=47),spec(110)),'locating_notch')
 def test_hole_spacing_changed_rejected(self):self.assert_failure(self.inspect(fixture(110,spacing=83.6),spec(110)),'hole_pattern')
 def test_claimed_diameter_cannot_replace_measured_geometry(self):self.assert_failure(self.inspect(fixture(diameter=6)),'hole_diameter')
 def test_blind_holes_rejected(self):self.assert_failure(self.inspect(fixture(depth=2)),'through_holes')
 def test_missing_hole_rejected(self):self.assert_failure(self.inspect(fixture(missing=True)),'hole_pattern')
 def test_extra_body_rejected(self):self.assert_failure(self.inspect(fixture(extra=True)),'single_solid')
 def test_width90_has_explicit_contradiction(self):
  f=spec(90).feasibility();self.assertFalse(f['feasible']);self.assertEqual(f['minimum_width_mm'],97)
  self.assertTrue(any(x['requirement']=='edge_material_x' for x in f['conflicts']))
 def test_symlink_input_rejected(self):
  target=self.root/'real.step';b.export_step(fixture(),target);link=self.root/'link.step';link.symlink_to(target)
  with self.assertRaises(ValueError):inspect_step(link,spec())
 def test_bad_parameters_rejected(self):
  for value in [True,float('nan'),float('inf'),0,-1]:
   with self.assertRaises(ValueError):dataclasses.replace(spec(),width_x=value)
 def test_equal_volume_unrequested_features_rejected(self):
  s=fixture();s-=b.Pos(0,15,0)*b.Box(2,2,4,align=(b.Align.CENTER,b.Align.CENTER,b.Align.MIN))
  s+=b.Pos(45,0,0)*b.Box(2,2,4,align=(b.Align.CENTER,b.Align.CENTER,b.Align.MIN))
  report=self.inspect(s);self.assertTrue(report['checks']['bounds']['pass']);self.assertTrue(report['checks']['volume']['pass'])
  self.assert_failure(report,'material_geometry')

 def test_linked_parent_input_rejected(self):
  folder=self.root/'actual';folder.mkdir();b.export_step(fixture(),folder/'part.step');link=self.root/'alias';link.symlink_to(folder,target_is_directory=True)
  with self.assertRaises(ValueError):inspect_step(link/'part.step',spec())

 def test_extra_non_solid_geometry_is_rejected(self):
  for extra in [b.Face.make_rect(2,2,b.Plane.XY.offset(2)),b.Edge.make_line((0,0,1),(1,1,2))]:
   with self.subTest(kind=type(extra).__name__):self.assert_failure(self.inspect(b.Compound([fixture(),extra])),'single_solid')
