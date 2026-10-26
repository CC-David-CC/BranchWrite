"""Actual CPU BW/COW/OS evidence; scripted proposals, no native model quality."""
import unittest
from unittest.mock import patch
from tests import test_lesson_capture as fixture_module
from branchwrite.lesson_capture import CaptureRefused,capture_assessment
from branchwrite.coding_terminal_observation import observe_unverified_workflow,archive_unverified_workflow,read_unverified_archive
from branchwrite.coding_cli import build_launch,save_launch,run_saved

class TerminalWorkflowObservationTests(unittest.TestCase):
    def fixture(self):
        f=fixture_module.LessonCaptureTests(methodName='runTest');self.addCleanup(f.doCleanups);f.setUp();return f

    def test_closed_unchecked_changed_attempt_is_archival_failure_not_lesson(self):
        f=self.fixture();f.actions[:]=[
            dict(tool='read_file',arguments=dict(path='value.txt')),
            dict(tool='replace',arguments=dict(path='value.txt',before='wrong',after='right')),
            dict(tool='read_file',arguments=dict(path='value.txt'))]
        state=f.root/'unchecked';launch=build_launch(f.project,'Repair value.txt.',f.connection,branch='unchecked',project_files=True,thinking_mode='off',instruction_style='compact-finish-request',shell_timeout=2)
        save_launch(state,launch);_,result=run_saved(state,max_steps=1024)
        self.assertEqual(result['status'],'complete');self.assertFalse(result['verified'])
        with self.assertRaisesRegex(CaptureRefused,'unchecked changed'):capture_assessment(state,f.root/'unsupported-capture')
        observation=observe_unverified_workflow(state)
        self.assertFalse(observation['training_eligible']);self.assertFalse(observation['workflow_finished'])
        self.assertEqual(observation['artifact_correctness'],'unassessed')
        self.assertIn('replace',[row['tool']for row in observation['tool_outcomes']])
        from branchwrite.lesson_cli import main
        with patch('branchwrite.lesson_cli._client',side_effect=AssertionError('local CLI must not connect')):
            self.assertEqual(main(['capture-terminal-failure',str(state),'--output',str(f.root/'terminal-archive')],output=lambda _:None),0)
        archive=read_unverified_archive(f.root/'terminal-archive')
        state.rename(f.root/'original-state-retired');f.project.rename(f.root/'original-project-retired')
        with patch('subprocess.Popen',side_effect=AssertionError('read-only archive')):
            self.assertEqual(read_unverified_archive(f.root/'terminal-archive'),archive)
            self.assertEqual(main(['terminal-show',str(f.root/'terminal-archive')],output=lambda _:None),0)
        path=f.root/'terminal-archive/state/cow-operations';record=next(path.iterdir());record.chmod(0o600);record.write_bytes(record.read_bytes()+b' ')
        with self.assertRaisesRegex(CaptureRefused,'evidence changed'):read_unverified_archive(f.root/'terminal-archive')

    def test_open_workflow_and_verified_success_are_not_terminal_false(self):
        f=self.fixture();state,_=f.run_case('open',steps=1,no_check=True)
        with self.assertRaisesRegex(CaptureRefused,'not terminal'):observe_unverified_workflow(state)
        # Fresh fixture resets the scripted native cursor.
        f=self.fixture();state,result=f.run_case('success',True)
        self.assertTrue(result['verified'])
        with self.assertRaisesRegex(CaptureRefused,'false workflow'):observe_unverified_workflow(state)

if __name__=='__main__':unittest.main()
