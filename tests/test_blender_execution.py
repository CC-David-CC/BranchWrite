"""Real Blender processes and renders, no model or GPU correctness claim."""
from pathlib import Path
import unittest
from branchwrite.blender_execution import BlenderRuntime,build_scene
ROOT=Path('/home/dflanag3/spatial-artifacts/bw-blender-20261020/blender-4.5.3-linux-x64')
SOURCE=b"""import bpy,math
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.mesh.primitive_cube_add(size=2,location=(0,0,1))
cube=bpy.context.object;cube.name='DemoModule'
cube.rotation_euler.z=0;cube.keyframe_insert(data_path='rotation_euler',frame=1)
cube.rotation_euler.z=math.pi/2;cube.keyframe_insert(data_path='rotation_euler',frame=24)
bpy.ops.wm.save_as_mainfile(filepath='/work/scene.blend')
"""
class BlenderExecutionTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.runtime=BlenderRuntime(ROOT,timeout=120)
 def test_actual_scene_reopen_controlled_views_and_animation(self):
  result=build_scene((('scene.py',SOURCE),),'scene.py',self.runtime)
  self.assertEqual(result['status'],'PASS',result.get('error'))
  self.assertIn('scene.blend',result['assets']);self.assertIn('isometric.png',result['assets'])
  self.assertEqual(result['assets']['top.png'][:8],b'\x89PNG\r\n\x1a\n')
  self.assertEqual(result['scene']['frames'],[1,12,24])
  self.assertTrue(result['scene']['transform_animation_observed'])
  self.assertEqual(result['scene']['objects'][0]['name'],'DemoModule')
  self.assertEqual(result['isolation']['namespace_members_after'],[])
  self.assertEqual(result['build_isolation']['namespace_members_after'],[])
 def test_missing_fresh_scene_export_fails(self):
  result=build_scene((('scene.py',b'pass'),('scene.blend',b'old')),'scene.py',self.runtime)
  self.assertEqual(result['status'],'FAIL');self.assertNotIn('scene.blend',result['assets'])
