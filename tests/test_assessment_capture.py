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


if __name__=='__main__':unittest.main()
