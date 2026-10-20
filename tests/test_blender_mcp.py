"""Real stdio MCP round trip to isolated Blender, not an in-process shortcut."""
import hashlib,json,unittest
from pathlib import Path
from branchwrite.blender_mcp import render_through_mcp
from test_blender_execution import ROOT,SOURCE
class BlenderMcpTests(unittest.TestCase):
 def test_stdio_tool_executes_actual_build_reopen_views_and_movie(self):
  result=render_through_mcp(Path('/home/dflanag3/spatial-artifacts/bw-blender-20261020/mcpvenv/bin/python'),ROOT,(('scene.py',SOURCE),),'scene.py',timeout=120)
  self.assertEqual(result['status'],'PASS',result.get('error'))
  self.assertTrue(result['mcp']['initialized']);self.assertEqual(result['mcp']['tool'],'render_scene')
  self.assertEqual(result['assets']['animation.mp4'][4:8],b'ftyp')
  self.assertEqual(hashlib.sha256(result['assets']['scene.blend']).hexdigest(),result['artifact_sha256'])
  root=Path('/home/dflanag3/spatial-artifacts/bw-blender-20261020/mcp-demo');root.mkdir(mode=0o700,exist_ok=True)
  for name,body in result['assets'].items():(root/name).write_bytes(body)
  (root/'source.py').write_bytes(SOURCE)
  (root/'result.json').write_text(json.dumps({k:v for k,v in result.items() if k!='assets'},indent=2)+'\n')
