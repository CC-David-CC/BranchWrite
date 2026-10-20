"""Actual two-part removable carrier, fixed interfaces and revision regressions."""
import tempfile,unittest
from pathlib import Path
from dataclasses import replace
import build123d as b
from branchwrite.cad_carrier import CarrierSpec,inspect_carrier

def fixture(s,shift=0,mirror=False):
 base=b.Box(s.base_x,s.base_y,s.base_z,align=(b.Align.CENTER,b.Align.CENTER,b.Align.MIN))
 z=s.base_z-s.seat_depth
 pocket=b.Pos(0,0,z)*b.Box(s.carrier_x+2*s.clearance,s.carrier_y+2*s.clearance,s.seat_depth,align=(b.Align.CENTER,b.Align.CENTER,b.Align.MIN))
 base-=pocket
 inner=s.carrier_x/2-s.key_depth
 key=b.Pos((inner+s.carrier_x/2+s.clearance)/2,0,z)*b.Box(s.key_depth+s.clearance,s.key_width,s.seat_depth,align=(b.Align.CENTER,b.Align.CENTER,b.Align.MIN))
 base+=key
 for x in (-s.base_hole_x/2,s.base_hole_x/2):
  for y in (-s.base_hole_y/2,s.base_hole_y/2):base-=b.Pos(x,y)*b.Cylinder(s.base_hole_d/2,s.base_z,align=(b.Align.CENTER,b.Align.CENTER,b.Align.MIN))
 carrier=b.Pos(0,0,z)*b.Box(s.carrier_x,s.carrier_y,s.carrier_z,align=(b.Align.CENTER,b.Align.CENTER,b.Align.MIN))
 depth=s.key_depth+s.clearance
 notch=b.Pos((s.carrier_x/2-depth/2)*(-1 if mirror else 1),0,z)*b.Box(depth,s.key_width+2*s.clearance,s.carrier_z,align=(b.Align.CENTER,b.Align.CENTER,b.Align.MIN))
 carrier-=notch
 for x in (-s.module_hole_x/2,s.module_hole_x/2):
  for y in (-s.module_hole_y/2,s.module_hole_y/2):carrier-=b.Pos(x,y,z)*b.Cylinder(s.module_hole_d/2,s.carrier_z,align=(b.Align.CENTER,b.Align.CENTER,b.Align.MIN))
 return b.Compound(children=[base,b.Pos(shift,0,0)*carrier])
class CarrierTests(unittest.TestCase):
 def inspect(self,s,**kw):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'part.step';b.export_step(fixture(s,**kw),p);return inspect_carrier(p,s)
 def test_actual_pair_reopened_has_correct_nominal_fit_and_no_interference(self):
  r=self.inspect(CarrierSpec());self.assertEqual(r['status'],'PASS',r)
  self.assertLessEqual(abs(r['measurements']['interference_mm3']),1e-5)
  self.assertAlmostEqual(r['measurements']['pocket_clearance_x_mm'],.3,places=6)
 def test_thicker_carrier_keeps_interface_identity_and_base(self):
  a=CarrierSpec();s=replace(a,carrier_z=5)
  self.assertEqual(a.interface_id,s.interface_id);self.assertNotEqual(a.identity,s.identity)
  self.assertEqual(self.inspect(s)['status'],'PASS')
 def test_mirrored_key_notch_rejected(self):self.assertEqual(self.inspect(CarrierSpec(),mirror=True)['status'],'FAIL')
 def test_shifted_carrier_rejected_even_if_it_still_fits(self):self.assertEqual(self.inspect(CarrierSpec(),shift=.1)['status'],'FAIL')
 def test_unknown_requirements_cannot_change_contract(self):
  d=CarrierSpec().document();d['dimensions']['allow_interference']=True
  with self.assertRaises(ValueError):CarrierSpec.from_document(d)
