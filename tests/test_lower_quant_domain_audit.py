
import importlib.util,math,unittest
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'validation/lower-quant-domains-20261021/audit_cli_trial.py'
s=importlib.util.spec_from_file_location('quant_domain_audit',p);a=importlib.util.module_from_spec(s);s.loader.exec_module(a)
def matrix(deg=0,scale=1):
 r=math.radians(deg);c=math.cos(r)*scale;s=math.sin(r)*scale
 return [[c,-s,0,0],[s,c,0,0],[0,0,scale,0],[0,0,0,1]]
def scene(degrees=45,second=False,scale=1):
 first=[{'name':'body','matrix':matrix()},{'name':'arm','matrix':matrix(scale=scale)}]
 last=[{'name':'body','matrix':matrix(20 if second else 0)},{'name':'arm','matrix':matrix(degrees,scale)}]
 return {'sampled_transforms':{'1':first,'24':last}}
class AnimationAcceptanceTests(unittest.TestCase):
 def test_one_arm_45_degrees_accepted(self):self.assertEqual(len(a.scene_motion(scene())),2)
 def test_no_movement_is_rejected(self):
  with self.assertRaises(AssertionError):a.scene_motion(scene(0))
 def test_wrong_rotation_is_rejected(self):
  with self.assertRaises(AssertionError):a.scene_motion(scene(90))
 def test_other_body_motion_is_rejected(self):
  with self.assertRaises(AssertionError):a.scene_motion(scene(second=True))
 def test_object_scale_does_not_change_rotation_measurement(self):self.assertAlmostEqual(a.scene_motion(scene(scale=3))[1]['angle_degrees'],45)
if __name__=='__main__':unittest.main()
