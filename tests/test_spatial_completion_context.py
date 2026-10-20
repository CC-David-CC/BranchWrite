"""Tell the model the actual admitted completion contract, not a stale shell policy."""
import unittest
from branchwrite.coding_defaults import continuation_input
class SpatialContextTests(unittest.TestCase):
 def schema(self):return dict(oneOf=[dict(properties=dict(tool=dict(enum=['run_check'])))])
 def test_cad_context_does_not_require_irrelevant_shell_checks(self):
  t=continuation_input('Make the plate.',self.schema(),completion_policy='cad-geometry-and-finish')
  self.assertIn('inspect_cad',t);self.assertIn('immutable',t)
  self.assertNotIn('Finish requires at least one check',t)
 def test_blender_context_requires_actual_mcp_render_receipt(self):
  t=continuation_input('Make a scene.',self.schema(),completion_policy='blender-scene-and-finish')
  self.assertIn('inspect_scene',t);self.assertNotIn('Finish requires at least one check',t)
 def test_normal_coding_retains_named_check_contract(self):
  self.assertIn('Finish requires at least one check',continuation_input('Fix it.',self.schema()))
