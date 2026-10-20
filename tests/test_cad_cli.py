import json,tempfile,unittest
from pathlib import Path
from branchwrite.coding_cli import build_launch,_validate,CAD_PROGRAM
from branchwrite.cad_config import validate_cad_config
from test_cad_execution import RUNTIME
from test_cad_evaluation import LIBS
from test_cad_geometry import spec
class CadCliTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.config=dict(python=str(RUNTIME),osmesa=str(LIBS),timeout=30,requirements=spec().document())
  self.connection=dict(endpoint_url='http://127.0.0.1:8099',endpoint_pin='a'*64,model_contract_id='b'*64,execution_profile_id='c'*64,eos_tokens=[1])
 def test_normal_directory_launch_binds_requirements_and_actual_image_feedback(self):
  r=build_launch(Path(self.tmp.name),'Build a plate.',self.connection,branch='cad-cli',project_files=True,cad=self.config)
  _validate(r);self.assertEqual(r['program'],CAD_PROGRAM)
  self.assertEqual(r['config']['verification'],dict(schema=1,cad=True))
  self.assertEqual(r['config']['profiles']['cad-views'],dict(kind='image-feedback',source='current'))
  self.assertIn('inspect_cad',r['config']['bindings']['task']['value'])
 def test_readonly_cannot_gain_cad_execution(self):
  with self.assertRaises(ValueError):build_launch(Path(self.tmp.name),'Build.',self.connection,branch='no',mode='plan',cad=self.config)
 def test_unknown_or_unbounded_configuration_rejected(self):
  for extra in [dict(extra=True),dict(timeout=float('inf')),dict(timeout=True),dict(python='python')]:
   with self.subTest(extra=extra),self.assertRaises(ValueError):validate_cad_config({**self.config,**extra})

 def test_blender_directory_launch_uses_same_interpreter_with_image_feedback(self):
  from branchwrite.coding_cli import BLENDER_PROGRAM
  config=dict(distribution='/pinned/blender',mcp_python='/pinned/venv/bin/python',timeout=120,require_animation=True)
  r=build_launch(Path(self.tmp.name),'Create an animated scene.',self.connection,branch='blender-cli',project_files=True,blender=config)
  _validate(r);self.assertEqual(r['program'],BLENDER_PROGRAM)
  self.assertEqual(r['config']['verification'],dict(schema=1,blender=True))
