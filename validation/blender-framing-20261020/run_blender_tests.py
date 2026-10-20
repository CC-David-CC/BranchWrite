import unittest,json,time,sys
modules=json.loads(sys.argv[1]); suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(n) for n in modules)
class Recorded(unittest.TextTestResult):
 def startTest(self,t):self.started=time.monotonic();super().startTest(t)
 def addSuccess(self,t):rows.append(dict(id=t.id(),status='PASS',seconds=time.monotonic()-self.started));super().addSuccess(t)
 def addFailure(self,t,e):rows.append(dict(id=t.id(),status='FAIL'));super().addFailure(t,e)
 def addError(self,t,e):rows.append(dict(id=t.id(),status='ERROR'));super().addError(t,e)
 def addSkip(self,t,why):rows.append(dict(id=t.id(),status='SKIP',reason=why));super().addSkip(t,why)
rows=[];start=time.monotonic();result=unittest.TextTestRunner(verbosity=2,resultclass=Recorded).run(suite)
json.dump(dict(status='PASS' if result.wasSuccessful() and not result.skipped else 'FAIL',tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped),seconds=time.monotonic()-start,results=rows),open(sys.argv[2],'w'),indent=2)
sys.exit(not result.wasSuccessful())
