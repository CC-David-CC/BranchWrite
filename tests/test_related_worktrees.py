"""Real Git worktrees stay separate tool worlds despite identical input bytes."""
import json,os,subprocess,tempfile,unittest
from pathlib import Path
from branchwrite.execution import Executor,Grant,ToolRejected
from branchwrite.tool_registry import ToolRegistry

class RelatedWorktreeTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.repo=self.root/'repo';self.repo.mkdir()
  self.git_env={k:v for k,v in os.environ.items() if not k.startswith('GIT_')};self.git_env.update(GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL='/dev/null',GIT_TERMINAL_PROMPT='0')
  self.git('init','-q');(self.repo/'main.py').write_text('value = 0\n');(self.repo/'tests').mkdir();(self.repo/'tests/test_main.py').write_text('import unittest\nfrom main import value\nclass Check(unittest.TestCase):\n def test_value(self):self.assertEqual(value,1)\n')
  self.git('add','.');self.git('commit','-qm','owned fixture baseline')
  self.sources=[];self.executors=[];self.registries=[]
  for label in ['a','b']:
   source=self.root/('tree-'+label);self.git('worktree','add','-q','-b','task-'+label,str(source))
   e=Executor.create(source,self.root/('world-'+label),project_input=True)
   self.sources.append(source);self.executors.append(e);self.registries.append(ToolRegistry(e,Grant(('main.py',),True,read_paths=('main.py',))))
 def git(self,*args):return subprocess.check_output(['git','-c','user.name=Owned fixture','-c','user.email=fixture@invalid','-c','core.hooksPath=/dev/null',*args],cwd=self.repo,env=self.git_env,stderr=subprocess.STDOUT,text=True)
 def proposal(self,tool,**args):return json.dumps(dict(tool=tool,arguments=args))
 def test_real_worktree_administration_is_excluded_from_both_worlds(self):
  for source,e in zip(self.sources,self.executors):
   self.assertTrue((source/'.git').is_file());self.assertFalse((e.workspace/'.git').exists())
  self.assertNotEqual(self.registries[0].world,self.registries[1].world)
  self.assertEqual(self.git('status','--porcelain'),'')
 def test_equal_file_hash_does_not_allow_foreign_observation_or_plan(self):
  a,b=self.registries
  observed=a.execute(a.freeze(self.proposal('read_file',path='main.py')),'read-a').observation
  own=b.execute(b.freeze(self.proposal('read_file',path='main.py')),'read-b').observation
  self.assertEqual(observed.sha256,own.sha256);self.assertNotEqual(observed.world,own.world)
  change=self.proposal('replace',path='main.py',before='0',after='1')
  with self.assertRaises(ToolRejected):b.freeze(change,observations=(observed,))
  plan=a.freeze(change,observations=(observed,))
  with self.assertRaises(ToolRejected):b.execute(plan,'foreign-plan')
  self.assertEqual((self.executors[1].workspace/'main.py').read_text(),'value = 0\n')
 def test_edit_and_passing_tests_in_a_do_not_change_b_or_sources(self):
  a,b=self.registries;observation=a.execute(a.freeze(self.proposal('read_file',path='main.py')),'read').observation
  a.execute(a.freeze(self.proposal('replace',path='main.py',before='0',after='1'),observations=(observation,)),'edit-a')
  passed=a.execute(a.freeze(self.proposal('run_tests',suite='unit')),'tests-a');failed=b.execute(b.freeze(self.proposal('run_tests',suite='unit')),'tests-b')
  self.assertEqual(passed.exit_code,0,passed.stderr);self.assertEqual(failed.exit_code,1);self.assertIn(b'AssertionError',failed.stderr)
  for source in self.sources:self.assertEqual((source/'main.py').read_text(),'value = 0\n')
  self.assertEqual((self.executors[1].workspace/'main.py').read_text(),'value = 0\n');self.assertEqual(self.git('status','--porcelain'),'')
