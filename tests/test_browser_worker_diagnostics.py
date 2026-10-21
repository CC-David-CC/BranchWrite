"""Actual failed worker processes must expose useful bounded diagnostics."""
import sys, unittest
from types import SimpleNamespace
from unittest.mock import patch
from branchwrite.browser_isolation import render_isolated

class BrowserWorkerDiagnosticTests(unittest.TestCase):
 def failure(self, stderr):
  script="import sys;sys.stderr.write("+repr(stderr)+");sys.exit(1)"
  with patch('branchwrite.browser_isolation.isolation_command',return_value=[sys.executable,'-I','-c',script]):
   with self.assertRaises(ValueError) as found:
    render_isolated(b'<p>test</p>',SimpleNamespace(actions=(),timeout=5))
  return str(found.exception)
 def test_blank_trailing_lines_do_not_hide_rejection(self):
  self.assertIn('Permission denied',self.failure('Permission denied\n\n'))
 def test_empty_stderr_reports_actual_exit(self):
  self.assertIn('worker exit 1',self.failure(' \n\n'))
 def test_sandbox_failure_survives_playwright_cleanup_noise(self):
  error=self.failure('FATAL: No usable sandbox! unsafe workaround omitted\n - temporary directories cleanup\n\n')
  self.assertIn('Chromium sandbox unavailable',error)
  self.assertNotIn('unsafe workaround',error)
 def test_suid_helper_rejection_survives_playwright_cleanup_noise(self):
  error=self.failure('[pid=16][err] FATAL:setuid_sandbox_host.cc:172 The SUID sandbox helper binary was found, but is not configured correctly.\n - [pid=16] <gracefully close end>\n')
  self.assertIn('Chromium sandbox helper unavailable',error)
  self.assertNotIn('gracefully close',error)
  self.assertLessEqual(len(error),512)
 def test_long_error_keeps_start_and_is_bounded(self):
  error=self.failure('Permission denied: '+ 'x'*5000+'\n')
  self.assertIn('Permission denied:',error)
  self.assertLessEqual(len(error),512)
