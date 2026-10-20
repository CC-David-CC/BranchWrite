"""Content-addressed image feedback on the existing Kernel and real HTTP.

The HTTP peer supplies synthetic model receipts. Real Chromium supplies the
capture in CLI tests. These are client/recovery checks, not GPU qualification.
"""
import hashlib,io,json,os,subprocess,sys,tempfile,threading,unittest
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit,parse_qs
from unittest.mock import patch
from branchwrite.cow_client import CowClient,OperationJournal,BranchHead,OperationIndeterminate,ReceiptError,RequestRejected
from branchwrite.model_dispatch import ModelAdapter
from branchwrite.kernel import FrameKernel,ResultContract
from branchwrite.records import RuntimeLog,Artifact,decode,CorruptLog

class ImageFeedbackTests(unittest.TestCase):
 def setUp(self):
  from PIL import Image
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
  stream=io.BytesIO();Image.new('RGB',(7,3),'green').save(stream,format='PNG');self.raw=stream.getvalue()
  self.namespace='a'*32;self.revision=0;self.tip='1'*64;self.uploads=[];self.generations=[];self.bad_ack=False;self.no_namespace=False;self.gets=0;owner=self
  class Handler(BaseHTTPRequestHandler):
   def log_message(self,*args):pass
   def send(self,value):
    body=(json.dumps(value)+'\n').encode();self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
   def do_GET(self):
    owner.gets+=1;value=dict(name='images',revision=owner.revision,tip=owner.tip,root='0'*64)
    if not owner.no_namespace:value['namespace_id']=owner.namespace
    self.send(value)
   def do_POST(self):
    raw=self.rfile.read(int(self.headers['Content-Length']))
    if urlsplit(self.path).path=='/cow/images':
     namespace=parse_qs(urlsplit(self.path).query)['namespace'][0];owner.uploads.append((namespace,raw))
     from PIL import Image
     with Image.open(io.BytesIO(raw)) as image:width,height=image.size
     self.send(dict(namespace_id=namespace,image_id='0'*64 if owner.bad_ack else hashlib.sha256(raw).hexdigest(),bytes=len(raw),expires_ns=9999999999999999999,width=width,height=height,media_type='image/png'))
    else:
     body=json.loads(raw);owner.generations.append((self.path,body));owner.revision+=1;owner.tip=str(owner.revision+1)*64
     self.send(dict(event='complete',receipt=dict(operation_id=body['operation_id'],snapshot=owner.tip,branch=dict(name='images',revision=owner.revision,tip=owner.tip,root='0'*64),model_contract_id='model',execution_profile_id='profile'),
      answer=dict(text='observed',tokens=[7,299],stopped=True,snapshot=owner.tip)))
  self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.addCleanup(self.stop_server)
  self.client=CowClient.http('http://127.0.0.1:'+str(self.server.server_port),journal=OperationJournal(self.root/'journal'),api_key='fixture-only',endpoint_pin='image-peer')
  self.adapter=ModelAdapter(self.client,run_id='image-feedback',model_contract_id='model',execution_profile_id='profile',eos_tokens=(299,))
  self.head=BranchHead('images',0,'1'*64,'0'*64)
  self.log=RuntimeLog(self.root/'ledger');self.addCleanup(self.close);self.kernel=FrameKernel(self.log)
  self.kernel.create_root('root','attempt',self.log.put_artifact(b'caller'),self.log.put_artifact(b'input'),ResultContract('Caller','record'))
  self.image=self.log.put_artifact(self.raw)
 def stop_server(self):
  if self.thread.is_alive():self.server.shutdown();self.server.server_close();self.thread.join(3)
 def close(self):
  if not self.log._closed:self.log.close()
 def reopen(self):self.close();self.log=RuntimeLog(self.root/'ledger');self.kernel=FrameKernel(self.log)
 def admit(self):
  from branchwrite.image_feedback import image_feedback_call
  call=image_feedback_call(self.kernel,self.adapter,identifier='feedback',source=self.head,image=self.image,text='Actual capture; inspect the image.')
  self.kernel.spawn('root',expected_epoch=0,calls=(call,),next_pc=1)
 def step(self):
  from branchwrite.image_feedback import step_image_feedback
  return step_image_feedback(self.kernel,self.adapter,'feedback')
 def test_source_namespace_observation_binds_exact_head(self):
  self.assertEqual(self.client.image_namespace(self.head),self.namespace)
  self.revision=1;self.tip='2'*64
  with self.assertRaises(RequestRejected):self.client.image_namespace(self.head)
  self.assertEqual(self.uploads,[]);self.assertEqual(self.generations,[])
 def test_missing_namespace_refuses_before_upload_admission(self):
  self.no_namespace=True
  with self.assertRaises(ReceiptError):self.admit()
  self.assertEqual(self.uploads,[]);self.assertEqual(self.generations,[])
 def test_upload_intent_is_durable_before_send_and_binds_real_bytes(self):
  self.admit();actual=self.client.upload_image
  def guarded(namespace,body):
   frame=self.kernel.frame('feedback');self.assertIsNotNone(frame['dispatch']);request=decode(self.log.read_artifact(Artifact(*frame['inputs'])))
   self.assertEqual(request['namespace_id'],self.namespace);self.assertEqual(tuple(request['image']),(self.image.sha256,self.image.size_bytes))
   self.assertEqual(body,self.raw);return actual(namespace,body)
  with patch.object(self.client,'upload_image',side_effect=guarded):value=self.step()
  self.assertEqual(value['value'][0],'ModelInput');self.assertEqual(value['value'][1][0],dict(type='image',image_id=self.image.sha256))
  self.assertEqual(self.uploads,[(self.namespace,self.raw)]);self.assertEqual(self.generations,[])
 def test_completed_upload_reopen_is_offline_and_exact(self):
  self.admit();first=self.step();self.reopen()
  with patch.object(self.client.transport,'request',side_effect=AssertionError('no head read')),patch.object(self.client.transport,'upload_image',side_effect=AssertionError('no upload')):
   second=self.step()
  self.assertEqual(first,second);self.assertEqual(len(self.uploads),1)
 def test_failure_before_dispatch_causes_no_upload_and_can_resume(self):
  self.admit()
  with patch.object(self.kernel,'dispatch',side_effect=OSError('before dispatch')):
   with self.assertRaises(OSError):self.step()
  self.assertEqual(self.uploads,[]);self.reopen();self.step();self.assertEqual(len(self.uploads),1)
 def test_lost_upload_ack_repeats_only_identical_cache_fill_after_reopen(self):
  self.admit();actual=self.client.transport.upload_image
  def lost(*args):actual(*args);raise OperationIndeterminate('lost upload acknowledgement')
  with patch.object(self.client.transport,'upload_image',side_effect=lost):
   with self.assertRaises(OperationIndeterminate):self.step()
  self.assertEqual(self.kernel.frame('feedback')['state'],'Waiting');self.assertEqual(len(self.uploads),1)
  self.reopen();self.step();self.assertEqual(self.uploads,[(self.namespace,self.raw),(self.namespace,self.raw)]);self.assertEqual(self.generations,[])
 def test_lost_kernel_return_after_upload_repeats_no_model_work(self):
  self.admit()
  with patch.object(self.kernel,'record_result',side_effect=OSError('lost local publication')):
   with self.assertRaises(OSError):self.step()
  self.reopen();self.step();self.assertEqual(len(self.uploads),2);self.assertEqual(self.generations,[])
 def test_changed_upload_receipt_never_returns_usable_input(self):
  self.admit();self.bad_ack=True
  with self.assertRaises(ReceiptError):self.step()
  self.assertEqual(self.kernel.frame('feedback')['state'],'Waiting');self.assertEqual(self.generations,[])
 def test_changed_head_after_admission_refuses_before_upload(self):
  self.admit();self.revision=1;self.tip='2'*64
  with self.assertRaises(RequestRejected):self.step()
  self.assertEqual(self.uploads,[])
 def test_changed_namespace_after_admission_refuses_before_upload(self):
  self.admit();self.namespace='b'*32
  with self.assertRaises(ReceiptError):self.step()
  self.assertEqual(self.uploads,[])
 def test_changed_artifact_refuses_before_upload(self):
  self.admit();q=self.log.artifacts/self.image.sha256;q.chmod(0o600);q.write_bytes(self.raw[:-1]+bytes([self.raw[-1]^1]))
  with self.assertRaises(CorruptLog):self.step()
  self.assertEqual(self.uploads,[]);self.assertEqual(self.generations,[])
 def cli(self,*,image=True,bind_source=True,expand=True):
  page=b'<!doctype html><style>body{margin:0}.square{width:80px;height:80px;background:#16a34a}</style><div class="square"></div>'
  source=self.root/'source';source.mkdir();(source/'index.html').write_bytes(page)
  sha=hashlib.sha256(page).hexdigest()
  bindings=dict(read=dict(type='ToolProposal',value=json.dumps(dict(tool='read_file',arguments=dict(path='index.html')))))
  if image:bindings['capture']=dict(type='ToolProposal',value=json.dumps(dict(tool='capture_page',arguments=dict(path='index.html'))))
  lines=['FLOW view','PLAN r from=read against=world -> plan','ACT r plan=plan -> outcome']
  if image:lines+=['PLAN c from=capture against=world -> plan','ACT c plan=plan -> outcome']
  lines+=['TRANSFORM feedback input=outcome contract=tool-feedback'+(' profile=image_feedback' if bind_source else '')+' -> task']
  if expand:lines+=['EXPAND inspect from=current task=task profile=control -> observed']
  lines+=['END']
  program=self.root/'view.bw';program.write_text('\n'.join(lines)+'\n')
  cfg=dict(schema=1,source=str(source),run_id='cli-view',grant=dict(edit_paths=[],read_paths=['index.html'],create_paths=[],capture_paths=['index.html'] if image else [],allow_tests=False),bindings=bindings,profiles=dict(control=dict(request_tokens=16),image_feedback=dict(kind='image-feedback',source='current')),cow=dict(endpoint_url=self.client.endpoint_url,endpoint_pin='image-peer',model_contract_id='model',execution_profile_id='profile',eos_tokens=[299],branch='images',mode='ask'))
  if image:cfg['browser']=dict(executable=os.environ['BW_BROWSER_EXECUTABLE'],width=640,height=480,timeout=15)
  config=self.root/'host.json';config.write_text(json.dumps(cfg))
  command=[sys.executable,'-B','-m','branchwrite','run',str(program),'--config',str(config),'--state',str(self.root/'cli-state')]
  first=subprocess.run(command,capture_output=True,text=True,timeout=30,env={**os.environ,'BW_COW_API_KEY':'fixture-only'})
  return first,command
 def test_real_capture_cli_upload_model_request_and_offline_restart(self):
  first,command=self.cli();self.assertEqual(first.returncode,1,first.stderr);result=json.loads(first.stdout)
  self.assertEqual(len(self.uploads),1);self.assertEqual(len(self.generations),1)
  image=result['artifacts'][0];self.assertEqual(hashlib.sha256(self.uploads[0][1]).hexdigest(),image['sha256'])
  self.assertEqual(self.generations[0][1]['content'][0],dict(type='image',image_id=image['sha256']))
  self.stop_server();second=subprocess.run(command,capture_output=True,text=True,timeout=15)
  self.assertEqual(second.returncode,1,second.stderr);self.assertEqual(first.stdout,second.stdout);self.assertEqual(len(self.uploads),1);self.assertEqual(len(self.generations),1)
 def test_text_feedback_needs_no_upload_or_extra_model_request(self):
  first,_=self.cli(image=False);self.assertEqual(first.returncode,1,first.stderr)
  self.assertEqual(self.uploads,[]);self.assertEqual(len(self.generations),1);self.assertIsInstance(self.generations[0][1]['content'],str)
 def test_legacy_capture_feedback_remains_metadata_only(self):
  first,_=self.cli(bind_source=False,expand=False);self.assertEqual(first.returncode,1,first.stderr)
  self.assertEqual(self.uploads,[]);self.assertEqual(self.generations,[])

 def test_profile_kinds_and_source_bindings_reject_before_effects(self):
  from branchwrite.execution import Executor,Grant
  from branchwrite.tool_registry import ToolRegistry
  from branchwrite.interpreter import Interpreter,AdmissionError
  source=self.root/'profile-source';source.mkdir();executor=Executor.create(source,self.root/'profile-world')
  registry=ToolRegistry(executor,Grant((),False))
  profiles=dict(control=dict(request_tokens=16),image_feedback=dict(kind='image-feedback',source='current'),
   missing_source=dict(kind='image-feedback',source='missing'))
  runtime=Interpreter(self.kernel,registry,adapter=self.adapter,profiles=profiles)
  before=self.log.event_count
  cases=[
   ('EXPAND x from=current task=task profile=image_feedback -> output','registered model profile'),
   ('TRANSFORM x input=outcome contract=tool-feedback profile=control -> task','registered image feedback profile'),
   ('TRANSFORM x input=outcome contract=tool-feedback profile=missing_source -> task','missing or incompatible typed binding'),
   ('TRANSFORM x input=output contract=cow-source profile=image_feedback -> task','registered image feedback profile')]
  for line,reason in cases:
   with self.subTest(line=line),self.assertRaisesRegex(AdmissionError,reason):
    runtime.preflight('FLOW view\n'+line+'\nEND\n',dict(current='COWSource',task='Text',outcome='ToolOutcome',output='ModelOutput'))
  with self.assertRaises(AdmissionError):
   Interpreter(self.kernel,registry,adapter=self.adapter,profiles=dict(bad=dict(kind='image-feedback',source='current',settings=dict(temperature=2))))
  self.assertEqual(self.log.event_count,before);self.assertEqual(self.uploads,[]);self.assertEqual(self.generations,[])
