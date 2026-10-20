"""Real boundary admission before paid/model work; no GPU claim."""
import json, subprocess, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from branchwrite.execution import Executor, Grant, ToolRejected
from branchwrite.run_cli import execute

class TestBoundaryAdmission(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="bw-boundary-admit-")
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.source=self.root/"source"
        (self.source/"tests").mkdir(parents=True)
        (self.source/"tests/__init__.py").write_text("")
        # Admission must not import candidate files or run the project tests.
        (self.source/"tests/test_tripwire.py").write_text("raise RuntimeError('project code ran during admission')\n")
        self.executor=Executor.create(self.source,self.root/"world")

    def test_probe_uses_real_sandbox_without_running_project(self):
        self.executor.check_test_boundary()

    def test_nested_disabled_userns_is_rejected_before_http(self):
        cfg=dict(schema=1,source=str(self.source),run_id="boundary-negative",
            grant=dict(edit_paths=[],create_paths=[],read_paths=[],allow_tests=True),
            bindings={},profiles={},
            cow=dict(endpoint_url="http://127.0.0.1:1",endpoint_pin="not-contacted",
                model_contract_id="unused",execution_profile_id="unused",
                eos_tokens=[1],branch="unused",mode="ask",bootstrap="coding"))
        config=self.root/"host.json";config.write_text(json.dumps(cfg))
        script=self.root/"nested.py"
        script.write_text(
            "import json\nfrom pathlib import Path\nfrom unittest.mock import patch\n"
            "from branchwrite.run_cli import execute\nfrom branchwrite.execution import ToolRejected\n"
            "with patch('branchwrite.run_cli.CowClient.http') as http:\n"
            " try:\n"
            f"  execute('run','FLOW job\\nEND\\n',Path({str(config)!r}).read_text(),Path({str(self.root/'state')!r}),max_steps=10)\n"
            " except ToolRejected as exc:\n"
            "  assert 'test sandbox' in str(exc),str(exc)\n"
            " else: raise AssertionError('unavailable sandbox accepted')\n"
            " http.assert_not_called()\n"
            "print('BOUNDARY_REJECTED_BEFORE_HTTP')\n")
        command=["/usr/bin/bwrap","--unshare-user","--disable-userns",
            "--cap-drop","ALL","--ro-bind","/","/",
            "--bind",str(self.root),str(self.root),"--",
            sys.executable,"-B",str(script)]
        result=subprocess.run(command,capture_output=True,text=True,timeout=15,
            env={**__import__('os').environ,"PYTHONPATH":str(Path(__file__).resolve().parents[1])})
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn("BOUNDARY_REJECTED_BEFORE_HTTP",result.stdout)

    def test_completed_workflow_does_not_probe_or_execute_again(self):
        cfg=dict(schema=1,source=str(self.source),run_id="completed",
            grant=dict(edit_paths=[],create_paths=[],read_paths=[],allow_tests=True),
            bindings={},profiles={})
        # Once complete, local resume has no need for a working process sandbox.
        with patch.object(Executor,"check_test_boundary"):
            first=execute("run","FLOW job\nEND\n",json.dumps(cfg),self.root/"done",max_steps=10)
        before=(self.root/"done/ledger/events.bwl").read_bytes()
        with patch.object(Executor,"check_test_boundary",side_effect=AssertionError("redundant probe")):
            second=execute("run","FLOW job\nEND\n",json.dumps(cfg),self.root/"done",max_steps=10)
        self.assertEqual(first,second)
        self.assertEqual(before,(self.root/"done/ledger/events.bwl").read_bytes())

if __name__=="__main__":unittest.main()
