"""Actual process death and new-process CLI resume; no model/GPU claim."""
import json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from branchwrite.records import RuntimeLog
from branchwrite.kernel import FrameKernel
class ToolSettlementCLITests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.source=self.root/'source';self.source.mkdir();(self.source/'tests').mkdir();(self.source/'tests/__init__.py').write_text('')
  (self.source/'tests/test_once.py').write_text('import unittest\nfrom pathlib import Path\nclass Once(unittest.TestCase):\n def test_bytes(self):self.assertEqual(Path("new.txt").read_text(),"written once")\n')
  bindings={name:dict(type='ToolProposal',value=json.dumps(dict(tool=tool,arguments=args))) for name,tool,args in [('creation','create_file',dict(path='new.txt',content='written once')),('testing','run_tests',dict(suite='unit')),('done','finish',dict(answer='done'))]}
  cfg=dict(schema=1,source=str(self.source),run_id='settlement-cli',grant=dict(edit_paths=[],create_paths=['new.txt'],read_paths=[],allow_tests=True),bindings=bindings,profiles={})
  self.program=self.root/'job.bw';self.program.write_text('FLOW job\nPLAN c from=creation against=world -> plan\nACT create plan=plan\nPLAN t from=testing against=world -> plan\nACT tests plan=plan\nPLAN f from=done against=world -> plan\nACT finish plan=plan -> outcome\nVERIFY v input=outcome contract=unit-tests-and-finish -> verified\nEND\n')
  self.config=self.root/'host.json';self.config.write_text(json.dumps(cfg));self.state=self.root/'state'
 def command(self,env=None):
  return subprocess.run([sys.executable,'-B','-m','branchwrite','run',str(self.program),'--config',str(self.config),'--state',str(self.state)],env=env,capture_output=True,text=True,timeout=30)
 def crash(self,method,code):
  guard=self.root/'guard';guard.mkdir()
  hook='import os\nfrom branchwrite.kernel import FrameKernel\ndef stop(*a,**kw):os._exit('+str(code)+')\nFrameKernel.'+method+'=stop\n'
  compile(hook,str(guard/'sitecustomize.py'),'exec');(guard/'sitecustomize.py').write_text(hook)
  env=dict(os.environ,PYTHONPATH=str(guard)+os.pathsep+os.environ.get('PYTHONPATH',''),PYTHONDONTWRITEBYTECODE='1')
  r=self.command(env);self.assertEqual(r.returncode,code,r.stderr)
 def frames(self):
  with RuntimeLog(self.state/'ledger',read_only=True) as l:return FrameKernel(l).frames()
 def test_death_after_durable_return_resumes_and_verifies_without_second_create(self):
  self.crash('settle',93)
  pending=[f for f in self.frames() if f['contract']==('ToolOutcome','record')];self.assertEqual(len(pending),1);self.assertEqual(pending[0]['state'],'Settling')
  target=self.state/'world/workspace/new.txt';before=target.stat();self.assertEqual(target.read_text(),'written once')
  resumed=self.command();self.assertEqual(resumed.returncode,0,resumed.stderr);self.assertTrue(json.loads(resumed.stdout)['verified'])
  after=target.stat();self.assertEqual((before.st_ino,before.st_mtime_ns),(after.st_ino,after.st_mtime_ns));self.assertFalse((self.source/'new.txt').exists())
  tools=[f for f in self.frames() if f['contract']==('ToolOutcome','record')];self.assertEqual(len(tools),3);self.assertTrue(all(f['state']=='Closed' for f in tools))
  self.assertEqual(len({f['dispatch'][0] for f in tools}),3)
  ledger=(self.state/'ledger/events.bwl').read_bytes();again=self.command()
  self.assertEqual(again.returncode,0,again.stderr);self.assertEqual(again.stdout,resumed.stdout);self.assertEqual((self.state/'ledger/events.bwl').read_bytes(),ledger)
 def test_death_before_durable_return_stays_unknown_without_repeating_effect(self):
  self.crash('record_result',94)
  pending=[f for f in self.frames() if f['contract']==('ToolOutcome','record')];self.assertEqual(pending[0]['state'],'Waiting')
  target=self.state/'world/workspace/new.txt';before=target.stat();ledger=(self.state/'ledger/events.bwl').read_bytes()
  resumed=self.command();self.assertEqual(resumed.returncode,4,resumed.stderr);self.assertIn('unresolved original operation',resumed.stderr);self.assertIn('branchwrite status',resumed.stderr);self.assertIn('durable retirement proof',resumed.stderr);self.assertNotIn('branchwrite reconcile',resumed.stderr)
  after=target.stat();self.assertEqual((before.st_ino,before.st_mtime_ns),(after.st_ino,after.st_mtime_ns));self.assertEqual(target.read_text(),'written once');self.assertEqual((self.state/'ledger/events.bwl').read_bytes(),ledger)
if __name__=='__main__':unittest.main()
