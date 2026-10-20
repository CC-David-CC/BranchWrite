import unittest,json,time,sys
from pathlib import Path
out=Path(__file__).parent;rows=[]
class Result(unittest.TextTestResult):
 def addSuccess(self,t):super().addSuccess(t);rows.append(dict(id=t.id(),status='PASS'))
 def addFailure(self,t,e):super().addFailure(t,e);rows.append(dict(id=t.id(),status='FAIL'))
 def addError(self,t,e):super().addError(t,e);rows.append(dict(id=t.id(),status='ERROR'))
 def addSkip(self,t,e):super().addSkip(t,e);rows.append(dict(id=t.id(),status='SKIP',reason=e))
modules=['serve.test_cow_http_pause','serve.test_cow_runtime_source_identity','test_consumed_pause_coordinator','test_consumed_pause','test_schedule_binding_cache']
started=time.monotonic()
with (out/'focused.txt').open('w') as log:r=unittest.TextTestRunner(stream=log,verbosity=2,resultclass=Result).run(unittest.defaultTestLoader.loadTestsFromNames(modules))
report=dict(status='PASS' if r.wasSuccessful() and not r.skipped else 'FAIL',tests=r.testsRun,failures=len(r.failures),errors=len(r.errors),skips=len(r.skipped),seconds=time.monotonic()-started,results=rows,scope='CPU/source identity/coordinator/HTTP pause fixtures; no new model numerical claim')
(out/'focused.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='results'}));sys.exit(0 if report['status']=='PASS' else 1)
