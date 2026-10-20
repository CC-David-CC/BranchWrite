"""A project context is rebuilt from durable files and saved COW branch histories."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from branchwrite.project_context import capture_context_pack, context_status

class ProjectContextReceiptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.project = self.root / "project"
        self.project.mkdir()
        (self.project / "README.md").write_text("Project rules\n", encoding="utf-8")
        (self.project / "src").mkdir()
        (self.project / "src" / "main.py").write_text("def run(): return 1\n", encoding="utf-8")
        (self.project / ".env").write_text("SHOULD_NOT_BE_SELECTED\n", encoding="utf-8")
        self.state = self.root / "base-state"
        self.state.mkdir(mode=0o700)

    def branch(self, name="fix-a", *, revision=3, tip="b" * 64, active=False, text="Fixed edge case"):
        return {
            "head": {"name": name, "revision": revision, "root": "a" * 64, "tip": tip},
            "history": {
                "id": name, "revision": revision, "root": "a" * 64, "tip": tip,
                "controller_status": "active" if active else "complete",
                "pending_controller": {"active": active},
                "messages": [
                    {"role": "user", "text": "Repair the edge case", "content": "Repair the edge case"},
                    {"role": "assistant", "text": text, "content": text},
                ],
            },
        }

    def test_build_binds_project_files_and_saved_branch_tips(self):
        result = capture_context_pack(
            self.project, self.state, read_files=("README.md",), read_dirs=("src",),
            branches=(self.branch(),), as_of="2026-10-20T00:00:00Z")
        prefix = (Path(result["pack_path"]) / "prefix.txt").read_text(encoding="utf-8")
        self.assertIn("Project rules", prefix)
        self.assertIn("def run(): return 1", prefix)
        self.assertIn("Repair the edge case", prefix)
        self.assertNotIn("SHOULD_NOT_BE_SELECTED", prefix)
        self.assertEqual(result["source_receipt"]["branch_sources"][0]["tip"], "b" * 64)
        self.assertEqual(result["source_receipt"]["branch_sources"][0]["revision"], 3)
        status = context_status(self.state)
        self.assertEqual(status["phase"], "PACK_DURABLE")
        self.assertEqual(status["pack_id"], result["pack_id"])

    def test_retry_uses_frozen_files_and_branch_tip_after_crash(self):
        first = capture_context_pack(
            self.project, self.state, read_files=("README.md",), read_dirs=("src",),
            branches=(self.branch(),), as_of="2026-10-20T00:00:00Z")
        (self.project / "README.md").write_text("Changed after crash\n", encoding="utf-8")
        retry = capture_context_pack(
            self.project, self.state, read_files=("README.md",), read_dirs=("src",),
            branches=(self.branch(revision=4, tip="c" * 64, text="Later branch update"),),
            as_of="2026-10-20T01:00:00Z")
        self.assertEqual(retry["pack_id"], first["pack_id"])
        self.assertEqual(retry["source_receipt"], first["source_receipt"])
        prefix = (Path(retry["pack_path"]) / "prefix.txt").read_text(encoding="utf-8")
        self.assertIn("Project rules", prefix)
        self.assertNotIn("Changed after crash", prefix)
        self.assertNotIn("Later branch update", prefix)

    def test_new_state_sees_changed_project_and_branch(self):
        capture_context_pack(
            self.project, self.state, read_files=("README.md",), read_dirs=("src",),
            branches=(self.branch(),), as_of="2026-10-20T00:00:00Z")
        next_state = self.root / "next-state"
        next_state.mkdir(mode=0o700)
        (self.project / "README.md").write_text("New durable rules\n", encoding="utf-8")
        first_id = json.loads((self.state / "context-pack-receipt.json").read_text())["pack_id"]
        second = capture_context_pack(
            self.project, next_state, read_files=("README.md",), read_dirs=("src",),
            branches=(self.branch(revision=4, tip="c" * 64, text="New branch result"),),
            as_of="2026-10-20T01:00:00Z")
        self.assertNotEqual(second["pack_id"], first_id)
        prefix = (Path(second["pack_path"]) / "prefix.txt").read_text(encoding="utf-8")
        self.assertIn("New durable rules", prefix)
        self.assertIn("New branch result", prefix)


    def test_process_death_after_source_snapshot_resumes_frozen_inputs(self):
        branch_path = self.root / "branch.json"
        branch_path.write_text(json.dumps(self.branch()), encoding="utf-8")
        hook = r'''
import json,os,sys
from pathlib import Path
import branchwrite.project_context as pc
branch=json.loads(Path(sys.argv[4]).read_text())
original=pc.append_event
def stop_after_source(state,phase,**details):
    result=original(state,phase,**details)
    if phase=="SOURCE_SNAPSHOT_DURABLE": os._exit(77)
    return result
pc.append_event=stop_after_source
pc.capture_context_pack(Path(sys.argv[1]),Path(sys.argv[2]),read_files=("README.md",),read_dirs=("src",),branches=(branch,),as_of="2026-10-20T00:00:00Z")
'''
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        crashed = subprocess.run([sys.executable, "-B", "-c", hook,
            str(self.project), str(self.state), str(self.root), str(branch_path)],
            capture_output=True, text=True, env=env, timeout=20)
        self.assertEqual(crashed.returncode, 77, crashed.stderr)
        self.assertTrue((self.state / "context-source-receipt.json").exists())
        self.assertFalse((self.state / "context-pack-receipt.json").exists())
        status = context_status(self.state)
        self.assertEqual(status["phase"], "SOURCE_SNAPSHOT_DURABLE")
        (self.project / "README.md").write_text("Changed while offline", encoding="utf-8")
        branch_path.write_text(json.dumps(self.branch(revision=4, tip="c" * 64,
            active=True, text="Moved branch")), encoding="utf-8")
        recovery = r'''
import json,sys
from pathlib import Path
from branchwrite.project_context import capture_context_pack
branch=json.loads(Path(sys.argv[4]).read_text())
result=capture_context_pack(Path(sys.argv[1]),Path(sys.argv[2]),read_files=("README.md",),read_dirs=("src",),branches=(branch,),as_of="2026-10-20T01:00:00Z")
print(json.dumps(result))
'''
        recovered = subprocess.run([sys.executable, "-B", "-c", recovery,
            str(self.project), str(self.state), str(self.root), str(branch_path)],
            capture_output=True, text=True, env=env, timeout=20)
        self.assertEqual(recovered.returncode, 0, recovered.stderr)
        record = json.loads(recovered.stdout)
        prefix = (Path(record["pack_path"]) / "prefix.txt").read_text(encoding="utf-8")
        self.assertIn("Project rules", prefix)
        self.assertIn("Fixed edge case", prefix)
        self.assertNotIn("Changed while offline", prefix)
        self.assertNotIn("Moved branch", prefix)
        self.assertEqual(context_status(self.state)["phase"], "PACK_DURABLE")

    def test_death_between_snapshot_rename_and_state_receipt_recovers_orphan(self):
        branch_path = self.root / "branch.json"
        branch_path.write_text(json.dumps(self.branch()), encoding="utf-8")
        hook = r"""
import json,os,sys
from pathlib import Path
import branchwrite.project_context as pc
branch=json.loads(Path(sys.argv[4]).read_text())
original=pc._publish
def stop_before_receipt(state,name,value):
    if name=="context-source-receipt.json": os._exit(78)
    return original(state,name,value)
pc._publish=stop_before_receipt
pc.capture_context_pack(Path(sys.argv[1]),Path(sys.argv[2]),read_files=("README.md",),read_dirs=("src",),branches=(branch,),as_of="2026-10-20T00:00:00Z")
"""
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        crashed = subprocess.run([sys.executable, "-B", "-c", hook,
            str(self.project), str(self.state), str(self.root), str(branch_path)],
            capture_output=True, text=True, env=env, timeout=20)
        self.assertEqual(crashed.returncode, 78, crashed.stderr)
        self.assertFalse((self.state / "context-source-receipt.json").exists())
        (self.project / "README.md").write_text("Changed after snapshot", encoding="utf-8")
        later = self.branch(revision=4, tip="c" * 64, text="Moved branch")
        recovered = capture_context_pack(self.project, self.state, read_files=("README.md",),
            read_dirs=("src",), branches=(later,), as_of="2026-10-20T01:00:00Z")
        prefix = (Path(recovered["pack_path"]) / "prefix.txt").read_text(encoding="utf-8")
        self.assertIn("Project rules", prefix)
        self.assertIn("Fixed edge case", prefix)
        self.assertNotIn("Changed after snapshot", prefix)
        self.assertNotIn("Moved branch", prefix)
        self.assertTrue((self.state / "context-source-receipt.json").exists())
        self.assertEqual(context_status(self.state)["phase"], "PACK_DURABLE")

    def test_parent_and_child_context_selections_are_rejected(self):
        with self.assertRaises(ValueError):
            capture_context_pack(self.project, self.state, read_files=("src",),
                read_dirs=("src/main.py",), branches=(), as_of="2026-10-20T00:00:00Z")

    def test_image_or_conflicting_branch_message_is_not_flattened(self):
        image_branch=self.branch()
        image_branch["history"]["messages"][0]["content"]=[{"type":"image","data":"..."}]
        with self.assertRaises(ValueError):
            capture_context_pack(self.project,self.state,read_files=("README.md",),
                read_dirs=(),branches=(image_branch,),as_of="2026-10-20T00:00:00Z")
        conflict=self.branch()
        conflict["history"]["messages"][0]["content"]="different projection"
        with self.assertRaises(ValueError):
            capture_context_pack(self.project,self.state,read_files=("README.md",),
                read_dirs=(),branches=(conflict,),as_of="2026-10-20T00:00:00Z")

    def test_active_or_mismatched_branch_is_rejected(self):
        with self.assertRaises(ValueError):
            capture_context_pack(self.project, self.state, read_files=("README.md",),
                read_dirs=(), branches=(self.branch(active=True),), as_of="2026-10-20T00:00:00Z")
        mismatched = self.branch()
        mismatched["history"]["tip"] = "c" * 64
        with self.assertRaises(ValueError):
            capture_context_pack(self.project, self.state, read_files=("README.md",),
                read_dirs=(), branches=(mismatched,), as_of="2026-10-20T00:00:00Z")
        self.assertFalse((self.state / "context-source-receipt.json").exists())

    def test_symlinked_source_is_rejected(self):
        outside = self.root / "outside.txt"
        outside.write_text("private", encoding="utf-8")
        (self.project / "linked.txt").symlink_to(outside)
        with self.assertRaises(ValueError):
            capture_context_pack(self.project, self.state, read_files=(), read_dirs=(".",),
                branches=(), as_of="2026-10-20T00:00:00Z")
        self.assertFalse((self.state / "context-source-receipt.json").exists())

if __name__ == "__main__":
    unittest.main()
