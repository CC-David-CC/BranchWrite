import os,sys,json,unittest,time
from pathlib import Path
r=Path('/home/dflanag3/src/branchwrite-interactive-loop-20261020');sys.path.insert(0,str(r));os.chdir(r)
from tools.check_client_setup import Results
modules=['tests.test_browser_host_inspection','tests.test_html_inspection','tests.test_greeting_inspection','tests.test_browser_isolation','tests.test_browser_errors']
out=Path(__file__).parent;start=time.monotonic()
with (out/'tests.txt').open('w') as stream:
 result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=Results).run(unittest.defaultTestLoader.loadTestsFromNames(modules))
report=dict(status='PASS' if result.wasSuccessful() and not result.skipped else 'FAIL',tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped),seconds=time.monotonic()-start,scope='Real sandboxed Chromium and host-owned inspection regressions; protected catalog assertions unchanged. No model/GPU.',tests=result.outcomes)
(out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='tests'}))
