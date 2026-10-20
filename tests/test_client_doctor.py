import io,json,unittest
from contextlib import redirect_stdout,redirect_stderr
from unittest.mock import patch
from branchwrite.__main__ import main
class ClientDoctorTests(unittest.TestCase):
 def test_real_sandbox_reports_retirement_and_preserves_literal_bytes(self):
  out=io.StringIO()
  with redirect_stdout(out):code=main(['doctor'])
  self.assertEqual(code,0);value=json.loads(out.getvalue())
  self.assertEqual(value['status'],'PASS');self.assertEqual(value['inference'],'NOT_RUN')
  self.assertTrue(value['checks']['literal_bytes']);self.assertTrue(value['checks']['original_unchanged'])
  self.assertTrue(value['isolation']['worker_exited']);self.assertEqual(value['isolation']['namespace_members_after'],[])
 def test_sandbox_refusal_is_failure_without_unsafe_fallback(self):
  from branchwrite.execution import Executor
  out=io.StringIO()
  with patch.object(Executor,'run_shell',side_effect=ValueError('sandbox unavailable')),redirect_stdout(out):code=main(['doctor'])
  self.assertEqual(code,2);value=json.loads(out.getvalue());self.assertEqual(value['status'],'FAIL');self.assertIn('sandbox unavailable',value['error'])
