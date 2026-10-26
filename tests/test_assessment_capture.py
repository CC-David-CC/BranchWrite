"""Standalone assessment captures replay actual BW/COW/OS evidence without dispatch."""
import unittest
from unittest.mock import patch

from tests import test_lesson_capture as fixture_module
from branchwrite.lesson_capture import capture_assessment,read_capture,CaptureRefused


class AssessmentCaptureTests(unittest.TestCase):
    def test_actual_failed_and_finished_attempts_are_archived_without_invented_links(self):
        fixture=fixture_module.LessonCaptureTests(methodName='runTest');self.addCleanup(fixture.doCleanups);fixture.setUp()
        failed,failed_result=fixture.run_case('assessment-failed')
        fixed,fixed_result=fixture.run_case('assessment-fixed',True)
        self.assertFalse(failed_result['verified']);self.assertTrue(fixed_result['verified'])
        from branchwrite.lesson_cli import main
        with patch('branchwrite.lesson_cli._client',side_effect=AssertionError('no transport')):
            self.assertEqual(main(['capture-assessment',str(failed),'--output',str(fixture.root/'failed-archive')],output=lambda _:None),0)
        first=read_capture(fixture.root/'failed-archive')
        second=capture_assessment(fixed,fixture.root/'fixed-archive')
        for archive,verified in [(first,None),(second,True)]:
            self.assertEqual(archive.manifest['kind'],'assessment')
            self.assertIsNone(archive.failure_capture_id)
            self.assertIs(archive.manifest['evidence']['recorded_workflow_verified'],verified)
            self.assertFalse(archive.training_approved)
        failed.rename(fixture.root/'retired-failed');fixed.rename(fixture.root/'retired-fixed')
        fixture.project.rename(fixture.root/'retired-project')
        with patch('subprocess.Popen',side_effect=AssertionError('no process dispatch')):
            self.assertEqual(read_capture(second.directory).file_bytes('value.txt'),b'right\n')
        # Even a rewritten self-hash cannot make an assessment a correction.
        from branchwrite.lesson_capture import _canonical,_sha
        value=second.manifest;value['kind']='correction';value['capture_id']=_sha(_canonical({k:v for k,v in value.items()if k!='capture_id'}))
        # The production bounded reader uses file descriptors, so inject at
        # that reader rather than editing the original archival bytes.
        from branchwrite import lesson_capture
        read=lesson_capture._read
        with patch.object(lesson_capture,'_read',lambda p,*a,**k:_canonical(value) if p==second.directory/'capture.json' else read(p,*a,**k)):
            with self.assertRaises(CaptureRefused):read_capture(second.directory)


    def test_actual_created_file_and_explicit_mode_change_are_supported(self):
        fixture=fixture_module.LessonCaptureTests(methodName='runTest')
        self.addCleanup(fixture.doCleanups);fixture.setUp()
        from branchwrite.coding_cli import build_launch,save_launch,run_saved
        fixture.actions[:]=[
            dict(tool='read_file',arguments=dict(path='value.txt')),
            dict(tool='replace',arguments=dict(path='value.txt',before='wrong',after='right')),
            dict(tool='create_text_file',arguments=dict(path='helper.py',line_ending='LF',final_newline=True,lines=['# owned helper'])),
            dict(tool='set_mode',arguments=dict(path='helper.py',mode='0644')),
            dict(tool='run_check',arguments=dict(name='content',command='test "$(cat value.txt)" = right')),
            dict(tool='finish',arguments=dict(answer='Scripted control; no model quality claim'))]
        state=fixture.root/'created-mode'
        launch=build_launch(fixture.project,'Make value.txt contain right followed by newline.',fixture.connection,
            branch='created-mode',project_files=True,thinking_mode='off',instruction_style='compact-finish-request',shell_timeout=2)
        launch['config']['grant'].update(read_paths=['helper.py'],mode_paths=['helper.py'],mode_mask=0o777)
        save_launch(state,launch);_,result=run_saved(state,max_steps=1024)
        self.assertTrue(result['verified'])
        captured=capture_assessment(state,fixture.root/'created-mode-capture')
        self.assertEqual(captured.file_bytes('helper.py'),b'# owned helper'+bytes([10]))
        row=next(r for r in captured.manifest['files']if r['path']=='helper.py')
        self.assertEqual(row['mode'],0o644)
        self.assertEqual(read_capture(captured.directory).capture_id,captured.capture_id)


if __name__=='__main__':unittest.main()
