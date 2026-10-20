"""Read-only planning is enforced by grants and current inventory, not prompting."""
import json,tempfile,unittest
from pathlib import Path
from branchwrite.coding_cli import build_launch
from branchwrite.execution import Executor,Grant
from branchwrite.tool_registry import ToolRegistry
from branchwrite.records import RuntimeLog
from branchwrite.kernel import FrameKernel
from branchwrite.interpreter import Interpreter,Value

class PlanModeTests(unittest.TestCase):
    def test_plan_launcher_has_no_file_write_or_execution_grants(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);(p/'page.html').write_text('hello')
            connection=dict(endpoint_url='http://127.0.0.1:1',endpoint_pin='cpu',model_contract_id='m',execution_profile_id='p',eos_tokens=[1])
            launch=build_launch(p,'Plan a change',connection,branch='plan',mode='plan')
            grant=launch['config']['grant']
            self.assertEqual(grant['read_paths'],['page.html'])
            self.assertEqual(grant['edit_paths'],[]);self.assertEqual(grant['create_paths'],[])
            self.assertFalse(grant.get('allow_shell',False));self.assertFalse(grant.get('project_files',False))
    def test_finish_in_read_only_mode_requires_unchanged_inventory(self):
        from branchwrite.verification import ReadOnlyPolicy
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);source=p/'source';source.mkdir();(source/'page').write_text('original')
            executor=Executor.create(source,p/'world')
            registry=ToolRegistry(executor,Grant((),False,read_paths=('page',)))
            policy=ReadOnlyPolicy.admit({'schema':1,'read_only':True},registry)
            with RuntimeLog(p/'ledger') as log:
                self.assertEqual(policy.verify(registry,log,())['status'],'pass')
                (executor.workspace/'page').write_text('changed')
                self.assertEqual(policy.verify(registry,log,())['status'],'fail')
    def test_read_only_policy_rejects_a_writable_host_grant(self):
        from branchwrite.verification import ReadOnlyPolicy
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);source=p/'source';source.mkdir()
            registry=ToolRegistry(Executor.create(source,p/'world'),Grant((),False,project_files=True))
            with self.assertRaises(ValueError):ReadOnlyPolicy.admit({'schema':1,'read_only':True},registry)
