"""New-run source refresh through actual subprocess CLI and COW HTTP."""
import json,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from branchwrite.context_pack import build_pack
from branchwrite.cow_client import OperationJournal
import test_coding_launcher_http as fixture

class CodingPackRefreshHTTPTests(unittest.TestCase):
 def test_refreshed_root_uses_new_bytes_and_resume_never_refreshes(self):
  case=fixture.CodingLauncherHttpTests();self.addCleanup(case.doCleanups)
  with tempfile.TemporaryDirectory() as directory:
   d=Path(directory);refs=d/'references';refs.mkdir();record=refs/'fact.txt'
   record.write_text('OLD OBSERVATION DO NOT USE')
   old=build_pack(root=refs,facts=['fact.txt'],output=d/'packs',as_of='2026-10-19T00:00:00Z')
   old_bytes={p.name:p.read_bytes() for p in Path(old['pack_path']).iterdir()}
   record.write_text('CURRENT REFRESHED OBSERVATION')
   actual=subprocess.run;seen=[]
   def run(argv,*args,**kwargs):
    if '-m' in argv and 'branchwrite' in argv and 'code' in argv:
     argv=list(argv)+['--context-pack',old['pack_path'],'--context-pack-id',old['pack_id'],'--refresh-context-pack']
     result=actual(argv,*args,**kwargs);self.assertEqual(result.returncode,3,result.stderr)
     state=Path(argv[argv.index('--state')+1]);journal=OperationJournal(state/'cow-operations')
     roots=[json.loads(p.read_text()) for p in (state/'cow-operations').glob('*.json') if json.loads(p.read_text())['path']=='/cow/text/context']
     self.assertEqual(len(roots),1)
     body=journal.decode_body(roots[0]).decode()
     self.assertIn('CURRENT REFRESHED OBSERVATION',body);self.assertNotIn('OLD OBSERVATION DO NOT USE',body)
     launch=json.loads((state/'coding-launch.json').read_text())['launch']
     pin=launch['config']['context_pack'];self.assertNotEqual(pin['pack_id'],old['pack_id'])
     self.assertEqual({p.name:p.read_bytes() for p in Path(old['pack_path']).iterdir()},old_bytes)
     seen.append('new-root');record.write_text('EXTERNAL EDIT AFTER ADMISSION')
     return result
    if '-m' in argv and 'branchwrite' in argv and 'resume' in argv:seen.append('resume-original')
    return actual(argv,*args,**kwargs)
   with patch('subprocess.run',side_effect=run):
    case.test_code_prepares_real_context_and_resume_keeps_pinned_setup()
   self.assertEqual(seen,['new-root','resume-original'])

if __name__=='__main__':unittest.main()
