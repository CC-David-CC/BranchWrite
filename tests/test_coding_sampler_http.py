"""Actual CLI subprocess/HTTP setup with pinned presets; no GPU generation."""
import json,subprocess,unittest
from pathlib import Path
from unittest.mock import patch
import test_coding_launcher_http as fixture
from branchwrite.coding_defaults import generation_profile

class CodingSamplerHttpTests(unittest.TestCase):
 def test_sampled_admissions_and_resume_keep_the_saved_profile(self):
  real_run=subprocess.run
  for sampler in ['min-p','dry-min-p']:
   with self.subTest(sampler=sampler):
    case=fixture.CodingLauncherHttpTests();self.addCleanup(case.doCleanups);seen=[]
    def run(argv,*args,**kwargs):
     is_code='branchwrite' in argv and 'code' in argv
     if is_code:argv=[*argv,'--sampler',sampler]
     result=real_run(argv,*args,**kwargs)
     if is_code:
      state=Path(argv[argv.index('--state')+1]);saved=json.loads((state/'coding-launch.json').read_text())['launch']
      self.assertEqual(saved['config']['profiles']['control'],generation_profile(sampler));seen.append(sampler)
     return result
    with patch('subprocess.run',side_effect=run):case.test_code_prepares_real_context_and_resume_keeps_pinned_setup()
    self.assertEqual(seen,[sampler])
