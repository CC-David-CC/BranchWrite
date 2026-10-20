"""Executed combined CPU/PTY/HTTP regression suite; no GPU model claim."""
import hashlib,json,os,platform,subprocess,sys,time,unittest
from pathlib import Path
repo=Path('/home/dflanag3/src/branchwrite-pdf-regression-20261020');cow=Path('/home/dflanag3/src/context-cow-consumed-pause-20261020')
roots=[repo,repo/'tests',cow/'experimental/branching_context/tests/implementation',cow/'experimental/branching_context/src',cow/'experimental/branching_context/scripts',cow/'tools',cow,cow/'experimental/branching_context/tests',Path('/home/dflanag3/spatial-artifacts/grammar-first-20261016-v1/deps'),Path('/home/dflanag3/spatial-artifacts/branchwrite-interactive-20261020/venv/lib/python3.12/site-packages')]
sys.path[:0]=list(map(str,roots));os.environ['PYTHONPATH']=':'.join(map(str,roots));os.chdir(repo);os.environ['COW_CLI_SCRIPT']=str(cow/'tools/cow_cli.py')
old=json.loads((repo/'validation/interactive-loop-20261020/model-pause/combined/result.json').read_text())
modules=sorted({r['id'].rsplit('.',2)[0] for r in old['tests']}|{'tests.test_interactive_preview','tests.test_remote_execution','tests.test_remote_ownership','tests.test_remote_tools','tests.test_remote_config','tests.test_remote_guest','tests.test_remote_upload','tests.test_tool_verification_feedback','tests.test_progress','tests.test_progress_http','tests.test_tool_progress_details','tests.test_pdf_cli','tests.test_pdf_completion','tests.test_pdf_execution','tests.test_pdf_tools','tests.test_python_runtime','tests.test_interactive_domains','tests.test_document_preview'})
rows=[]
class Result(unittest.TextTestResult):
 def addSuccess(self,t):super().addSuccess(t);rows.append(dict(id=t.id(),status='PASS'))
 def addFailure(self,t,e):super().addFailure(t,e);rows.append(dict(id=t.id(),status='FAIL'))
 def addError(self,t,e):super().addError(t,e);rows.append(dict(id=t.id(),status='ERROR'))
 def addSkip(self,t,e):super().addSkip(t,e);rows.append(dict(id=t.id(),status='SKIP',reason=e))
def fingerprints():return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((repo/'branchwrite').glob('*.py'))}
before=fingerprints();started=time.monotonic();suite=unittest.defaultTestLoader.loadTestsFromNames(modules)
with (Path(__file__).parent/'combined.txt').open('w') as stream:result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=Result).run(suite)
after=fingerprints();report=dict(status='PASS' if result.wasSuccessful() and not result.skipped and before==after else 'FAIL',tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped),elapsed_seconds=time.monotonic()-started,scope='CPU, installed process boundaries/PTY and COW HTTP fixtures; no real model inference',source_unchanged_during_tests=before==after,source_sha256=before,python=sys.version,tests=rows)
(Path(__file__).parent/'combined.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ('tests','source_sha256')}));sys.exit(0 if report['status']=='PASS' else 1)
