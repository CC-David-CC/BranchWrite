"""Local static preview from existing immutable file versions.

COW histories/controllers are untouched. Only bounded web files from the selected
Git checkpoint are read. Requests resolve captured bytes, never filesystem paths.
Refreshing replaces the captured bundle and retires its old URL. The same
loopback port keeps an SSH tunnel usable; closing the terminal retires the server.
"""
from hashlib import sha256
from http.server import BaseHTTPRequestHandler,HTTPServer
from pathlib import PurePosixPath
import secrets
import socket
import threading
from urllib.parse import quote,urlsplit
from .browser_assets import document_path

MAX_FILES=65
MAX_FILE_BYTES=4*1024*1024
MAX_TOTAL_BYTES=20*1024*1024
MEDIA={'.html':'text/html; charset=utf-8','.htm':'text/html; charset=utf-8',
 '.css':'text/css; charset=utf-8','.js':'text/javascript; charset=utf-8',
 '.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.webp':'image/webp',
 '.gif':'image/gif','.svg':'image/svg+xml','.ico':'image/x-icon',
 '.woff':'font/woff','.woff2':'font/woff2'}
# Direct documents are opt-in, never additional resources in a website bundle.
DOCUMENT_MEDIA={'.pdf':'application/pdf','.txt':'text/plain; charset=utf-8'}

class Preview:
 def __init__(self):
  self._server=None;self._thread=None;self.port=None
 def show(self,versions,commit,*,document=None):
  manifest=versions.read(commit);files=manifest['files']
  allowed={name:entry for name,entry in files.items()
   if PurePosixPath(name).suffix.lower() in MEDIA
   and not any(part.startswith('.') for part in PurePosixPath(name).parts)}
  if document is None:
   if 'index.html' in allowed:document='index.html'
   else:
    pages=[p for p in allowed if PurePosixPath(p).suffix.lower() in ('.html','.htm')]
    if len(pages)==1:document=pages[0]
    elif not pages:
     pdfs=[name for name in files if PurePosixPath(name).suffix.lower()=='.pdf' and not any(part.startswith('.') for part in PurePosixPath(name).parts)]
     if len(pdfs)==1:document=pdfs[0]
     elif pdfs:raise ValueError('Choose a PDF: /preview report.pdf (saved PDFs: '+', '.join(sorted(pdfs)[:8])+')')
     else:raise ValueError('No saved website yet. Ask me to make one first, or use /preview filename.txt for a saved text document.')
    else:raise ValueError('Choose a page: /preview page.html (saved pages: '+', '.join(sorted(pages)[:8])+')')
  document_path(document)
  suffix=PurePosixPath(document).suffix.lower();media=MEDIA
  if suffix in DOCUMENT_MEDIA and document in files and not any(part.startswith('.') for part in PurePosixPath(document).parts):
   allowed={document:files[document]};media=DOCUMENT_MEDIA
  elif document not in allowed or suffix not in ('.html','.htm'):
   raise ValueError('Choose a saved HTML page, PDF or .txt document inside this project')
  if len(allowed)>MAX_FILES:raise ValueError('Preview resource count exceeds the limit (65 files)')
  token=secrets.token_urlsafe(24);prefix='/'+token+'/';resources={};total=0
  for name,entry in allowed.items():
   document_path(name)
   raw=versions._git('cat-file','blob',entry['blob'])
   if len(raw)>MAX_FILE_BYTES:raise ValueError('Preview resource exceeds the file limit')
   total+=len(raw)
   if total>MAX_TOTAL_BYTES:raise ValueError('Preview resources exceed the total byte limit')
   if sha256(raw).hexdigest()!=entry['sha256']:raise ValueError('Saved preview file hash disagrees with its checkpoint')
   resources[prefix+quote(name,safe='/')]=(raw,media[PurePosixPath(name).suffix.lower()])
  if self._server is not None:
   self._server.resources=resources
   return 'http://127.0.0.1:'+str(self.port)+prefix+quote(document,safe='/')
  class Handler(BaseHTTPRequestHandler):
   def serve(self,head=False):
    # Numeric loopback binding and an exact Host prevent rebinding/absolute-URL
    # aliases. No directory listing, disk IO, proxy, API key or model call.
    host=self.headers.get('Host','')
    if host not in ('127.0.0.1:'+str(self.server.server_port),'localhost:'+str(self.server.server_port)):
     self.send_error(404);return
    target=urlsplit(self.path)
    if target.scheme or target.netloc:
     self.send_error(404);return
    resource=self.server.resources.get(target.path)
    if resource is None:self.send_error(404);return
    body,media=resource
    self.send_response(200);self.send_header('Content-Type',media)
    self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store')
    self.send_header('Referrer-Policy','no-referrer');self.send_header('X-Content-Type-Options','nosniff')
    self.end_headers()
    if not head:self.wfile.write(body)
   def handle_preview(self,head=False):
    try:self.serve(head)
    except (BrokenPipeError,ConnectionResetError,TimeoutError):pass # normal browser disconnect/retirement
   def do_GET(self):self.handle_preview()
   def do_HEAD(self):self.handle_preview(True)
   def do_POST(self):self.send_error(405)
   def do_PUT(self):self.send_error(405)
   def do_DELETE(self):self.send_error(405)
   def log_message(self,*args):pass
   def setup(self):
    super().setup();self.connection.settimeout(2)
  class Server(HTTPServer):
   def process_request(self,request,address):
    # A slow local reader must not keep terminal shutdown waiting indefinitely.
    # Unlike socket inactivity timeout, this bounds the whole request lifetime.
    def retire():
     try:request.shutdown(socket.SHUT_RDWR)
     except OSError:pass
    timer=threading.Timer(2,retire);timer.daemon=True;timer.start()
    try:super().process_request(request,address)
    finally:timer.cancel()
  server=Server(('127.0.0.1',0),Handler);server.resources=resources
  thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.05},name='branchwrite-preview',daemon=False)
  self._server=server;self._thread=thread;self.port=server.server_port
  try:thread.start()
  except BaseException:self._server=None;self._thread=None;server.server_close();raise
  return 'http://127.0.0.1:'+str(self.port)+prefix+quote(document,safe='/')
 def close(self):
  server,thread=self._server,self._thread
  if server is None:return
  server.shutdown();server.server_close();thread.join(timeout=3)
  if thread.is_alive():raise RuntimeError('Preview did not settle; retain its ownership')
  self._server=None;self._thread=None


def instructions(url,port,*,environ=None):
 """Explain which computer owns localhost; never expose the server to the LAN."""
 import getpass,ipaddress,os,shlex
 env=os.environ if environ is None else environ
 parts=env.get('SSH_CONNECTION','').split()
 if len(parts)==4:
  try:host=str(ipaddress.ip_address(parts[2]))
  except ValueError:host=None
  if host is not None:
   target=shlex.quote(getpass.getuser()+'@'+host)
   return ('Preview is saved on this client, not the inference server.\n'
    'On your own computer, keep this command running in another terminal:\n'
    'ssh -N -L '+str(port)+':127.0.0.1:'+str(port)+' '+target+'\n'
    'Then open this link in your browser: '+url+'\n'
    'Keep BranchWrite open while viewing. /preview refreshes the saved version.')
 return ('Open this link in your browser: '+url+'\n'
  'Keep BranchWrite open while viewing. /preview refreshes the saved version.')
