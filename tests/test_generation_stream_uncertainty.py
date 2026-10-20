"""Actual HTTP error stream and CLI reporting; no inference/backend qualification."""
import unittest,tempfile,threading,json,io
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from contextlib import redirect_stdout,redirect_stderr
from branchwrite.cow_client import CowClient,OperationJournal,OperationIndeterminate
class StreamUncertaintyTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.posts=0;self.kind='error';owner=self
  class Handler(BaseHTTPRequestHandler):
   def log_message(self,*args):pass
   def send(self,status,value,stream=False):
    raw=value if stream else json.dumps(value).encode();self.send_response(status);self.send_header('Content-Type','application/x-ndjson' if stream else 'application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
   def do_GET(self):
    if self.path.startswith('/cow/head'):return self.send(200,dict(name='main',revision=0,tip='a'*64,root='a'*64))
    return self.send(404,dict(error='unknown operation'))
   def do_POST(self):
    self.rfile.read(int(self.headers['Content-Length']));owner.posts+=1
    rows=[] if owner.kind=='empty' else [dict(event='text',text='uncommitted output'),dict(event=owner.kind,error='capacity unavailable')]
    self.send(200,b''.join(json.dumps(v).encode()+b'\n' for v in rows),True)
  self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.addCleanup(lambda:(self.server.shutdown(),self.server.server_close(),self.thread.join(2)))
  self.client=CowClient.http('http://127.0.0.1:'+str(self.server.server_port),journal=OperationJournal(Path(self.tmp.name)/'journal'),endpoint_pin='owned-test')
 def check_pending(self,kind):
  self.kind=kind;op='stream-'+kind
  with self.assertRaises(OperationIndeterminate) as caught:self.client.answer('main',0,op,3)
  self.assertEqual(caught.exception.operation_id,op);self.assertEqual(self.client.journal.read(op)['state'],'pending')
  with self.assertRaises(OperationIndeterminate):self.client.answer('main',0,op,3)
  with self.assertRaises(OperationIndeterminate):self.client.reconcile_generation(op)
  self.assertEqual(self.posts,1);self.assertNotIn('answer',self.client.journal.read(op))
 def test_error_retains_original_pending_identity(self):self.check_pending('error')
 def test_failure_retains_original_pending_identity(self):self.check_pending('failure')
 def test_eof_retains_original_pending_identity(self):self.check_pending('empty')
 def test_first_cli_failure_reports_unresolved_original_operation(self):
  from branchwrite.__main__ import _run_result
  err=io.StringIO()
  with redirect_stdout(io.StringIO()),redirect_stderr(err):code=_run_result(lambda:self.client.answer('main',0,'original-stream',3))
  self.assertEqual(code,4);self.assertIn('original-stream',err.getvalue());self.assertIn('reconcile',err.getvalue());self.assertIn('capacity unavailable',err.getvalue());self.assertEqual(self.posts,1)
 def test_rejected_http_response_is_closed(self):
  from urllib.error import HTTPError
  from unittest.mock import patch
  from branchwrite.cow_client import HTTPTransport,RequestRejected
  body=io.BytesIO(b'{"error":"bad request"}')
  failure=HTTPError('http://127.0.0.1:1/cow/status',400,'bad',{},body)
  with patch('branchwrite.cow_client.urlopen',side_effect=failure):
   with self.assertRaises(RequestRejected):HTTPTransport('http://127.0.0.1:1').request('GET','/cow/status')
  self.assertTrue(body.closed)
if __name__=='__main__':unittest.main()
