"""Configuration is portable data; actual host command admission stays strict."""
import json,tempfile,unittest,shutil
from pathlib import Path
from unittest.mock import patch
from branchwrite.coding_cli import build_launch
from branchwrite.execution import Executor,Grant,ToolRejected
from branchwrite.terminal import ShellConfig
class ShellConfigurationTests(unittest.TestCase):
 def test_build_launch_does_not_admit_a_host_executable(self):
  with tempfile.TemporaryDirectory() as t:
   with patch('branchwrite.terminal.NamedCommand',side_effect=AssertionError('host admission during parsing')):
    value=build_launch(t,'Repair',dict(endpoint_url='http://127.0.0.1:1',endpoint_pin='owned',model_contract_id='m',execution_profile_id='p',eos_tokens=[256]),branch='new',edit_paths=['app.py'],test_commands=['python3 -m unittest'])
   self.assertEqual(value['config']['shell']['timeout'],120)
 def test_bad_parameters_still_rejected_before_execution(self):
  with tempfile.TemporaryDirectory() as t:
   for timeout in [True,0,-1,float('inf'),121,'10']:
    with self.subTest(timeout=timeout),self.assertRaises(ValueError):
     build_launch(t,'Repair',dict(endpoint_url='http://127.0.0.1:1',endpoint_pin='owned',model_contract_id='m',execution_profile_id='p',eos_tokens=[256]),branch='new',edit_paths=['app.py'],test_commands=['python3 -m unittest'],shell_timeout=timeout)
 def test_real_namespace_can_parse_but_cannot_admit_unmapped_host_ownership(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);source=root/'source';source.mkdir()
   package=Path(__file__).resolve().parents[1]/'branchwrite'
   shutil.copytree(package,source/'branchwrite',ignore=shutil.ignore_patterns('__pycache__'))
   script="""from pathlib import Path
from branchwrite.coding_cli import build_launch
from branchwrite.terminal import ShellConfig
from branchwrite.execution import ToolRejected
p=Path('/tmp/project');p.mkdir()
v=build_launch(p,'Repair',dict(endpoint_url='http://127.0.0.1:1',endpoint_pin='owned',model_contract_id='m',execution_profile_id='p',eos_tokens=[256]),branch='new',edit_paths=['app.py'],test_commands=['python3 -m unittest'])
assert v['config']['shell']['timeout']==120
assert Path('/usr/bin/bash').stat().st_uid!=0
try:ShellConfig()
except ToolRejected:pass
else:raise AssertionError('unmapped ownership admitted for actual execution')
print('CONFIG_OK_EXECUTION_REJECTED')
"""
   (source/'probe.py').write_text(script)
   reads=tuple(str(f.relative_to(source)) for f in source.rglob('*') if f.is_file())
   executor=Executor.create(source,root/'world',shell=ShellConfig(timeout=15))
   result=executor.run_shell('config-probe',Grant((),False,read_paths=reads,allow_shell=True),'python3 -B probe.py')
   self.assertEqual(result.exit_code,0,result.stderr.read_bytes().decode())
   self.assertIn(b'CONFIG_OK_EXECUTION_REJECTED',result.stdout.read_bytes())
