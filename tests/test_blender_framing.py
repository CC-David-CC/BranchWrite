"""Actual moving meshes and independent camera-space containment checks."""
import math,unittest
from test_blender_execution import ROOT,SOURCE
from branchwrite.blender_execution import BlenderRuntime,build_scene

class BlenderFramingTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.runtime=BlenderRuntime(ROOT,timeout=120)
 def test_fast_moving_mesh_stays_in_all_controlled_views(self):
  source=SOURCE.replace(b"cube.rotation_euler.z=0;",b"cube.location.x=-8;cube.keyframe_insert(data_path='location',frame=1);cube.location.x=8;cube.keyframe_insert(data_path='location',frame=24);cube.rotation_euler.z=0;")
  result=build_scene((("scene.py",source),),"scene.py",self.runtime)
  self.assertEqual(result['status'],'PASS',result.get('error'))
  scene=result['scene']
  for name,view in scene['cameras'].items():
   x,y,z=view['rotation'];cx,sx=math.cos(x),math.sin(x);cy,sy=math.cos(y),math.sin(y);cz,sz=math.cos(z),math.sin(z)
   right=(cz*cy,sz*cy,-sy);up=(cz*sy*sx-sz*cx,sz*sy*sx+cz*cx,cy*sx)
   for frame,items in scene['sampled_transforms'].items():
    matrix=items[0]['matrix']
    for px in (-1,1):
     for py in (-1,1):
      for pz in (-1,1):
       point=[sum(matrix[i][j]*v for j,v in enumerate((px,py,pz,1))) for i in range(3)]
       delta=[point[i]-view['position'][i] for i in range(3)]
       horizontal=sum(v*right[i] for i,v in enumerate(delta));vertical=sum(v*up[i] for i,v in enumerate(delta))
       with self.subTest(view=name,frame=frame):
        self.assertLessEqual(abs(horizontal),view['scale']/2+1e-5)
        self.assertLessEqual(abs(vertical),view['scale']*(240/320)/2+1e-5)
  self.assertEqual(scene['framing_frames'],list(range(1,25)))
 def test_valid_scene_without_world_gets_derived_studio_world(self):
  source=SOURCE.replace(b"bpy.ops.wm.save_as_mainfile",b"bpy.context.scene.world=None\nbpy.ops.wm.save_as_mainfile")
  result=build_scene((("scene.py",source),),"scene.py",self.runtime)
  self.assertEqual(result['status'],'PASS',result.get('error'))
  self.assertIn('animation.mp4',result['assets'])
