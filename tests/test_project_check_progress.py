"""Actual check readiness is visible without certifying a finished task."""
import json, tempfile, unittest
from pathlib import Path
from branchwrite.execution import Executor, Grant
from branchwrite.terminal import ShellConfig
from branchwrite.tool_registry import ToolRegistry
from branchwrite.records import RuntimeLog
from branchwrite.kernel import FrameKernel
from branchwrite.interpreter import Interpreter, Value


class ProjectCheckProgressTests(unittest.TestCase):
    def execute(self, actions, *, progress_feedback=True):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / 'source'
            source.mkdir()
            (source / 'marker').write_text('good')
            executor = Executor.create(source, root / 'world', shell=ShellConfig(timeout=2), project_input=True)
            registry = ToolRegistry(executor, Grant((), False, allow_shell=True, project_files=True))
            program = ['FLOW progress']
            bindings = {}
            for index, action in enumerate(actions):
                label = 'step' + str(index)
                bindings[label] = Value('ToolProposal', json.dumps(action))
                program.extend([
                    'PLAN p-' + label + ' from=' + label + ' against=world -> plan',
                    'ACT a-' + label + ' plan=plan -> outcome',
                    'VERIFY v-' + label + ' contract=project-checks-and-finish input=outcome -> verified',
                    'TRANSFORM f-' + label + ' contract=tool-feedback input=outcome evidence=verified -> view-' + label,
                ])
            program.append('END')
            with RuntimeLog(root / 'ledger') as log:
                spec=dict(schema=1, selected_checks=True)
                if progress_feedback is not None: spec['progress_feedback']=progress_feedback
                runtime = Interpreter(FrameKernel(log), registry, verification=spec)
                runtime.start('\n'.join(program) + '\n', bindings)
                result = runtime.run()
                self.assertEqual(result.status, 'complete')
                self.assertEqual((source / 'marker').read_text(), 'good')
                views = [json.loads(result.value['bindings']['view-step' + str(i)][1]) for i in range(len(actions))]
                return result.value, views

    def check(self, command='test "$(cat marker)" = good'):
        return dict(tool='run_check', arguments=dict(name='content', command=command))

    def test_default_policy_does_not_opt_into_experimental_feedback(self):
        result, views = self.execute([self.check()], progress_feedback=None)
        self.assertFalse(result['verified'])
        self.assertNotIn('check_status', views[0]['verification'])
        self.assertEqual(views[0]['verification']['checks'], [])

    def test_passing_check_is_progress_until_explicit_finish(self):
        unfinished, views = self.execute([self.check()])
        progress = views[0]['verification']
        self.assertFalse(unfinished['verified'])
        self.assertEqual(progress['status'], 'fail')
        self.assertEqual(progress['check_status'], 'pass')
        self.assertTrue(progress['finish_required'])
        self.assertEqual(progress['checks'], [dict(name='content', status='pass', exit_code=0, disposition='exited')])
        self.assertNotIn('command', progress['checks'][0])
        finished, views = self.execute([self.check(), dict(tool='finish', arguments=dict(answer='checked marker contents'))])
        self.assertTrue(finished['verified'])
        self.assertEqual(views[-1]['verification']['status'], 'pass')

    def test_successful_exploration_does_not_become_a_named_check(self):
        result, views = self.execute([dict(tool='run_shell', arguments=dict(command='test -f marker'))])
        self.assertFalse(result['verified'])
        self.assertEqual(views[0]['verification']['check_status'], 'fail')
        self.assertEqual(views[0]['verification']['checks'], [])

    def test_failed_and_stale_receipts_are_not_ready_to_finish(self):
        _, views = self.execute([self.check('exit 7')])
        self.assertEqual(views[0]['verification']['check_status'], 'fail')
        _, views = self.execute([
            self.check(),
            dict(tool='read_file', arguments=dict(path='marker')),
            dict(tool='replace', arguments=dict(path='marker', before='good', after='changed')),
        ])
        self.assertEqual(views[0]['verification']['check_status'], 'pass')
        self.assertEqual(views[-1]['verification']['check_status'], 'fail')
        self.assertEqual(views[-1]['verification']['checks'][0]['status'], 'fail')


if __name__ == '__main__':
    unittest.main()
