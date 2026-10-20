"""Real sandboxed H07 checks; protected assertions and fixtures unchanged."""
import hashlib,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from branchwrite.browser_capture import BrowserConfig,PageInspection,render_snapshot
class GreetingInspectionTests(unittest.TestCase):
 def setUp(self):
  self.pack=Path(os.environ['BW_BASIC_LOOP_PACK']);self.check=self.pack/'protected/checks.py';self.check_bytes=self.check.read_bytes()
  self.starter=(self.pack/'fixtures/starter/H07/index.html').read_bytes()
  controls=b'<div><input id="name"><button id="greet">Greet</button><output id="greeting"></output></div><script>document.getElementById("greet").onclick=()=>{document.getElementById("greeting").textContent="Hello, "+document.getElementById("name").value+"!";};</script>'
  self.good=self.starter.replace(b'</main>',controls+b'</main>')
  self.browser=Path(os.environ['BW_BROWSER_EXECUTABLE'])
 def config(self):return BrowserConfig(self.browser,inspection=PageInspection(self.check,hashlib.sha256(self.check_bytes).hexdigest(),'H07'))
 def test_real_checker_preserves_counter_and_greets_literal_markup(self):
  r=render_snapshot(self.good,self.config());self.assertEqual(r.inspection['status'],'PASS')
  self.assertEqual(r.inspection['actions'],[['click','increment'],['click','increment'],['fill','name=Ada'],['click','greet'],['fill','name=<b>Ada</b>'],['click','greet']])
  self.assertEqual(r.served_sha256,hashlib.sha256(self.good).hexdigest());self.assertTrue(r.isolation['worker_exited'])
  self.assertEqual(r.isolation['namespace_members_after'],[]);self.assertEqual(self.check.read_bytes(),self.check_bytes)
 def test_unsafe_html_greeting_is_not_accepted(self):
  bad=self.good.replace(b'getElementById("greeting").textContent',b'getElementById("greeting").innerHTML')
  r=render_snapshot(bad,self.config());self.assertEqual(r.inspection['status'],'FAIL')
  self.assertIn(['fill','name=<b>Ada</b>'],r.inspection['actions']);self.assertTrue(r.isolation['worker_exited'])
 def test_greeting_does_not_excuse_broken_existing_counter(self):
  bad=self.good.replace(b'String(++count)',b'String(count)')
  r=render_snapshot(bad,self.config());self.assertEqual(r.inspection['status'],'FAIL')
  self.assertEqual(r.inspection['actions'],[['click','increment']]);self.assertEqual(self.check.read_bytes(),self.check_bytes)
 def test_unknown_inspection_target_remains_rejected(self):
  with self.assertRaises(ValueError):PageInspection(self.check,hashlib.sha256(self.check_bytes).hexdigest(),'H99')
 def cli(self,payload):
  temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);root=Path(temp.name);source=root/'source';source.mkdir();(source/'index.html').write_bytes(payload)
  actions=[dict(kind='fill',target='name',value='<b>Lin</b>'),dict(kind='click',target='greet',value='')]
  proposals=dict(read=dict(tool='read_file',arguments=dict(path='index.html')),interact=dict(tool='interact_page',arguments=dict(path='index.html',actions=actions)),finish=dict(tool='finish',arguments=dict(answer='observed greeting')))
  cfg=dict(schema=1,source=str(source),run_id='h07-policy-cli',grant=dict(edit_paths=[],create_paths=[],read_paths=['index.html'],capture_paths=['index.html'],interact_paths=['index.html'],allow_tests=False),browser=dict(executable=str(self.browser),width=640,height=480,timeout=15),profiles={},verification=dict(schema=1,interactive_captures=[dict(path='index.html',width=640,height=480)],inspection=dict(path=str(self.check),sha256=hashlib.sha256(self.check_bytes).hexdigest(),target='H07')),bindings={k:dict(type='ToolProposal',value=json.dumps(v)) for k,v in proposals.items()})
  path=root/'host.json';path.write_text(json.dumps(cfg));program=root/'job.bw';program.write_text('FLOW page\nPLAN r from=read against=world -> p\nACT r plan=p\nPLAN i from=interact against=world -> p\nACT i plan=p -> outcome\nPLAN f from=finish against=world -> p\nACT f plan=p -> outcome\nVERIFY v input=outcome contract=interactive-page-inspection-and-finish -> verified\nEND\n')
  state=root/'run';cmd=[sys.executable,'-B','-m','branchwrite','run',str(program),'--config',str(path),'--state',str(state)]
  result=subprocess.run(cmd,capture_output=True,text=True,timeout=30)
  return result,cmd,state
 def test_actual_cli_fill_click_protected_check_and_offline_reopen(self):
  first,cmd,state=self.cli(self.good);self.assertEqual(first.returncode,0,first.stderr);r=json.loads(first.stdout);self.assertTrue(r['verified']);self.assertEqual(len(r['artifacts']),1)
  from branchwrite.records import RuntimeLog,Artifact,decode
  from branchwrite.kernel import FrameKernel
  with RuntimeLog(state/'ledger') as log:
   k=FrameKernel(log);root=decode(log.read_artifact(Artifact(*k.frame('program')['result'])))[2];v=root['bindings']['verified'][1]
   self.assertTrue(v['inspections'][0]['same_capture']);self.assertIn('Hello, <b>Lin</b>!',v['captures'][0]['text'])
   self.assertEqual(v['inspections'][0]['checker']['status'],'PASS')
  again=subprocess.run(cmd,capture_output=True,text=True,timeout=30);self.assertEqual(again.returncode,0,again.stderr);self.assertEqual(first.stdout,again.stdout)
 def test_actual_cli_rejects_unsafe_handler_with_image_retained(self):
  bad=self.good.replace(b'getElementById("greeting").textContent',b'getElementById("greeting").innerHTML')
  result,_,_=self.cli(bad);self.assertEqual(result.returncode,1,result.stderr);r=json.loads(result.stdout);self.assertFalse(r['verified']);self.assertEqual(len(r['artifacts']),1)
if __name__=='__main__':unittest.main()
