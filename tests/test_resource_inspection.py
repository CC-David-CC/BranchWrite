"""Unchanged H08 assertions, actual image bytes and preserved controls."""
import hashlib,io,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from PIL import Image
from branchwrite.browser_capture import BrowserConfig,PageInspection,render_snapshot
from branchwrite.browser_assets import BrowserAsset

class ResourceInspectionTests(unittest.TestCase):
 def setUp(self):
  self.pack=Path(os.environ['BW_BASIC_LOOP_PACK']);self.check=self.pack/'protected/checks.py';self.check_bytes=self.check.read_bytes()
  self.starter=(self.pack/'fixtures/starter/H08/index.html').read_bytes()
  self.png=(self.pack/'fixtures/starter/H08/assets/sample.png').read_bytes()
  self.good=self.starter.replace(b'</main>',b'<img id="asset" src="assets/sample.png" alt="Two-color marker"></main>')
  self.browser=Path(os.environ['BW_BROWSER_EXECUTABLE']);self.asset=BrowserAsset('assets/sample.png',self.png)
 def config(self):
  return BrowserConfig(self.browser,inspection=PageInspection(self.check,hashlib.sha256(self.check_bytes).hexdigest(),'H08'))
 def test_actual_resource_pixels_and_preserved_controls_pass(self):
  result=render_snapshot(self.good,self.config(),assets=(self.asset,))
  self.assertEqual(result.inspection['status'],'PASS')
  self.assertEqual(result.inspection['actions'],[['click','increment'],['click','increment'],['fill','name=Ada'],['click','greet'],['fill','name=<b>Ada</b>'],['click','greet']])
  self.assertEqual(result.asset_manifest,(self.asset.manifest,))
  self.assertEqual(result.served_assets[0]['sha256'],hashlib.sha256(self.png).hexdigest())
  self.assertEqual(self.check.read_bytes(),self.check_bytes)
  self.assertTrue(result.isolation['worker_exited'])
 def test_loaded_wrong_pixels_fail_original_checker(self):
  b=io.BytesIO();Image.new('RGB',(48,32),'black').save(b,format='PNG')
  result=render_snapshot(self.good,self.config(),assets=(BrowserAsset('assets/sample.png',b.getvalue()),))
  self.assertEqual(result.inspection['status'],'FAIL')
  self.assertIn('marker',result.inspection['error'])
 def test_missing_resource_is_not_a_pass(self):
  with self.assertRaisesRegex(ValueError,'unsupported resource'):render_snapshot(self.good,self.config())
 def test_added_image_does_not_excuse_broken_counter(self):
  bad=self.good.replace(b'String(++count)',b'String(count)')
  result=render_snapshot(bad,self.config(),assets=(self.asset,))
  self.assertEqual(result.inspection['status'],'FAIL')
  self.assertEqual(result.inspection['actions'],[['click','increment']])
 def test_actual_static_cli_separates_initial_capture_from_checker_actions(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);source=root/'source';(source/'assets').mkdir(parents=True);(source/'index.html').write_bytes(self.good);(source/'assets/sample.png').write_bytes(self.png)
   props={k:dict(type='ToolProposal',value=json.dumps(dict(tool=v,arguments=a))) for k,v,a in [('read','read_file',dict(path='index.html')),('capture','capture_page',dict(path='index.html')),('finish','finish',dict(answer='observed supplied image'))]}
   cfg=dict(schema=1,source=str(source),run_id='h08-resources',grant=dict(edit_paths=[],create_paths=[],read_paths=['index.html','assets/sample.png'],capture_paths=['index.html'],asset_paths=['assets/sample.png'],allow_tests=False),browser=dict(executable=str(self.browser),width=640,height=480,timeout=15),profiles={},bindings=props,verification=dict(schema=1,inspected_captures=[dict(path='index.html',width=640,height=480)],inspection=dict(path=str(self.check),sha256=hashlib.sha256(self.check_bytes).hexdigest(),target='H08')))
   config=root/'host.json';config.write_text(json.dumps(cfg));program=root/'job.bw';program.write_text('FLOW image\nPLAN r from=read against=world -> p\nACT r plan=p\nPLAN c from=capture against=world -> p\nACT c plan=p\nPLAN f from=finish against=world -> p\nACT f plan=p -> outcome\nVERIFY v input=outcome contract=page-inspection-and-finish -> verified\nEND\n')
   state=root/'run';cmd=[sys.executable,'-B','-m','branchwrite','run',str(program),'--config',str(config),'--state',str(state)]
   first=subprocess.run(cmd,capture_output=True,text=True,timeout=30);self.assertEqual(first.returncode,0,first.stderr);self.assertTrue(json.loads(first.stdout)['verified'])
   from branchwrite.records import RuntimeLog,Artifact,decode
   from branchwrite.kernel import FrameKernel
   with RuntimeLog(state/'ledger') as log:
    k=FrameKernel(log);r=decode(log.read_artifact(Artifact(*k.frame('program')['result'])))[2];v=r['bindings']['verified'][1];i=v['inspections'][0]
    self.assertEqual(i['checker']['status'],'PASS');self.assertTrue(i['same_capture'])
    self.assertNotEqual(i['protected_image'][0],i['captured_image_sha256'])
    self.assertEqual(log.read_artifact(Artifact(hashlib.sha256(self.png).hexdigest(),len(self.png))),self.png)
   again=subprocess.run(cmd,capture_output=True,text=True,timeout=30);self.assertEqual(again.returncode,0,again.stderr);self.assertEqual(first.stdout,again.stdout)

if __name__=='__main__':unittest.main()
