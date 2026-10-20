import unittest,tempfile,json,subprocess,sys
from pathlib import Path
RUNNER=Path(__file__).with_name('run-comparison-client.py')
class RunnerExitTests(unittest.TestCase):
 def run_case(self,client_exit,audit_exit):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);d=root/'coding-fixture';d.mkdir();access=root/'client-access';access.mkdir();(access/'credentials.json').write_text('{}')
   (d/'workload.json').write_text(json.dumps({'base_snapshot':'a'*64}))
   (root/'comparison-client-driver.py').write_text('raise SystemExit('+str(client_exit)+')')
   (root/'audit-coding-output.py').write_text('raise SystemExit('+str(audit_exit)+')')
   source=RUNNER.read_text().replace("python='/home/dflanag3/spatial-artifacts/branchwrite-dev19-package-20261019-v1/venv/bin/python'",'python='+repr(sys.executable))
   (root/'run-comparison-client.py').write_text(source)
   result=subprocess.run([sys.executable,'-B',str(root/'run-comparison-client.py'),'fixture'],capture_output=True,text=True)
   return result.returncode,(d/'audit.exit').exists()
 def test_client_failure_stops_before_audit(self):self.assertEqual(self.run_case(7,0),(7,False))
 def test_audit_failure_propagates(self):self.assertEqual(self.run_case(0,9),(9,True))
 def test_success_requires_both(self):self.assertEqual(self.run_case(0,0),(0,True))
if __name__=='__main__':unittest.main()
