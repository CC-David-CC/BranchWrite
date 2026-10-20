"""Related real Git worktrees, shared canonical prefix, independent HTTP tips.

Real local HTTP/Store with CPU FlowModel; no GPU sharing or autonomous claim.
"""
from collections import defaultdict
from pathlib import Path
import unittest
import test_related_worktrees as worlds_fixture
import test_cow_client_flow as cow_fixture

class RelatedWorktreeHistoryTests(unittest.TestCase):
 def test_common_computation_root_does_not_merge_worktree_effect_authority(self):
  worlds=worlds_fixture.RelatedWorktreeTests();self.addCleanup(worlds.doCleanups);worlds.setUp()
  cow=cow_fixture.CowClientFlowTests();self.addCleanup(cow.doCleanups);cow.setUp();client=cow._client('http','worktrees')
  ns=client.create_namespace('Related worktrees','related-ns')['namespace_id']
  revision=worlds.git('rev-parse','HEAD').strip()
  common=client.load_context('common',ns,[dict(role='system',content='Shared repository revision '+revision+'. Treat each worktree and its tool observations separately.')],'common-root').receipt.branch
  a=client.fork('common',common.tip,'task-a','fork-a');b=client.fork('common',common.tip,'task-b','fork-b')
  self.assertEqual(a.tip,common.tip);self.assertEqual(b.tip,common.tip)
  cow.models[0].plans=defaultdict(lambda:(ord('x'),299))
  answer_a=client.ask('task-a',a.revision,'ask-a','Diagnose task A in tool world '+worlds.registries[0].world,16)
  self.assertEqual(client.head('task-b'),b);self.assertEqual(client.head('common'),common)
  answer_b=client.ask('task-b',b.revision,'ask-b','Review task B in tool world '+worlds.registries[1].world,16)
  self.assertNotEqual(answer_a.receipt.branch.tip,answer_b.receipt.branch.tip)
  self.assertEqual(answer_a.receipt.branch.root,answer_b.receipt.branch.root);self.assertEqual(client.head('common'),common)
  # The same host isolation checks apply even with a shared COW ancestor.
  left,right=worlds.registries
  seen=left.execute(left.freeze(worlds.proposal('read_file',path='main.py')),'read-a').observation
  from branchwrite.execution import ToolRejected
  with self.assertRaises(ToolRejected):right.freeze(worlds.proposal('replace',path='main.py',before='0',after='1'),observations=(seen,))
  self.assertEqual((worlds.executors[1].workspace/'main.py').read_text(),'value = 0\n')
