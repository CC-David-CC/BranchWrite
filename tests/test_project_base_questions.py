"""Project Base is the existing GoldenPath implementation, not another store."""
from collections import defaultdict
from dataclasses import replace
import unittest
import test_cow_client_flow as fixture

class ProjectBaseQuestionTests(unittest.TestCase):
 def setUp(self):
  from branchwrite.golden_path import ProjectBase
  self.case=fixture.CowClientFlowTests();self.addCleanup(self.case.doCleanups);self.case.setUp();self.client=self.case._client('http','project-base')
  ns=self.client.create_namespace('Project Base','project-base-ns')['namespace_id'];self.base=ProjectBase(self.client,ns,eos_tokens=(299,));self.version=self.base.start('base','Work on this pinned project.',(), 'base-root')
  self.case.models[0].plans=defaultdict(lambda:(257,299))
 def question(self,source=None,**kw):
  args=dict(source=self.version if source is None else source,branch='question',question='What test should I run?',fork_operation='question-fork',question_operation='question-generate',max_tokens=2);args.update(kw);return self.base.question(**args)
 def test_public_name_is_one_implementation_and_questions_leave_base_unchanged(self):
  from branchwrite.golden_path import ProjectBase,GoldenPath
  self.assertIs(ProjectBase,GoldenPath);before=self.client.head('base')
  first=self.question();second=self.question(branch='other',question='Where is the failure?',fork_operation='other-fork',question_operation='other-generate')
  self.assertEqual(self.client.head('base'),before);self.assertNotEqual(first.receipt.snapshot,second.receipt.snapshot)
  self.assertEqual(self.client.journal.read('question-fork')['source_binding']['snapshot'],self.version.snapshot)
 def test_question_on_summary_version_uses_append_without_editing_reference(self):
  from branchwrite.golden_path import Observation
  observation=Observation.from_bytes('tests','run-1',b'OK','Tests passed at the recorded revision.',observed_ns=10)
  version=self.base.refresh(self.version,'base-v1',(observation,),'refresh-fork','refresh-summary',2,now_ns=11)
  before=self.client.head(version.branch);self.question(source=version)
  self.assertEqual(self.client.journal.read('question-generate')['path'],'/cow/text/append-user');self.assertEqual(self.client.head(version.branch),before)
 def test_invalid_question_rejected_before_fork(self):
  for question in ['',None,'x'*65537]:
   with self.subTest(question=type(question)),self.assertRaises(ValueError):self.question(question=question)
  self.assertIsNone(self.client.journal.read('question-fork'))
 def test_foreign_endpoint_version_rejected_before_transport(self):
  with self.assertRaises(ValueError):self.question(source=replace(self.version,endpoint_pin='another-server'))
  self.assertIsNone(self.client.journal.read('question-fork'))
 def test_retry_retains_original_ids_and_does_not_generate_again(self):
  first=self.question();before=len(self.case.trace);second=self.question()
  self.assertEqual(second.receipt,first.receipt);self.assertEqual(len(self.case.trace),before)
  from branchwrite.cow_client import OperationReuseError
  with self.assertRaises(OperationReuseError):self.question(question='Different work with the same IDs.')
  self.assertEqual(len(self.case.trace),before)

 def test_competing_base_versions_remain_independent_and_questions_pin_each(self):
  from branchwrite.golden_path import Observation
  first=Observation.from_bytes('commands','run-a',b'command A passed','Command A passed on its pinned revision.',observed_ns=10)
  second=Observation.from_bytes('commands','run-b',b'command B passed','Command B passed on its pinned revision.',observed_ns=10)
  a=self.base.refresh(self.version,'candidate-a',(first,),'candidate-a-fork','candidate-a-summary',2,now_ns=11)
  b=self.base.refresh(self.version,'candidate-b',(second,),'candidate-b-fork','candidate-b-summary',2,now_ns=11)
  self.assertEqual(a.parent_snapshot,b.parent_snapshot);self.assertNotEqual(a.snapshot,b.snapshot)
  before_a=self.client.head(a.branch);before_b=self.client.head(b.branch)
  self.question(source=a,branch='ask-a',fork_operation='ask-a-fork',question_operation='ask-a-gen')
  self.question(source=b,branch='ask-b',fork_operation='ask-b-fork',question_operation='ask-b-gen')
  self.assertEqual(self.client.head(a.branch),before_a);self.assertEqual(self.client.head(b.branch),before_b)
  self.assertEqual(self.client.journal.read('ask-a-fork')['source_binding']['snapshot'],a.snapshot)
  self.assertEqual(self.client.journal.read('ask-b-fork')['source_binding']['snapshot'],b.snapshot)
