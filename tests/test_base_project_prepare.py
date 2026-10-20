"""Project-backed prepare-base binds durable local and COW inputs before admission."""
import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from branchwrite.__main__ import main

class FakeClient:
    def __init__(self, branch):
        self.branch = branch
        self.calls = []
        self.journal = self
    def head(self, name):
        self.calls.append(("head", name))
        return SimpleNamespace(name=name, revision=self.branch["head"]["revision"],
            root=self.branch["head"]["root"], tip=self.branch["head"]["tip"])
    def history(self, name):
        self.calls.append(("history", name))
        return SimpleNamespace(raw=self.branch["history"])
    def create_namespace(self, name, operation_id):
        self.calls.append(("namespace", operation_id))
        return {"namespace_id":"ns"}
    def read(self, operation_id):
        self.calls.append(("receipt", operation_id))
        return {"receipt":{"model_contract_id":"c"*64}}

class FakeBase:
    def __init__(self, client, namespace, *, eos_tokens):
        self.client=client
        self.namespace=namespace
    def prepare_pack(self, **kwargs):
        self.client.calls.append(("prefill", kwargs["expected_pack_id"]))
        return SimpleNamespace(snapshot="d"*64, operation_id=kwargs["operation_id"])
    def catalog_entry(self, version, **kwargs):
        return {"base_id":"e"*64,"prefix_tokens":23,"snapshot":version.snapshot,
            "reference_pack_id":"f"*64}

class ProjectPrepareTests(unittest.TestCase):
    def test_normal_code_cli_freezes_and_reuses_project_receipt(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);project=root/"project";project.mkdir()
            (project/"README.md").write_text("first source truth\n")
            state=root/"state"
            connection=root/"connection.json"
            connection.write_text(json.dumps({"endpoint_url":"http://127.0.0.1:8123",
                "endpoint_pin":"local-test","model_contract_id":"c"*64,
                "execution_profile_id":"d"*64,"eos_tokens":[256]}))
            branch={"head":{"name":"repair","revision":5,"root":"a"*64,"tip":"b"*64},
                "history":{"id":"repair","revision":5,"root":"a"*64,"tip":"b"*64,
                    "pending_controller":{"active":False},"controller_status":"complete",
                    "messages":[{"role":"user","text":"repair issue"},
                                 {"role":"assistant","text":"fixed it"}]}}
            fake=FakeClient(branch)
            argv=["code",str(project),"--task","review the project","--connection",str(connection),
                "--state",str(state),"--branch","worker","--read","README.md",
                "--context-source-branch","repair","--build-project-context",
                "--test-command","true"]
            with patch.dict(os.environ,{"BW_COW_API_KEY":"test-key"}), \
                 patch("branchwrite.cow_client.CowClient.http",return_value=fake), \
                 patch("branchwrite.coding_cli.run_saved",return_value=(0,{"status":"PREPARED"})):
                self.assertEqual(main(argv),0)
            launch_path=state/"coding-launch.json"
            saved=json.loads(launch_path.read_text())["launch"]
            pack=saved["config"]["context_pack"]
            receipt_hash=saved["config"]["bindings"]["project_context_receipt_sha256"]["value"]
            self.assertEqual(len(receipt_hash),64)
            prefix=(Path(pack["path"])/"prefix.txt").read_text()
            self.assertIn("first source truth",prefix)
            self.assertIn("fixed it",prefix)
            self.assertEqual([call[0] for call in fake.calls].count("history"),1)
            (project/"README.md").write_text("changed while client was stopped\n")
            moved={"head":{"name":"repair","revision":6,"root":"a"*64,"tip":"c"*64},
                "history":{"id":"repair","revision":6,"root":"a"*64,"tip":"c"*64,
                    "pending_controller":{"active":False},"controller_status":"complete",
                    "messages":[{"role":"assistant","text":"new result"}]}}
            fake.branch=moved
            with patch.dict(os.environ,{"BW_COW_API_KEY":"test-key"}), \
                 patch("branchwrite.cow_client.CowClient.http",return_value=fake), \
                 patch("branchwrite.coding_cli.run_saved",return_value=(0,{"status":"PREPARED"})):
                self.assertEqual(main(argv),0)
            recovered=json.loads(launch_path.read_text())["launch"]
            self.assertEqual(recovered["config"]["context_pack"],pack)
            self.assertEqual(recovered["config"]["bindings"]["project_context_receipt_sha256"]["value"],receipt_hash)
            self.assertEqual([call[0] for call in fake.calls].count("history"),1)
            self.assertNotIn("changed while client was stopped",(Path(pack["path"])/"prefix.txt").read_text())

    def test_invalid_code_request_fails_before_context_capture(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);project=root/"project";project.mkdir()
            (project/"README.md").write_text("source\n")
            state=root/"state";connection=root/"connection.json"
            connection.write_text(json.dumps({"endpoint_url":"http://127.0.0.1:8123",
                "endpoint_pin":"local-test","model_contract_id":"c"*64,
                "execution_profile_id":"d"*64,"eos_tokens":[256]}))
            argv=["code",str(project),"--task","work","--connection",str(connection),
                "--state",str(state),"--branch","worker","--read","README.md",
                "--build-project-context"]
            fake=FakeClient({})
            with patch.dict(os.environ,{"BW_COW_API_KEY":"test-key"}), \
                 patch("branchwrite.cow_client.CowClient.http",return_value=fake), \
                 contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(argv),2)
            self.assertFalse(state.exists())
            self.assertEqual(fake.calls,[])

    def test_cli_builds_pack_from_project_and_stable_cow_tip(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t); project=root/"project"; project.mkdir()
            (project/"README.md").write_text("project truth\n")
            (project/".env").write_text("unselected secret\n")
            state=root/"state"; state.mkdir(mode=0o700)
            conn={"endpoint_url":"http://127.0.0.1:8123","endpoint_pin":"local-test",
                "model_contract_id":"c"*64,"execution_profile_id":"d"*64,"eos_tokens":[256]}
            connection=root/"connection.json";connection.write_text(json.dumps(conn))
            text="saved branch result"
            branch={"head":{"name":"repair","revision":5,"root":"a"*64,"tip":"b"*64},
                "history":{"id":"repair","revision":5,"root":"a"*64,"tip":"b"*64,
                    "pending_controller":{"active":False},"controller_status":"complete",
                    "messages":[{"role":"user","text":"fix it"},{"role":"assistant","text":text}]}}
            fake=FakeClient(branch)
            argv=["prepare-base","--connection",str(connection),"--state",str(state),
                "--branch","base","--purpose","Shared project context","--project",str(project),
                "--read","README.md","--source-branch","repair","--source-revision","a"*40,
                "--capacity","131072","--operation-id","project-base-1"]
            output=io.StringIO()
            with patch.dict(os.environ,{"BW_COW_API_KEY":"test-key"}), \
                 patch("branchwrite.cow_client.CowClient.http",return_value=fake), \
                 patch("branchwrite.base_cli.ProjectBase",FakeBase), \
                 contextlib.redirect_stdout(output):
                self.assertEqual(main(argv),0)
            result=json.loads(output.getvalue())
            self.assertEqual(result["status"],"PREPARED")
            setup=json.loads((state/"base-setup.json").read_text())
            self.assertEqual(setup["schema"],2)
            self.assertEqual(setup["source_receipt_sha256"],result["source_receipt_sha256"])
            source=json.loads((state/"context-source-receipt.json").read_text())
            self.assertEqual(source["branch_sources"][0]["tip"],"b"*64)
            prefix=(Path(setup["reference_pack_path"])/"prefix.txt").read_text()
            self.assertIn("project truth",prefix)
            self.assertIn("saved branch result",prefix)
            self.assertNotIn("unselected secret",prefix)
            self.assertEqual([call[0] for call in fake.calls].count("prefill"),1)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["context-status",str(state),"--json"]),0)

if __name__=="__main__":unittest.main()
