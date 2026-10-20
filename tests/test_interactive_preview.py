import hashlib,json,socket,tempfile,unittest,urllib.error,urllib.request
from pathlib import Path
from branchwrite.workspace_versions import WorkspaceVersions

class PreviewTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.root=Path(self.temp.name);self.project=self.root/'project';self.project.mkdir()
  (self.project/'index.html').write_text('<!doctype html><link rel="stylesheet" href="style.css"><h1>Saved page</h1><p>caf\u00e9</p>')
  (self.project/'style.css').write_text('h1{color:blue}')
  (self.project/'.env').write_text('PRIVATE=not-for-preview')
  self.versions=WorkspaceVersions(self.project,self.root/'files')
  self.commit=self.versions.capture('first',context=None,parent=None,source=self.project)['commit']
 def preview(self,**kw):
  from branchwrite.interactive_preview import Preview
  p=Preview();self.addCleanup(p.close);return p,p.show(self.versions,self.commit,**kw)
 def test_http_serves_exact_saved_version_and_relative_assets_without_model_work(self):
  preview,url=self.preview();(self.project/'index.html').write_text('new unsaved edit')
  with urllib.request.urlopen(url) as response:
   data=response.read();self.assertIn(b'Saved page',data);self.assertIn('caf\u00e9'.encode(),data)
   self.assertEqual(response.headers['Cache-Control'],'no-store')
   self.assertEqual(response.headers['Referrer-Policy'],'no-referrer')
  with urllib.request.urlopen(url.rsplit('/',1)[0]+'/style.css?v=2') as response:
   self.assertEqual(response.read(),b'h1{color:blue}');self.assertIn('text/css',response.headers['Content-Type'])
  with urllib.request.urlopen(urllib.request.Request(url,method='HEAD')) as response:
   self.assertEqual(response.read(),b'');self.assertEqual(int(response.headers['Content-Length']),len(data))
 def test_only_token_scoped_captured_resources_are_served(self):
  preview,url=self.preview();origin=url.split('/')[0]+'//'+url.split('/')[2];folder=url.rsplit('/',1)[0]
  for denied in [origin+'/',origin+'/index.html',folder+'/.env',folder+'/%2e%2e/index.html',folder+'/../index.html',folder+'/%2findex.html',folder+'/']:
   with self.subTest(url=denied):
    with self.assertRaises(urllib.error.HTTPError) as cm:urllib.request.urlopen(denied)
    self.assertEqual(cm.exception.code,404)
  with self.assertRaises(urllib.error.HTTPError) as cm:urllib.request.urlopen(urllib.request.Request(url,data=b'x'))
  self.assertEqual(cm.exception.code,405)
 def test_refresh_retires_previous_url_and_close_releases_port(self):
  preview,url=self.preview();port=preview.port
  new=preview.show(self.versions,self.commit)
  self.assertEqual(preview.port,port,'refresh should keep an existing SSH tunnel usable')
  with self.assertRaises((OSError,urllib.error.URLError)):urllib.request.urlopen(url,timeout=1)
  self.assertNotEqual(url,new);preview.close();preview.close()
  with self.assertRaises(OSError):socket.create_connection(('127.0.0.1',preview.port),timeout=1)
 def test_document_selection_is_bounded_and_does_not_leak_non_web_files(self):
  from branchwrite.interactive_preview import Preview
  for bad in ['../index.html','/index.html','.env','style.css','index.html?x=1']:
   with self.subTest(bad=bad),self.assertRaises(ValueError):
    Preview().show(self.versions,self.commit,document=bad)
 def test_missing_default_has_actionable_choice_without_starting_server(self):
  from branchwrite.interactive_preview import Preview
  (self.project/'index.html').unlink();(self.project/'a.html').write_text('A');(self.project/'b.html').write_text('B')
  commit=self.versions.capture('multiple',context=None,parent=self.commit,source=self.project)['commit'];p=Preview();self.addCleanup(p.close)
  with self.assertRaisesRegex(ValueError,'/preview.*html'):p.show(self.versions,commit)
  self.assertIsNone(p.port)
  url=p.show(self.versions,commit,document='b.html')
  with urllib.request.urlopen(url) as response:self.assertEqual(response.read(),b'B')
 def test_asset_count_limit_is_explicit_and_preserves_previous_preview(self):
  preview,url=self.preview()
  for n in range(65):(self.project/(str(n)+'.css')).write_text('x')
  commit=self.versions.capture('many',context=None,parent=self.commit,source=self.project)['commit']
  with self.assertRaisesRegex(ValueError,'resource.*limit'):preview.show(self.versions,commit)
  with urllib.request.urlopen(url) as response:self.assertIn(b'Saved page',response.read())
 def test_unreferenced_git_blob_corruption_is_not_accepted(self):
  from branchwrite.interactive_preview import Preview
  manifest=self.versions.read(self.commit);blob=manifest['files']['index.html']['blob']
  # Supply a corrupted payload through the existing Git reader boundary. This
  # checks the preview's SHA assertion independently of Git's own object IDs.
  original=self.versions._git
  def corrupt(*args,**kwargs):
   return b'changed' if args==('cat-file','blob',blob) else original(*args,**kwargs)
  self.versions._git=corrupt
  with self.assertRaisesRegex(ValueError,'hash'):Preview().show(self.versions,self.commit)

 def test_slow_request_cannot_hold_preview_shutdown(self):
  import time
  preview,url=self.preview();connection=socket.create_connection(('127.0.0.1',preview.port));self.addCleanup(connection.close)
  connection.sendall(b'GET /unfinished HTTP/1.1\r\n')
  time.sleep(.05);started=time.monotonic();preview.close()
  self.assertLess(time.monotonic()-started,3.5)
 def test_host_and_absolute_url_aliases_are_rejected(self):
  import http.client
  preview,url=self.preview();path=url.split(str(preview.port),1)[1]
  for target,host in [(path,'untrusted.example'),(url,'127.0.0.1:'+str(preview.port))]:
   with self.subTest(target=target,host=host):
    c=http.client.HTTPConnection('127.0.0.1',preview.port,timeout=2)
    try:c.request('GET',target,headers={'Host':host});response=c.getresponse();self.assertEqual(response.status,404);response.read()
    finally:c.close()
 def test_help_distinguishes_local_browser_from_remote_client(self):
  from branchwrite.interactive_preview import instructions
  url='http://127.0.0.1:12345/opaque/index.html'
  local=instructions(url,12345,environ={});self.assertIn(url,local);self.assertNotIn('ssh -N',local)
  remote=instructions(url,12345,environ={'SSH_CONNECTION':'10.0.7.1 40000 10.0.7.95 22'})
  self.assertIn('ssh -N -L 12345:127.0.0.1:12345',remote);self.assertIn('@10.0.7.95',remote);self.assertIn(url,remote)
