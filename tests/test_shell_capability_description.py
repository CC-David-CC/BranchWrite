"""Model-visible tool facts are derived from the actual host configuration."""
from pathlib import Path
import tempfile,unittest
from branchwrite.execution import Executor,Grant
from branchwrite.terminal import ShellConfig
from branchwrite.tool_registry import ToolRegistry
class ShellCapabilityDescriptionTests(unittest.TestCase):
 def test_actual_deadline_and_namespace_boundaries_are_explicit(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);source=root/'source';source.mkdir()
   executor=Executor.create(source,root/'world',shell=ShellConfig(timeout=2.5))
   schema=ToolRegistry(executor,Grant((),False,allow_shell=True)).model_schema()
   shell=next(v for v in schema['oneOf'] if v['properties']['tool']['enum']==['run_shell'])
   description=shell['properties']['arguments']['properties']['command']['description']
   self.assertIn('2.5 seconds',description)
   self.assertIn('new PID namespace',description)
   self.assertIn('namespace_members_after',description)
   self.assertIn('not success',description)
