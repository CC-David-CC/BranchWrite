"""Real installed standard hardware, isolated construction and reopened STEP."""
import importlib.metadata,json,tempfile,unittest
from pathlib import Path
from branchwrite.cad_execution import CadRuntime,build_candidate
from test_cad_execution import RUNTIME

class WarehouseEnvironmentTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.runtime=CadRuntime(RUNTIME,timeout=60)
 def build(self,code):
  result=build_candidate((("model.py",code.encode()),),"model.py",self.runtime)
  self.assertEqual(result["disposition"],"built",result["stderr"].decode("utf8","replace"))
  self.assertTrue(result["isolation"]["worker_exited"])
  self.assertEqual(result["isolation"]["namespace_members_after"],[])
  import build123d as b
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/"actual.step";path.write_bytes(result["step"]);shape=b.import_step(path)
  self.assertTrue(shape.is_valid);self.assertGreater(shape.volume,0)
  return result,shape
 def test_initial_environment_has_pinned_companion(self):
  self.assertEqual(importlib.metadata.version("bd-warehouse"),"0.4.0")
  self.assertEqual(importlib.metadata.version("build123d"),"0.13.0")
 def test_user_m4_socket_head_example_exports_reopenable_solid(self):
  _,shape=self.build("""from build123d import export_step
from bd_warehouse.fastener import SocketHeadCapScrew
screw=SocketHeadCapScrew(size="M4-0.7",length=16,fastener_type="iso4762",simple=True)
export_step(screw,"part.step")
""")
  self.assertEqual(len(shape.solids()),1)
  bounds=shape.bounding_box()
  self.assertAlmostEqual(bounds.min.Z,-16,places=6)
  self.assertAlmostEqual(bounds.max.Z,4,places=6)
  self.assertGreater(bounds.size.X,4)
 def test_catalogue_queries_and_positioned_component(self):
  result,shape=self.build("""import json
from build123d import export_step,Pos
from bd_warehouse.fastener import SocketHeadCapScrew
assert "iso4762" in SocketHeadCapScrew.types()
assert "M4-0.7" in SocketHeadCapScrew.sizes("iso4762")
screw=SocketHeadCapScrew("M4-0.7",16,"iso4762",simple=True)
print(json.dumps({"types":sorted(SocketHeadCapScrew.types()),"sizes":SocketHeadCapScrew.sizes("iso4762")}))
export_step(Pos(20,10,16)*screw,"part.step")
""")
  self.assertIn("M4-0.7",json.loads(result["stdout"])["sizes"])
  bounds=shape.bounding_box()
  self.assertAlmostEqual((bounds.min.X+bounds.max.X)/2,20,places=6)
  self.assertAlmostEqual((bounds.min.Y+bounds.max.Y)/2,10,places=6)
  self.assertAlmostEqual(bounds.min.Z,0,places=6)
 def test_matching_clearance_hole_changes_actual_solid(self):
  _,shape=self.build("""from build123d import *
from bd_warehouse.fastener import SocketHeadCapScrew,ClearanceHole
screw=SocketHeadCapScrew("M4-0.7",16,"iso4762",simple=True)
with BuildPart() as plate:
 Box(20,20,4,align=(Align.CENTER,Align.CENTER,Align.MAX))
 ClearanceHole(screw,fit="Normal",depth=4,counter_sunk=False)
export_step(plate.part,"part.step")
""")
  import math
  self.assertEqual(len(shape.solids()),1)
  cylinders=[face for face in shape.faces() if face.geom_type.name=="CYLINDER"]
  self.assertEqual(len(cylinders),1)
  self.assertAlmostEqual(cylinders[0].radius,2.25,places=6)
  self.assertAlmostEqual(shape.volume,20*20*4-math.pi*2.25**2*4,places=5)
