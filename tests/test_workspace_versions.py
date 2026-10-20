"""Real Git/file checkpoints: independent file/context bases and crash settlement."""
import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

class WorkspaceVersionsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name); self.project=self.root/"project"; self.project.mkdir()
        (self.project/"a.txt").write_text("original A\n")
        (self.project/"b.txt").write_text("original B\n")
        from branchwrite.workspace_versions import WorkspaceVersions
        self.versions=WorkspaceVersions(self.project,self.root/"versions")
        self.context=dict(branch="main",tip="a"*64,root="b"*64,revision=1,
            model_contract_id="model",execution_profile_id="profile")
    def capture(self,name,**kwargs):
        return self.versions.capture(name,context=kwargs.pop("context",self.context),**kwargs)
    def test_checkpoint_preserves_user_git_index_head_and_dirty_files(self):
        def git(*args): return subprocess.check_output(["git","-C",str(self.project),*args])
        git("init","-q");git("add","a.txt")
        git("-c","user.name=Test","-c","user.email=test@invalid","commit","-qm","baseline")
        (self.project/"a.txt").write_text("user unstaged\n");git("add","b.txt")
        before={f:(self.project/".git"/f).read_bytes() for f in ("HEAD","index","refs/heads/master") if (self.project/".git"/f).exists()}
        status=git("status","--porcelain=v1","-z")
        receipt=self.capture("before-work")
        self.assertTrue(receipt["commit"])
        self.assertEqual(git("status","--porcelain=v1","-z"),status)
        self.assertEqual(before,{f:(self.project/".git"/f).read_bytes() for f in before})
        self.assertEqual(self.versions.read(receipt["commit"])["context"],self.context)
    def test_old_context_with_new_files_uses_isolated_worktree(self):
        old=self.capture("old")
        (self.project/"a.txt").write_text("newer A\n")
        new=self.capture("new",context=dict(self.context,tip="c"*64,revision=2),parent=old["commit"])
        path=self.root/"alternative"
        result=self.versions.explore("experiment",context_commit=old["commit"],files_commit=new["commit"],destination=path)
        self.assertEqual(result["context"],self.context)
        self.assertEqual(result["file_commit"],new["commit"])
        self.assertEqual((path/"a.txt").read_text(),"newer A\n")
        (path/"a.txt").write_text("candidate A\n")
        self.assertEqual((self.project/"a.txt").read_text(),"newer A\n")
        self.assertEqual(self.versions.read(old["commit"])["context"],self.context)
    def versions_with_changes(self):
        old=self.capture("baseline")
        (self.project/"a.txt").write_text("candidate A\n")
        (self.project/"b.txt").write_text("candidate B\n")
        new=self.capture("candidate",parent=old["commit"])
        (self.project/"a.txt").write_text("original A\n")
        (self.project/"b.txt").write_text("original B\n")
        return old["commit"],new["commit"]
    def test_guarded_publication_keeps_unrelated_user_edits_and_is_idempotent(self):
        old,new=self.versions_with_changes()
        (self.project/"notes.txt").write_text("new user notes\n")
        result=self.versions.publish("publish-one",old,new)
        self.assertEqual(result["status"],"committed")
        self.assertEqual((self.project/"a.txt").read_text(),"candidate A\n")
        self.assertEqual((self.project/"notes.txt").read_text(),"new user notes\n")
        again=self.versions.publish("publish-one",old,new)
        self.assertEqual(again,result)
    def test_conflicting_preimage_fails_before_first_write(self):
        old,new=self.versions_with_changes()
        (self.project/"b.txt").write_text("user changed B\n")
        with self.assertRaisesRegex(ValueError,"changed|conflict"):
            self.versions.publish("conflict",old,new)
        self.assertEqual((self.project/"a.txt").read_text(),"original A\n")
        self.assertEqual((self.project/"b.txt").read_text(),"user changed B\n")
    def test_crash_after_one_file_recovers_same_intent(self):
        old,new=self.versions_with_changes()
        def kill(phase,path):
            if phase=="file_durable":raise RuntimeError("simulated lost process")
        with self.assertRaisesRegex(RuntimeError,"lost process"):
            self.versions.publish("interrupted",old,new,observer=kill)
        self.assertEqual((self.project/"a.txt").read_text(),"candidate A\n")
        self.assertEqual((self.project/"b.txt").read_text(),"original B\n")
        from branchwrite.workspace_versions import WorkspaceVersions
        restarted=WorkspaceVersions(self.project,self.root/"versions")
        result=restarted.publish("interrupted",old,new)
        self.assertEqual(result["status"],"committed")
        self.assertEqual((self.project/"b.txt").read_text(),"candidate B\n")
        with self.assertRaisesRegex(ValueError,"different"):
            restarted.publish("interrupted",new,old)
    def test_crash_recovery_does_not_overwrite_intervening_edit(self):
        old,new=self.versions_with_changes()
        def kill(phase,path):
            if phase=="file_durable":raise RuntimeError("stop")
        with self.assertRaises(RuntimeError):self.versions.publish("partial",old,new,observer=kill)
        (self.project/"a.txt").write_text("my intervening change\n")
        with self.assertRaisesRegex(ValueError,"changed|conflict"):
            self.versions.publish("partial",old,new)
        self.assertEqual((self.project/"a.txt").read_text(),"my intervening change\n")
    def test_symlink_cannot_redirect_capture_or_publication(self):
        old,new=self.versions_with_changes()
        outside=self.root/"outside";outside.write_text("do not touch\n")
        (self.project/"a.txt").unlink();(self.project/"a.txt").symlink_to(outside)
        with self.assertRaises((ValueError,RuntimeError)):self.capture("symlink")
        with self.assertRaises((ValueError,RuntimeError)):self.versions.publish("redirect",old,new)
        self.assertEqual(outside.read_text(),"do not touch\n")
    def test_version_names_cannot_escape_or_rebind_a_checkpoint(self):
        first=self.capture("stable")
        with self.assertRaises(ValueError):self.capture("../../escape")
        (self.project/"a.txt").write_text("changed\n")
        with self.assertRaisesRegex(ValueError,"different|exists"):
            self.capture("stable")
        self.assertEqual(self.versions.read(first["commit"])["context"],self.context)
    def test_restore_removes_only_files_owned_by_the_checkpoint_delta(self):
        old=self.capture("before")
        (self.project/"new.txt").write_text("mine\n")
        new=self.capture("after",parent=old["commit"])
        (self.project/"user.txt").write_text("keep\n")
        self.versions.publish("step-back",new["commit"],old["commit"])
        self.assertFalse((self.project/"new.txt").exists())
        self.assertEqual((self.project/"user.txt").read_text(),"keep\n")

    def test_new_nested_file_and_executable_mode_survive_version_restore(self):
        old=self.capture("empty-nested")
        (self.project/"src").mkdir();(self.project/"src/run.sh").write_text("#!/bin/sh\nexit 0\n")
        (self.project/"src/run.sh").chmod(0o750)
        new=self.capture("with-nested",parent=old["commit"])
        (self.project/"src/run.sh").unlink();(self.project/"src").rmdir()
        self.versions.publish("nested",old["commit"],new["commit"])
        self.assertEqual((self.project/"src/run.sh").stat().st_mode & 0o777,0o750)
        self.assertEqual((self.project/"src/run.sh").read_text(),"#!/bin/sh\nexit 0\n")
    def test_real_process_exit_after_first_write_is_recovered(self):
        old,new=self.versions_with_changes()
        import sys
        code="""import os,sys
from branchwrite.workspace_versions import WorkspaceVersions
v=WorkspaceVersions(sys.argv[1],sys.argv[2])
def stop(phase,path):
    if phase=='file_durable':os._exit(17)
v.publish('process-crash',sys.argv[3],sys.argv[4],observer=stop)
"""
        result=subprocess.run([sys.executable,"-c",code,str(self.project),str(self.root/"versions"),old,new])
        self.assertEqual(result.returncode,17)
        self.assertEqual((self.project/"a.txt").read_text(),"candidate A\n")
        self.assertEqual((self.project/"b.txt").read_text(),"original B\n")
        self.assertEqual(self.versions.publish("process-crash",old,new)["status"],"committed")
        self.assertEqual((self.project/"b.txt").read_text(),"candidate B\n")
