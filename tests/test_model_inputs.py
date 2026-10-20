"""Typed image inputs through the real CLI/HTTP journal. No GPU qualification.

The HTTP peer returns deterministic synthetic receipts; live H02 must separately
prove image delivery and interpretation on Q4.
"""
import json,os,subprocess,sys,tempfile,threading,unittest
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from branchwrite.cow_client import CowClient,OperationJournal,BranchHead,OperationReuseError
from branchwrite.model_dispatch import ModelAdapter,ModelContractError
from branchwrite.interpreter import AdmissionError
from branchwrite.run_cli import _config
from branchwrite.records import RuntimeLog,Artifact,decode

PARTS=[dict(type='image',image_id='a'*64),dict(type='text',text='Describe the attached image.')]
class ModelInputTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
  self.posts=[];self.revision=0;self.tip='1'*64;owner=self
  class Handler(BaseHTTPRequestHandler):
   def log_message(self,*args):pass
   def send(self,value):
    body=(json.dumps(value)+'\n').encode()
    self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
   def do_GET(self):self.send(dict(branch=dict(name='images',revision=owner.revision,tip=owner.tip,root='0'*64)))
   def do_POST(self):
    body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
    owner.posts.append((self.path,body));owner.revision+=1;owner.tip=str(owner.revision+1)*64
    self.send(dict(event='complete',receipt=dict(operation_id=body['operation_id'],snapshot=owner.tip,branch=dict(name='images',revision=owner.revision,tip=owner.tip,root='0'*64),model_contract_id='model',execution_profile_id='profile'),
     answer=dict(text='observed',tokens=[7,299],stopped=True,snapshot=owner.tip)))
  self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.addCleanup(self.stop_server)
  self.url='http://127.0.0.1:'+str(self.server.server_port)
  self.client=CowClient.http(self.url,journal=OperationJournal(self.root/'journal'),api_key='fixture-only',endpoint_pin='test-image-peer')
  self.adapter=ModelAdapter(self.client,run_id='image-run',model_contract_id='model',execution_profile_id='profile',eos_tokens=(299,))
  self.head=BranchHead('images',0,'1'*64,'0'*64)
 def stop_server(self):
  if self.thread.is_alive():self.server.shutdown();self.server.server_close();self.thread.join(3)
 def frame(self):return dict(id='model-frame',attempt='attempt',inputs=('f'*64,10))
 def test_frozen_parts_preserve_order_and_detach_caller_data(self):
  parts=[dict(x) for x in PARTS];parts.insert(1,dict(type='image',image_id='b'*64))
  frozen=self.adapter.freeze(self.head,mode='ask',content=parts)
  before=frozen.data;parts[0]['image_id']='c'*64;parts.reverse()
  plan=self.adapter.plan(frozen);self.assertEqual(plan['config']['content'][0]['image_id'],'a'*64)
  self.assertEqual(plan['config']['content'][1]['image_id'],'b'*64);self.assertEqual(frozen.data,before)
 def test_continuation_does_not_append_image_parts_again(self):
  plan=self.adapter.plan(self.adapter.freeze(self.head,mode='ask',content=PARTS))
  first=self.adapter.native(self.frame(),plan,0,plan['source'],0)[2]
  following=self.adapter.native(self.frame(),plan,1,plan['source'],1)[2]
  self.assertEqual(json.loads(first['body'])['content'],PARTS);self.assertNotIn('content',json.loads(following['body']))
  self.assertEqual(following['path'],'/cow/text/resume')
 def test_malformed_or_unbounded_parts_fail_before_native_dispatch(self):
  bad=[[],[dict(type='image',image_id='a'*64)],dict(image='a'*64),
   [dict(type='image',image_id='../path'),dict(type='text',text='q')],
   [dict(type='image',image_id='a'*64,path='/secret'),dict(type='text',text='q')],
   [dict(type='image_url',url='http://example.invalid'),dict(type='text',text='q')],
   [dict(type='text',text='x'*262145)], [dict(type='image',image_id='a'*64)]*9+[dict(type='text',text='q')]]
  for parts in bad:
   with self.subTest(parts_type=type(parts).__name__),self.assertRaises(ModelContractError):
    self.adapter.freeze(self.head,mode='ask',content=parts)
  self.assertEqual(self.posts,[])
 def test_http_ask_and_append_keep_exact_parts_in_original_intent(self):
  for index,mode in enumerate(['ask','append_user']):
   plan=self.adapter.plan(self.adapter.freeze(self.client.head('images'),mode=mode,content=PARTS))
   request=self.adapter.native(dict(id='model-'+str(index),attempt='attempt',inputs=('f'*64,10)),plan,0,plan['source'],0)[2]
   reply=self.adapter.execute(request);self.adapter.validate_response(request,dict(operation_id=reply.operation_id,receipt=dict(reply.receipt.raw),answer=dict(reply.answer),source_binding=reply.source_binding.to_json()))
   saved=self.client.journal.read(reply.operation_id)
   self.assertEqual(json.loads(self.client.journal.decode_body(saved))['content'],PARTS)
   self.assertEqual(self.posts[-1][1]['content'],PARTS)
   with patch.object(self.client.transport,'request',side_effect=AssertionError('committed replay cannot use network')):
    again=self.adapter.execute(request)
   self.assertEqual(reply.answer,again.answer)
  self.assertEqual([x[0] for x in self.posts],['/cow/text/ask','/cow/text/append-user'])
 def config(self):
  source=self.root/'source';source.mkdir(exist_ok=True)
  return dict(schema=1,source=str(source),run_id='image-cli',grant=dict(edit_paths=[],read_paths=[],create_paths=[],allow_tests=False),
   bindings=dict(task=dict(type='ModelInput',value=[dict(x) for x in PARTS])),profiles=dict(control=dict(request_tokens=16)),
   cow=dict(endpoint_url=self.url,endpoint_pin='test-image-peer',model_contract_id='model',execution_profile_id='profile',eos_tokens=[299],branch='images',mode='ask'))
 def test_cli_accepts_typed_parts_but_not_paths_urls_or_extra_fields(self):
  cfg=self.config();self.assertEqual(_config(json.dumps(cfg))['bindings']['task']['value'],PARTS)
  for content in [[dict(type='image',image_id='bad'),dict(type='text',text='q')],[dict(type='image',path='/tmp/file.png'),dict(type='text',text='q')],{'content':PARTS}]:
   bad=json.loads(json.dumps(cfg));bad['bindings']['task']['value']=content
   with self.subTest(content=content),self.assertRaises((AdmissionError,ValueError)):_config(json.dumps(bad))
 def test_real_cli_then_restart_offline_keeps_one_image_request(self):
  config=self.root/'host.json';config.write_text(json.dumps(self.config()))
  program=self.root/'task.bw';program.write_text('FLOW image\nEXPAND inspect from=current task=task profile=control -> observed\nEND\n')
  state=self.root/'run';command=[sys.executable,'-B','-m','branchwrite','run',str(program),'--config',str(config),'--state',str(state)]
  first=subprocess.run(command,capture_output=True,text=True,timeout=20)
  self.assertEqual(first.returncode,1,first.stderr) # Complete output; no acceptance oracle was selected.
  report=json.loads(first.stdout);self.assertEqual(report['status'],'complete');self.assertFalse(report['verified'])
  self.assertEqual(len(self.posts),1);self.assertEqual(self.posts[0][1]['content'],PARTS)
  with RuntimeLog(state/'ledger') as log:
   raw=(log.artifacts/report['result_artifact']).read_bytes();value=decode(raw)[2]['bindings']['observed'][1]
   self.assertEqual(value['text'],'observed');self.assertEqual(value['consumed_output_tokens'],2)
  self.stop_server()
  second=subprocess.run(command,capture_output=True,text=True,timeout=20)
  self.assertEqual(second.returncode,1,second.stderr);self.assertEqual(first.stdout,second.stdout);self.assertEqual(len(self.posts),1)
 def test_changed_parts_cannot_resume_an_admitted_cli_run(self):
  config=self.root/'host.json';cfg=self.config();config.write_text(json.dumps(cfg))
  program=self.root/'task.bw';program.write_text('FLOW image\nEXPAND inspect from=current task=task profile=control -> observed\nEND\n')
  state=self.root/'run';command=[sys.executable,'-B','-m','branchwrite','run',str(program),'--config',str(config),'--state',str(state)]
  first=subprocess.run(command,capture_output=True,text=True,timeout=20);self.assertEqual(first.returncode,1,first.stderr)
  cfg['bindings']['task']['value'][0]['image_id']='d'*64;config.write_text(json.dumps(cfg))
  second=subprocess.run(command,capture_output=True,text=True,timeout=20);self.assertEqual(second.returncode,2,second.stderr);self.assertEqual(len(self.posts),1)
 def test_text_calls_preserve_existing_wire_shape(self):
  plan=self.adapter.plan(self.adapter.freeze(self.head,mode='ask',content='plain text'))
  request=self.adapter.native(self.frame(),plan,0,plan['source'],0)[2]
  self.assertEqual(json.loads(request['body'])['content'],'plain text')
