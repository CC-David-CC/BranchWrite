"""Actual CLI/HTTP bootstrap and resume, reusing unchanged launcher checks."""
import json,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from branchwrite.context_pack import build_pack
from branchwrite.cow_client import OperationJournal
import test_coding_launcher_http as fixture

class CodingPackHTTPTests(unittest.TestCase):
 def test_cli_bootstrap_uses_pack_and_resume_keeps_original_context(self):
  case=fixture.CodingLauncherHttpTests();self.addCleanup(case.doCleanups)
  with tempfile.TemporaryDirectory() as directory:
   refs=Path(directory)/'references';refs.mkdir();record=refs/'example.txt';record.write_text('PINNED ORIGINAL EXAMPLE')
   pack=build_pack(root=refs,examples=['example.txt'],output=Path(directory)/'packs',as_of='2026-10-19T00:00:00Z')
   actual=subprocess.run;seen=[]
   def run(argv,*args,**kwargs):
    if '-m' in argv and 'branchwrite' in argv and 'code' in argv:
     argv=list(argv)+['--context-pack',pack['pack_path'],'--context-pack-id',pack['pack_id']]
     result=actual(argv,*args,**kwargs)
     self.assertEqual(result.returncode,3,result.stderr)
     state=Path(argv[argv.index('--state')+1]);journal=OperationJournal(state/'cow-operations')
     records=[json.loads(p.read_text()) for p in (state/'cow-operations').glob('*.json')]
     roots=[r for r in records if r['path']=='/cow/text/context'];self.assertEqual(len(roots),1)
     body=journal.decode_body(roots[0]).decode();self.assertIn('PINNED ORIGINAL EXAMPLE',body)
     launch=json.loads((state/'coding-launch.json').read_text())['launch']
     self.assertEqual(launch['config']['context_pack']['pack_id'],pack['pack_id'])
     seen.append('code');record.write_text('CHANGED AFTER ROOT ADMISSION')
     return result
    if '-m' in argv and 'branchwrite' in argv and 'resume' in argv:seen.append('resume')
    return actual(argv,*args,**kwargs)
   with patch('subprocess.run',side_effect=run):
    case.test_code_prepares_real_context_and_resume_keeps_pinned_setup()
   self.assertEqual(seen,['code','resume'])

 def test_process_exit_after_root_before_workflow_uses_original_prefix(self):
  import os,hashlib
  from branchwrite.records import RuntimeLog
  from branchwrite.kernel import FrameKernel
  case=fixture.CodingLauncherHttpTests();self.addCleanup(case.doCleanups)
  with tempfile.TemporaryDirectory() as directory:
   base=Path(directory);refs=base/'references';refs.mkdir();record=refs/'example.txt';record.write_text('ORIGINAL BEFORE CRASH')
   pack=build_pack(root=refs,examples=['example.txt'],output=base/'packs',as_of='2026-10-19T00:00:00Z')
   guard=base/'guard';guard.mkdir()
   (guard/'sitecustomize.py').write_text("import os\nimport branchwrite.interpreter as m\ndef stop_before_admission(*a,**kw):\n os._exit(91)\nm.Interpreter.start=stop_before_admission\n")
   actual=subprocess.run;seen=[]
   def run(argv,*args,**kwargs):
    if '-m' in argv and 'branchwrite' in argv and 'code' in argv:
     argv=list(argv)+['--context-pack',pack['pack_path'],'--context-pack-id',pack['pack_id']]
     normal=dict(kwargs['env']);fault=dict(normal,PYTHONPATH=str(guard)+os.pathsep+normal.get('PYTHONPATH',''))
     failed=actual(argv,*args,**dict(kwargs,env=fault))
     self.assertEqual(failed.returncode,91,failed.stderr)
     state=Path(argv[argv.index('--state')+1])
     with RuntimeLog(state/'ledger',read_only=True) as log:self.assertFalse(FrameKernel(log).frames())
     records=[(p,json.loads(p.read_text())) for p in (state/'cow-operations').glob('*.json')]
     roots=[(p,r) for p,r in records if r['path']=='/cow/text/context'];self.assertEqual(len(roots),1)
     path,root=roots[0];self.assertEqual(root['state'],'complete');before=path.read_bytes()
     record.write_text('CHANGED AFTER PROCESS EXIT')
     resumed=actual([argv[0],'-B','-m','branchwrite','resume',str(state),'--max-steps','1'],capture_output=True,text=True,env=normal,timeout=20)
     self.assertEqual(resumed.returncode,3,resumed.stderr)
     self.assertEqual(path.read_bytes(),before)
     self.assertEqual(len([p for p in (state/'cow-operations').glob('*.json') if json.loads(p.read_text())['path']=='/cow/text/context']),1)
     seen.append('recovered-admission')
     return resumed
    return actual(argv,*args,**kwargs)
   with patch('subprocess.run',side_effect=run):
    case.test_code_prepares_real_context_and_resume_keeps_pinned_setup()
   self.assertEqual(seen,['recovered-admission'])

 def test_lost_root_reply_is_explicitly_reconciled_before_admission(self):
  import os,hashlib
  case=fixture.CodingLauncherHttpTests();self.addCleanup(case.doCleanups)
  with tempfile.TemporaryDirectory() as directory:
   base=Path(directory);refs=base/'references';refs.mkdir();record=refs/'example.txt';record.write_text('ORIGINAL LOST REPLY PREFIX')
   pack=build_pack(root=refs,examples=['example.txt'],output=base/'packs',as_of='2026-10-19T00:00:00Z')
   guard=base/'guard';guard.mkdir()
   (guard/'sitecustomize.py').write_text("import os\nfrom branchwrite.cow_client import HTTPTransport\nactual=HTTPTransport.request\ndef lose(self,method,path,body=None,**kw):\n r=actual(self,method,path,body,**kw)\n if method=='POST' and path=='/cow/text/context':\n  events=list(r.events)\n  assert sum(e.get('event')=='complete' for e in events)==1\n  os._exit(92)\n return r\nHTTPTransport.request=lose\n")
   actual=subprocess.run;seen=[]
   def run(argv,*args,**kwargs):
    if '-m' in argv and 'branchwrite' in argv and 'code' in argv:
     argv=list(argv)+['--context-pack',pack['pack_path'],'--context-pack-id',pack['pack_id']]
     normal=dict(kwargs['env']);fault=dict(normal,PYTHONPATH=str(guard)+os.pathsep+normal.get('PYTHONPATH',''))
     failed=actual(argv,*args,**dict(kwargs,env=fault));self.assertEqual(failed.returncode,92,failed.stderr)
     state=Path(argv[argv.index('--state')+1])
     journal=OperationJournal(state/'cow-operations');records=[json.loads(p.read_text()) for p in (state/'cow-operations').glob('*.json')]
     roots=[r for r in records if r['path']=='/cow/text/context'];self.assertEqual(len(roots),1)
     root=roots[0];self.assertEqual(root['state'],'pending');op=root['operation_id']
     before={str(p.relative_to(state/'ledger')):p.read_bytes() for p in (state/'ledger').rglob('*') if p.is_file()}
     denied=actual([argv[0],'-B','-m','branchwrite','reconcile',str(state),'--operation-id','unowned-bootstrap'],capture_output=True,text=True,env=normal,timeout=10)
     self.assertEqual(denied.returncode,2,denied.stderr);self.assertEqual(journal.read(op),root)
     record.write_text('CHANGED WHILE ROOT ACK WAS LOST')
     recovered=actual([argv[0],'-B','-m','branchwrite','reconcile',str(state),'--operation-id',op],capture_output=True,text=True,env=normal,timeout=15)
     self.assertEqual(recovered.returncode,0,recovered.stderr)
     value=json.loads(recovered.stdout);self.assertEqual(value['scope'],'bootstrap');self.assertFalse(value['workflow_advanced'])
     self.assertEqual({str(p.relative_to(state/'ledger')):p.read_bytes() for p in (state/'ledger').rglob('*') if p.is_file()},before)
     self.assertEqual(journal.read(op)['body_b64'],root['body_b64']);self.assertEqual(journal.read(op)['state'],'complete')
     resumed=actual([argv[0],'-B','-m','branchwrite','resume',str(state),'--max-steps','1'],capture_output=True,text=True,env=normal,timeout=15)
     self.assertEqual(resumed.returncode,3,resumed.stderr);seen.append('explicit-original-root-recovered')
     return resumed
    return actual(argv,*args,**kwargs)
   with patch('subprocess.run',side_effect=run):
    case.test_code_prepares_real_context_and_resume_keeps_pinned_setup()
   self.assertEqual(seen,['explicit-original-root-recovered'])
