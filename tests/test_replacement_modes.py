"""Actual replacement permissions must survive the owner's process umask."""
from pathlib import Path
import hashlib,os,tempfile,unittest
from unittest.mock import patch
from branchwrite.execution import Executor,Grant


@unittest.skipUnless(os.name=='posix','native POSIX modes required')
class ReplacementModeTests(unittest.TestCase):
    def setup_executor(self,root,mode):
        source=root/'source';source.mkdir()
        original=b'answer = 0'+bytes([10]);path=source/'task.py'
        path.write_bytes(original);path.chmod(mode)
        executor=Executor.create(source,root/'run')
        return executor,path,original

    def test_byte_and_whole_file_replacements_preserve_exact_existing_mode(self):
        for method in ('replace','replace_file'):
            for mode in (0o644,0o755,0o444):
                for mask in (0o022,0o077,0o777):
                    with self.subTest(method=method,mode=oct(mode),umask=oct(mask)),tempfile.TemporaryDirectory()as folder:
                        executor,source,original=self.setup_executor(Path(folder),mode)
                        target=executor.workspace/'task.py';self.assertEqual(target.stat().st_mode&0o777,mode)
                        expected=b'answer = 1'+bytes([10]);old=os.umask(mask)
                        try:
                            args=('mode-check',Grant(edit_paths=('task.py',),allow_tests=False),'task.py',hashlib.sha256(original).hexdigest())
                            result=(executor.replace(*args,b'0',b'1')if method=='replace'
                                    else executor.replace_file(*args,expected))
                        finally:os.umask(old)
                        self.assertEqual(result.disposition,'applied')
                        self.assertEqual(target.stat().st_mode&0o777,mode)
                        self.assertEqual(target.read_bytes(),expected)
                        self.assertEqual(source.read_bytes(),original)
                        self.assertEqual(source.stat().st_mode&0o777,mode)

    def test_failed_mode_restoration_never_replaces_original_or_leaks_temporary(self):
        with tempfile.TemporaryDirectory()as folder:
            executor,source,original=self.setup_executor(Path(folder),0o644)
            target=executor.workspace/'task.py'
            with patch('branchwrite.execution.os.fchmod',side_effect=OSError('mode restoration failed')):
                with self.assertRaisesRegex(OSError,'mode restoration failed'):
                    executor.replace('mode-failure',Grant(edit_paths=('task.py',),allow_tests=False),
                        'task.py',hashlib.sha256(original).hexdigest(),b'0',b'1')
            self.assertEqual(target.read_bytes(),original)
            self.assertEqual(target.stat().st_mode&0o777,0o644)
            self.assertEqual(list(executor.workspace.iterdir()),[target])
            self.assertEqual(source.read_bytes(),original)


if __name__=='__main__':unittest.main()
