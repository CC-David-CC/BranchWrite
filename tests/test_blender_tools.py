"""Registry to real MCP to real isolated Blender; no model claim."""
import json,tempfile,unittest
from pathlib import Path
from branchwrite.execution import Executor,Grant,ToolRejected
from branchwrite.tool_registry import ToolRegistry
from branchwrite.blender_tools import BlenderCapability,BlenderPolicy
from branchwrite.blender_execution import BlenderRuntime
from branchwrite.records import RuntimeLog,encode
from test_blender_execution import ROOT,SOURCE
class BlenderToolTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.cap=BlenderCapability(BlenderRuntime(ROOT),Path('/home/dflanag3/spatial-artifacts/bw-blender-20261020/mcpvenv/bin/python'))
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);root=Path(self.tmp.name);source=root/'source';source.mkdir();(source/'scene.py').write_bytes(SOURCE)
  self.ex=Executor.create(source,root/'world');self.grant=Grant((),False,project_files=True)
  self.registry=ToolRegistry(self.ex,self.grant,blender=self.cap);self.log=RuntimeLog(root/'ledger');self.addCleanup(self.log.close)
 def test_complete_mcp_artifact_chain_current_acceptance_and_stale_rejection(self):
  plan=self.registry.freeze(json.dumps(dict(tool='inspect_scene',arguments=dict(path='scene.py'))))
  out=self.registry.execute(plan,'blender-op');value,_=out.publish(self.log)
  self.assertEqual(out.disposition,'scene_checked',out.stderr);self.assertEqual(len(value['details']['asset_manifest']),6)
  ref=self.log.put_artifact(plan.data);res=self.log.put_artifact(encode(('ToolOutcome',None,value)))
  frame=dict(id='scene-check',state='Closed',inputs=(ref.sha256,ref.size_bytes),result=(res.sha256,res.size_bytes),dispatch=('blender-op',None))
  policy=BlenderPolicy.admit(dict(schema=1,blender=True),self.registry)
  self.assertEqual(policy.verify(self.registry,self.log,[(frame,value)])['status'],'pass')
  (self.ex.workspace/'scene.py').write_bytes(SOURCE+b'\n# source revision\n')
  self.assertEqual(policy.verify(self.registry,self.log,[(frame,value)])['status'],'fail')
 def test_no_host_capability_no_blender_tool(self):
  with self.assertRaises(ToolRejected):ToolRegistry(self.ex,self.grant).freeze(json.dumps(dict(tool='inspect_scene',arguments=dict(path='scene.py'))))
