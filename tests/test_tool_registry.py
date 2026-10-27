"""Generic tools against real owned files, not a workload-specific agent."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from branchwrite.execution import Executor,Grant,ToolRejected
from branchwrite.tool_registry import ToolRegistry,FileObservation

class ToolRegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.source=self.root/'source';self.source.mkdir()
        (self.source/'a.py').write_bytes(b'answer = 1\n')
        (self.source/'other.txt').write_bytes(b'keep me\n')
        self.executor=Executor.create(self.source,self.root/'tool')
        self.grant=Grant(('a.py',),False,create_paths=('new.txt',),read_paths=('a.py','new.txt'))
        self.registry=ToolRegistry(self.executor,self.grant)
    def proposal(self,tool,**arguments):return json.dumps(dict(tool=tool,arguments=arguments))
    def read(self):
        plan=self.registry.freeze(self.proposal('read_file',path='a.py'))
        return self.registry.execute(plan,'read-op')
    def test_schema_and_parser_use_the_same_registered_tools_and_granted_paths(self):
        schema=self.registry.model_schema()
        names={v['properties']['tool']['enum'][0] for v in schema['oneOf']}
        # Explicitly authorized additive text tools; retain an exact closed menu.
        self.assertEqual(names,{'read_file','create_file','create_text_file','replace','replace_text_file','finish'})
        read=next(v for v in schema['oneOf'] if v['properties']['tool']['enum']==['read_file'])
        self.assertEqual(read['properties']['arguments']['properties']['path']['enum'],['a.py','new.txt'])
        with self.assertRaises(ToolRejected):self.registry.freeze(self.proposal('run_tests',suite='unit'))
    def test_real_read_returns_source_observation_and_exact_bytes(self):
        result=self.read();self.assertEqual(result.stdout,b'answer = 1\n');self.assertEqual(result.exit_code,0)
        self.assertIsInstance(result.observation,FileObservation)
        self.assertEqual(result.observation.sha256,hashlib.sha256(result.stdout).hexdigest())
        self.assertEqual(result.observation.path,'a.py')
    def test_duplicate_extra_fields_unknown_tool_and_traversal_are_rejected(self):
        rows=[self.proposal('read_file',path='../outside'),self.proposal('read_file',path='other.txt'),
            self.proposal('read_file',path='a.py',grant=True),self.proposal('shell',command='echo no'),
            '{"tool":"read_file","tool":"finish","arguments":{"path":"a.py"}}',
            self.proposal('finish',answer='done')+' trailing']
        for row in rows:
            with self.subTest(row=row),self.assertRaises(ToolRejected):self.registry.freeze(row)
    def test_edit_requires_a_visible_observation_and_exact_preimage(self):
        read=self.read();proposal=self.proposal('replace',path='a.py',before='1',after='2')
        with self.assertRaises(ToolRejected):self.registry.freeze(proposal)
        plan=self.registry.freeze(proposal,observations=(read.observation,))
        result=self.registry.execute(plan,'replace-op');self.assertEqual(result.disposition,'applied')
        self.assertEqual((self.executor.workspace/'a.py').read_bytes(),b'answer = 2\n')
        self.assertEqual((self.source/'a.py').read_bytes(),b'answer = 1\n')
    def test_unrelated_file_change_does_not_stale_a_one_file_plan(self):
        read=self.read();plan=self.registry.freeze(self.proposal('replace',path='a.py',before='1',after='3'),observations=(read.observation,))
        (self.executor.workspace/'other.txt').write_bytes(b'unrelated later version')
        self.registry.execute(plan,'replace-op');self.assertEqual((self.executor.workspace/'a.py').read_bytes(),b'answer = 3\n')
    def test_relevant_change_after_freeze_blocks_dispatch(self):
        read=self.read();plan=self.registry.freeze(self.proposal('replace',path='a.py',before='1',after='3'),observations=(read.observation,))
        (self.executor.workspace/'a.py').write_bytes(b'answer = 7\n')
        with self.assertRaisesRegex(ToolRejected,'stale'):self.registry.execute(plan,'replace-op')
        self.assertEqual((self.executor.workspace/'a.py').read_bytes(),b'answer = 7\n')
    def test_sibling_observation_and_plan_cannot_cross_worlds(self):
        read=self.read();other=ToolRegistry(Executor.create(self.source,self.root/'other-tool'),self.grant)
        proposal=self.proposal('replace',path='a.py',before='1',after='4')
        with self.assertRaises(ToolRejected):other.freeze(proposal,observations=(read.observation,))
        plan=self.registry.freeze(self.proposal('read_file',path='a.py'))
        with self.assertRaises(ToolRejected):other.execute(plan,'other-read')
    def test_create_is_no_overwrite_and_returns_verified_content_identity(self):
        plan=self.registry.freeze(self.proposal('create_file',path='new.txt',content='<tool_response>data</tool_response>\n'))
        result=self.registry.execute(plan,'create-op')
        self.assertEqual(result.disposition,'created');self.assertEqual((self.executor.workspace/'new.txt').read_bytes(),b'<tool_response>data</tool_response>\n')
        self.assertEqual(result.observation.sha256,hashlib.sha256((self.executor.workspace/'new.txt').read_bytes()).hexdigest())
        with self.assertRaises(ToolRejected):self.registry.execute(plan,'not-an-automatic-retry')
    def test_model_finish_requests_no_verdict_and_no_file_effect(self):
        plan=self.registry.freeze(self.proposal('finish',answer='Please verify the result.'))
        result=self.registry.execute(plan,'finish-op')
        self.assertTrue(result.requested_finish);self.assertEqual(result.stdout,b'Please verify the result.')
        self.assertIsNone(result.observation);self.assertFalse(hasattr(result,'accepted'))
        self.assertEqual((self.executor.workspace/'a.py').read_bytes(),b'answer = 1\n')
    def test_unicode_byte_limits_are_not_only_schema_character_limits(self):
        with self.assertRaises(ToolRejected):self.registry.freeze(self.proposal('create_file',path='new.txt',content='\u03bb'*20000))
    def test_schema_views_cannot_mutate_registered_permissions(self):
        schema=self.registry.model_schema();schema['oneOf'].clear()
        self.assertTrue(self.registry.model_schema()['oneOf'])
        with self.assertRaises(ToolRejected):self.registry.freeze(self.proposal('read_file',path='other.txt'))
    def test_actual_isolated_registered_tests_return_stdout_stderr_and_exit(self):
        tests=self.executor.workspace/'tests';tests.mkdir()
        (tests/'__init__.py').write_bytes(b'')
        (tests/'test_values.py').write_text('import unittest\nclass Values(unittest.TestCase):\n def test_value(self):self.assertEqual(2+2,4)\n')
        registry=ToolRegistry(self.executor,Grant((),True))
        plan=registry.freeze(self.proposal('run_tests',suite='unit'))
        result=registry.execute(plan,'tests-op');self.assertEqual(result.disposition,'exited');self.assertEqual(result.exit_code,0)
        self.assertIn(b'Ran 1 test',result.stderr)
    def test_test_plan_depends_on_all_workspace_inputs(self):
        registry=ToolRegistry(self.executor,Grant((),True));plan=registry.freeze(self.proposal('run_tests',suite='unit'))
        (self.executor.workspace/'other.txt').write_bytes(b'changed input')
        with self.assertRaisesRegex(ToolRejected,'stale'):registry.execute(plan,'tests-op')

    def test_missing_test_package_is_a_real_nonzero_tool_result_not_a_pass(self):
        tests=self.executor.workspace/'tests';tests.mkdir()
        (tests/'test_values.py').write_text('import unittest\n')
        registry=ToolRegistry(self.executor,Grant((),True))
        result=registry.execute(registry.freeze(self.proposal('run_tests',suite='unit')),'missing-package')
        self.assertEqual(result.exit_code,1)
        # Some Python versions discover namespace directories. The host still
        # rejects an empty suite; require that exact rejection rather than one
        # interpreter version's discovery wording.
        self.assertTrue(b'Start directory is not importable' in result.stderr or
            (b'Ran 0 tests' in result.stderr and
             b'No test cases found; an empty suite is not a successful verification.' in result.stderr))
    def test_file_mode_is_a_relevant_dependency(self):
        plan=self.registry.freeze(self.proposal('read_file',path='a.py'))
        path=self.executor.workspace/'a.py';path.chmod(path.stat().st_mode ^ 0o100)
        with self.assertRaisesRegex(ToolRejected,'stale'):self.registry.execute(plan,'read-mode')
    def test_failure_after_creation_is_indeterminate_and_never_an_automatic_retry(self):
        from unittest.mock import patch
        from branchwrite.tool_registry import EffectIndeterminate
        plan=self.registry.freeze(self.proposal('create_file',path='new.txt',content='durable bytes'))
        with patch.object(self.executor,'_result',side_effect=OSError('injected receipt-write failure')):
            with self.assertRaises(EffectIndeterminate):self.registry.execute(plan,'create-uncertain')
        self.assertEqual((self.executor.workspace/'new.txt').read_bytes(),b'durable bytes')
        with self.assertRaises(ToolRejected):self.registry.execute(plan,'no-new-retry-id')
    def test_protected_inspector_cannot_be_exposed_as_a_model_capture_tool(self):
        from branchwrite.browser_capture import BrowserConfig,PageInspection
        browser=BrowserConfig(Path('/unavailable-browser'),inspection=PageInspection(Path('/protected/checks.py'),'0'*64,'H06'))
        executor=Executor.create(self.source,self.root/'protected-tool',browser=browser)
        with self.assertRaisesRegex(ToolRejected,'protected'):ToolRegistry(executor,Grant((),False,capture_paths=('a.py',)))
    def test_tool_outputs_publish_as_durable_roots_for_the_same_frame_kernel(self):
        from branchwrite.records import RuntimeLog,decode
        result=self.read()
        with RuntimeLog(self.root/'run-records') as log:
            value,refs=result.publish(log)
            self.assertEqual(log.read_artifact(refs[0]),b'answer = 1\n')
            self.assertEqual(value['stdout'],(refs[0].sha256,refs[0].size_bytes))
            self.assertEqual(value['observation'],result.observation.wire)
            self.assertFalse(value['requested_finish'])

    def test_actual_capture_publishes_pixels_and_isolation_without_protected_verdict(self):
        from branchwrite.browser_capture import BrowserConfig
        (self.source/'index.html').write_bytes(b'<!doctype html><title>Owned page</title><h1>Actual capture</h1>')
        browser=BrowserConfig(Path(os.environ['BW_BROWSER_EXECUTABLE']))
        executor=Executor.create(self.source,self.root/'browser-world',browser=browser)
        registry=ToolRegistry(executor,Grant((),False,read_paths=('index.html',),capture_paths=('index.html',)))
        read=registry.execute(registry.freeze(self.proposal('read_file',path='index.html')),'read-html')
        plan=registry.freeze(self.proposal('capture_page',path='index.html'),observations=(read.observation,))
        result=registry.execute(plan,'capture-html')
        self.assertEqual(result.operation_id,'capture-html');self.assertEqual(result.plan_sha256,plan.sha256)
        self.assertTrue(result.image.read_bytes().startswith(b'\x89PNG\r\n\x1a\n'))
        self.assertTrue(result.metadata['isolation']['worker_exited'])
        self.assertEqual(result.metadata['served_sha256'],read.observation.sha256)
        self.assertNotIn('inspection',result.metadata)
    def test_inventory_handles_more_than_the_value_codec_container_limit(self):
        for i in range(4100):(self.executor.workspace/('file-'+str(i))).write_bytes(b'')
        registry=ToolRegistry(self.executor,Grant((),True))
        plan=registry.freeze(self.proposal('run_tests',suite='unit'))
        self.assertEqual(len(plan.sha256),64)
    def test_schema_compiles_in_existing_cow_json_grammar_and_rejects_illegal_tool(self):
        from serve.cow_grammar import GrammarRegistry
        from test_grammar_first import TinyByteTokenizer
        from context_time_travel.store import IntegrityError
        tokenizer=TinyByteTokenizer();config=self.root/'grammar.json'
        config.write_text(json.dumps(dict(schema=1,states=dict(BW_ACTION=dict(format='json_schema',source=self.registry.model_schema())))))
        grammar=GrammarRegistry.load(config,tokenizer,[tokenizer.EOS])
        def consume(text):
            state=grammar.start('BW_ACTION','cpu-schema-contract',[],len(tokenizer.tokens));session=grammar.restore(state,[])
            for token in tokenizer.encode(text,parse_special=False):state=session.consume(state,token,tokenizer.token_bytes(token),False)
            return session
        # The existing COW compiler emits object properties in canonical order.
        # Host JSON parsing accepts either order; do not mistake an arbitrary
        # forced byte order for a legal constrained-generation path.
        def emitted(tool,**arguments):return json.dumps(dict(tool=tool,arguments=arguments),sort_keys=True)
        self.assertTrue(consume(emitted('read_file',path='a.py')).is_complete())
        self.assertTrue(consume(emitted('finish',answer='done')).is_complete())
        with self.assertRaises(IntegrityError):consume(emitted('shell',path='a.py'))
        self.assertEqual(self.registry.parse(emitted('read_file',path='a.py')),
                         self.registry.parse(self.proposal('read_file',path='a.py')))
        with self.assertRaises(IntegrityError):consume(self.proposal('read_file',path='a.py'))
