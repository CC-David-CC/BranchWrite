"""Real HTTP delivery of provisional recovery notices, not GPU qualification."""
import io,json,threading,unittest
from contextlib import redirect_stderr
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from branchwrite.cow_client import HTTPTransport
class SourceNoticeTests(unittest.TestCase):
 def test_notice_arrives_before_completion_and_cannot_mutate_stream(self):
  observed=threading.Event();release=threading.Event();received=[]
  source='a'*64
  first=dict(event='source_recomputation_started',source_snapshot=source,history_tokens=8192)
  final=dict(event='complete',answer={},receipt={})
  class Handler(BaseHTTPRequestHandler):
   def log_message(self,*args):pass
   def do_POST(self):
    self.rfile.read(int(self.headers.get('Content-Length','0')))
    self.send_response(200);self.send_header('Content-Type','application/x-ndjson');self.send_header('Connection','close');self.end_headers()
    self.wfile.write((json.dumps(first)+'\n').encode());self.wfile.flush()
    release.wait(5)
    self.wfile.write((json.dumps(final)+'\n').encode());self.wfile.flush()
    self.close_connection=True
  server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
  thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  self.addCleanup(server.server_close);self.addCleanup(lambda:(server.shutdown(),thread.join(2)))
  def notice(value):
   received.append(dict(value));value['event']='mutated';observed.set()
  transport=HTTPTransport('http://127.0.0.1:'+str(server.server_port),notice_handler=notice)
  results=[];errors=[]
  def call():
   try:results.append(transport.request('POST','/run',b'{}',stream=True))
   except BaseException as e:errors.append(e)
  worker=threading.Thread(target=call);worker.start()
  try:
   self.assertTrue(observed.wait(2),'notice must not wait for model completion')
   self.assertTrue(worker.is_alive())
  finally:release.set();worker.join(5)
  self.assertFalse(worker.is_alive());self.assertEqual(errors,[])
  self.assertEqual(received,[first])
  self.assertEqual(results[0].events[0],first)
 def test_cli_recovery_notice_leaves_stdout_machine_protocol_alone(self):
  from branchwrite.run_cli import _source_notice
  out=io.StringIO();err=io.StringIO()
  from contextlib import redirect_stdout
  with redirect_stdout(out),redirect_stderr(err):
   _source_notice(dict(event='source_recomputation_started',history_tokens=8192))
   _source_notice(dict(event='source_recomputed',prefix_forward_tokens=8192))
   _source_notice(dict(event='source_recomputation_failed',error='disk problem\nnext line'))
  self.assertEqual(out.getvalue(),'')
  self.assertIn('8192',err.getvalue());self.assertIn('prefix cost',err.getvalue())
  self.assertIn('failed',err.getvalue())
 def test_invalid_handler_rejected_before_network(self):
  with self.assertRaises(ValueError):HTTPTransport('http://127.0.0.1:1',notice_handler=42)
