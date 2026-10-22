"""Real COW HTTP forks, isolated files, process checks and one workflow ledger.

Scripted tool proposals exercise orchestration, not autonomous model competence.
"""
import json
import hashlib
from pathlib import Path
import threading
import unittest
from unittest.mock import patch
from tests import test_cow_client_flow as fixture
from branchwrite.execution import Executor, Grant
from branchwrite.tool_registry import ToolRegistry
from branchwrite.records import RuntimeLog, Artifact, decode
from branchwrite.kernel import FrameKernel
from branchwrite.interpreter import Interpreter, Value, AdmissionError
from branchwrite.model_dispatch import ModelAdapter
from branchwrite.parallel_dispatch import DispatchPool


class ExplorationTests(unittest.TestCase):
    def setUp(self):
        self.case=fixture.CowClientFlowTests();self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.client=self.case._client('http','explore')
        namespace=self.client.create_namespace('Exploration','explore-ns')['namespace_id']
        self.client.prepare('explore-base',namespace,'Shared project context.','explore-root')
        self.head=self.client.head('explore-base')
        self.root=Path(self.case.temp.name)/'bw';self.root.mkdir()
        self.source=self.root/'source';self.source.mkdir()
        (self.source/'tests').mkdir();(self.source/'tests/__init__.py').write_text('')
        (self.source/'tests/test_candidate.py').write_text('import unittest\nfrom pathlib import Path\nclass Check(unittest.TestCase):\n def test_result(self):\n  self.assertIn(Path("new.txt").read_text(), ("left", "right"))\n')
        self.parent=ToolRegistry(Executor.create(self.source,self.root/'parent'),Grant((),False))
        self.worlds={}
        for name in ('left','right'):
            registry=ToolRegistry(Executor.create(self.source,self.root/name),Grant((),True,create_paths=('new.txt',)))
            self.worlds[name]=dict(registry=registry)
        self.log=RuntimeLog(self.root/'ledger')
        self.addCleanup(lambda:None if self.log._closed else self.log.close())
        self.kernel=FrameKernel(self.log)
        self.pool=DispatchPool(2);self.addCleanup(self.pool.close)
        self.adapter=ModelAdapter(self.client,run_id='explore-run',model_contract_id='flow-model',execution_profile_id='flow-profile',eos_tokens=(299,))
        self.runtime=Interpreter(self.kernel,self.parent,adapter=self.adapter,worlds=self.worlds,
            parallel_budgets={'bounded':dict(max_parallel=2,max_requests=8,max_output_tokens=64)},dispatcher=self.pool)

    def program(self, *, rule='verified-first'):
        lines=['FLOW explore','PARALLEL.DO candidates base=current budget=bounded']
        for name in ('left','right'):
            lines.extend([f'BRANCH {name} base=current world={name}',
                f'PLAN create from={name}-request against=world -> creation',
                'ACT write plan=creation -> written',
                'PLAN test from=test-request against=world -> test-plan',
                'ACT check plan=test-plan -> checked',
                'PLAN finish from=finish-request against=world -> finish-plan',
                'ACT finish plan=finish-plan -> outcome',
                'VERIFY verdict input=outcome contract=unit-tests-and-finish -> verified','END'])
        lines.extend(['END',f'SELECT choose input=candidates rule={rule} -> selected','END'])
        return '\n'.join(lines)+'\n'

    def bindings(self, right='right'):
        def proposal(tool,**arguments):return Value('ToolProposal',json.dumps(dict(tool=tool,arguments=arguments)))
        return {'current':Value('COWSource',dict(head=dict(name=self.head.name,revision=self.head.revision,root=self.head.root,tip=self.head.tip),mode='ask')),
            'left-request':proposal('create_file',path='new.txt',content='left'),
            'right-request':proposal('create_file',path='new.txt',content=right),
            'test-request':proposal('run_tests',suite='unit'),
            'finish-request':proposal('finish',answer='Checked candidate.')}

    def test_two_approaches_overlap_verify_and_select_without_changing_source(self):
        barrier=threading.Barrier(2)
        for spec in self.worlds.values():
            registry=spec['registry'];original=registry.execute
            def execute(plan,operation,original=original):
                if decode(plan.data)[3]=='create_file':barrier.wait(3)
                return original(plan,operation)
            registry.execute=execute
        self.runtime.start(self.program(),self.bindings())
        result=self.runtime.run(max_steps=256)
        self.assertEqual(result.status,'complete');self.assertTrue(result.value['verified'])
        candidates=result.value['bindings']['candidates'][1]['candidates']
        self.assertEqual([c['verified'] for c in candidates],[True,True])
        self.assertEqual(result.value['bindings']['selected'][1]['selected']['name'],'left')
        self.assertFalse((self.source/'new.txt').exists())
        self.assertFalse((self.parent.executor.workspace/'new.txt').exists())
        self.assertEqual((self.worlds['left']['registry'].executor.workspace/'new.txt').read_text(),'left')
        self.assertEqual((self.worlds['right']['registry'].executor.workspace/'new.txt').read_text(),'right')
        self.assertEqual(self.client.head('explore-base'),self.head)
        self.assertEqual(sum(f['contract']==('COWForkReceipt','record') for f in self.kernel.frames()),2)

    def test_failure_is_retained_and_only_passing_candidate_is_selected(self):
        self.runtime.start(self.program(rule='right'),self.bindings(right='wrong'))
        result=self.runtime.run(max_steps=256)
        self.assertFalse(result.value['verified'])
        self.assertIsNone(result.value['bindings']['selected'][1]['selected'])
        self.assertEqual([c['verified'] for c in result.value['bindings']['candidates'][1]['candidates']],[True,False])

    def test_changed_candidate_cannot_be_selected(self):
        self.runtime.start(self.program(),self.bindings())
        while self.kernel.frame('program')['pc']<1:self.runtime.step()
        (self.worlds['left']['registry'].executor.workspace/'new.txt').write_text('post-check change')
        with self.assertRaisesRegex(AdmissionError,'changed'):self.runtime.run(max_steps=32)

    def test_overlapping_worlds_reject_before_any_cow_fork_or_tool(self):
        bad=Interpreter(self.kernel,self.parent,adapter=self.adapter,
            worlds={'left':self.worlds['left'],'right':self.worlds['left']},
            parallel_budgets=self.runtime.parallel_budgets,dispatcher=self.pool)
        with self.assertRaisesRegex(AdmissionError,'overlap'):bad.start(self.program(),self.bindings())
        self.assertEqual(self.log.event_count,0)

    def test_budget_rejects_frozen_overcommit_before_admission(self):
        program=self.program().replace('PLAN create from=left-request against=world -> creation',
            'EXPAND proposed from=current profile=large task=message\nPLAN create from=proposed against=world -> creation')
        runtime=Interpreter(self.kernel,self.parent,adapter=self.adapter,worlds=self.worlds,
            profiles={'large':dict(max_requests=10,max_output_tokens=128)},
            parallel_budgets=self.runtime.parallel_budgets,dispatcher=self.pool)
        with self.assertRaisesRegex(AdmissionError,'budget'):
            runtime.start(program,dict(self.bindings(),message=Value('Text','Try an approach.')))
        self.assertEqual(self.log.event_count,0)

    def test_review_and_export_read_only_the_selected_verified_workspace(self):
        from branchwrite.coding_cli import build_launch,enable_exploration,save_launch
        from branchwrite.project_baseline import capture,BINDING,reference_text
        from branchwrite.coding_review import inspect_changes
        from branchwrite.project_export import export_changes
        import zipfile
        self.root.chmod(0o700)
        self.parent=ToolRegistry(Executor.create(self.source,self.root/'world'),Grant((),False))
        (self.root/'candidates').mkdir()
        worlds={name:dict(registry=ToolRegistry(Executor.create(self.source,self.root/'candidates'/name),
            Grant((),True,create_paths=('new.txt',)))) for name in ('first','second')}
        connection=dict(endpoint_url='http://127.0.0.1:1',endpoint_pin='fixture',
            model_contract_id='flow-model',execution_profile_id='flow-profile',eos_tokens=[299])
        launch=build_launch(self.source,'Try two checked solutions',connection,branch='explore-base',
            create_paths=['new.txt'],test_commands=['python3 -m unittest'])
        enable_exploration(launch,selection='second');save_launch(self.root,launch)
        baseline=capture(self.log,self.parent)
        digest=hashlib.sha256(json.dumps(launch['config'],sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()
        bindings=dict(self.bindings(),**{'host-config-sha256':Value('Text',digest),
            BINDING:Value('Text',reference_text(baseline))})
        runtime=Interpreter(self.kernel,self.parent,adapter=self.adapter,worlds=worlds,
            parallel_budgets=self.runtime.parallel_budgets,dispatcher=self.pool)
        program=self.program(rule='right').replace('BRANCH left base=current world=left',
            'BRANCH first base=current world=first').replace('BRANCH right base=current world=right',
            'BRANCH second base=current world=second').replace('rule=right','rule=second')
        runtime.start(program,bindings)
        self.assertTrue(runtime.run(max_steps=256).value['verified'])
        # Reviews take a separate read lock, just as a later CLI process does.
        self.log.close()
        review=inspect_changes(self.root)
        self.assertEqual([row['path'] for row in review['changes']],['new.txt'])
        self.assertEqual(review['changes'][0]['after_sha256'],hashlib.sha256(b'right').hexdigest())
        destination=self.root.parent/'selected-export.zip'
        export_changes(self.root,destination)
        with zipfile.ZipFile(destination) as archive:
            self.assertEqual(archive.read('payloads/'+hashlib.sha256(b'right').hexdigest()),b'right')
            self.assertNotIn('payloads/'+hashlib.sha256(b'left').hexdigest(),archive.namelist())
        self.assertFalse((self.source/'new.txt').exists())


if __name__=='__main__':unittest.main()
