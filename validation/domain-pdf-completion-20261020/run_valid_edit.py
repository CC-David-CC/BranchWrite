from pathlib import Path
import hashlib,json,os,sys,time,unittest
repo=Path('/home/dflanag3/src/branchwrite-documents-20261020');sys.path[:0]=[str(repo),str(repo/'tests')];os.chdir(repo);out=Path(__file__).parent
rows=[]
class Result(unittest.TextTestResult):
 def addSuccess(self,t):super().addSuccess(t);rows.append(dict(id=t.id(),status='PASS'))
 def addFailure(self,t,e):super().addFailure(t,e);rows.append(dict(id=t.id(),status='FAIL'))
 def addError(self,t,e):super().addError(t,e);rows.append(dict(id=t.id(),status='ERROR'))
 def addSkip(self,t,e):super().addSkip(t,e);rows.append(dict(id=t.id(),status='SKIP',reason=e))
def fingerprint():return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (repo/'branchwrite').glob('*.py')}
before=fingerprint();began=time.monotonic();suite=unittest.defaultTestLoader.loadTestsFromNames(['test_domain_pdf_completion','test_pdf_completion','test_pdf_execution','test_pdf_tools','test_cad_tools','test_blender_tools'])
with (out/'valid-edit-green.txt').open('w') as log:result=unittest.TextTestRunner(stream=log,verbosity=2,resultclass=Result).run(suite)
report=dict(status='PASS' if result.wasSuccessful() and not result.skipped and fingerprint()==before else 'FAIL',tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped),source_unchanged=fingerprint()==before,source_sha256=before,tests=rows,elapsed_seconds=time.monotonic()-began,scope='actual local CAD STEP geometry, Blender/MCP/CPU rendering and isolated PDF build/reopen/page evidence; not model inference')
(out/'valid-edit-green.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['source_sha256','tests']}));sys.exit(0 if report['status']=='PASS' else 1)
