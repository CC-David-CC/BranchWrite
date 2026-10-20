"""Real checkout input without exposing shared Git administration."""
import pathlib,tempfile,unittest,json,subprocess,sys,os,threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from branchwrite.execution import Executor,ToolRejected
class ProjectAdmissionTests(unittest.TestCase):
 def test_low_level_executor_still_rejects_git_administration(self):
  with tempfile.TemporaryDirectory() as t:
   root=pathlib.Path(t);project=root/'source';project.mkdir();(project/'.git').mkdir()
   with self.assertRaises(ToolRejected):Executor.create(project,root/'world')
 def test_code_can_prepare_git_checkout_without_copying_git_metadata(self):
  for kind in ['directory','worktree-file','real-checkout','real-worktree']:
   with self.subTest(kind=kind),tempfile.TemporaryDirectory() as t:
    root=pathlib.Path(t);project=root/'source';project.mkdir();(project/'app.py').write_text('original\n')
    if kind=='directory':
     (project/'.git').mkdir();(project/'.git/config').write_text('PRIVATE_ADMIN_DO_NOT_COPY')
    elif kind=='worktree-file':(project/'.git').write_text('gitdir: /outside/private-administration\n')
    else:
     def git(*args,cwd=project):
      subprocess.run(['git','-c','core.hooksPath=/dev/null','-c','core.fsmonitor=false',*args],cwd=cwd,check=True,capture_output=True)
     git('init','-q');git('add','app.py')
     git('-c','user.name=Fixture','-c','user.email=fixture@invalid','commit','-qm','fixture')
     if kind=='real-worktree':
      linked=root/'linked';git('worktree','add','--detach',str(linked),'HEAD');project=linked
    requests=[]
    class Handler(BaseHTTPRequestHandler):
     def log_message(self,*args):pass
     def do_POST(self):
      requests.append(self.path);self.send_response(401);self.send_header('Content-Length','0');self.end_headers()
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
     connection=root/'connection.json';connection.write_text(json.dumps(dict(endpoint_url='http://127.0.0.1:'+str(server.server_port),endpoint_pin='owned',model_contract_id='model',execution_profile_id='profile',eos_tokens=[256])))
     task=root/'task.txt';task.write_text('Inspect app')
     state=root/'state'
     command=[sys.executable,'-B','-m','branchwrite','code',str(project),'--task-file',str(task),'--connection',str(connection),'--state',str(state),'--branch','project','--read','app.py','--test-command','python3 -m unittest']
     r=subprocess.run(command,capture_output=True,text=True,timeout=15,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',BW_COW_API_KEY='wrong'))
     self.assertEqual(r.returncode,2,r.stderr);self.assertIn('COW HTTP 401',r.stderr)
     self.assertTrue(requests)
     self.assertFalse((state/'world/workspace/.git').exists())
     self.assertEqual((state/'world/workspace/app.py').read_bytes(),(project/'app.py').read_bytes())
     self.assertTrue((project/'.git').exists())
    finally:server.shutdown();server.server_close();thread.join(5)

 def test_project_copy_omits_nested_git_without_following_links(self):
  with tempfile.TemporaryDirectory() as t:
   root=pathlib.Path(t);project=root/'source';project.mkdir()
   private=root/'private';private.mkdir();(private/'secret').write_text('not project data')
   (project/'.git').symlink_to(private,target_is_directory=True)
   (project/'src').mkdir();(project/'src/.git').write_text('gitdir: /elsewhere')
   (project/'.github').mkdir();(project/'.github/config').write_text('ordinary project file')
   e=Executor.create(project,root/'world',project_input=True)
   self.assertFalse((e.workspace/'.git').exists());self.assertFalse((e.workspace/'src/.git').exists())
   self.assertEqual((e.workspace/'.github/config').read_text(),'ordinary project file')
   self.assertEqual((private/'secret').read_text(),'not project data')
 def test_project_copy_still_rejects_other_links_and_bad_policy_types(self):
  with tempfile.TemporaryDirectory() as t:
   root=pathlib.Path(t);project=root/'source';project.mkdir();(project/'app.py').symlink_to('/etc/passwd')
   with self.assertRaises(ToolRejected):Executor.create(project,root/'world',project_input=True)
   self.assertFalse((root/'world').exists())
   with self.assertRaises(ToolRejected):Executor.create(project,root/'other',project_input='yes')
 def test_project_launch_cannot_grant_git_administration(self):
  from branchwrite.coding_cli import build_launch
  with tempfile.TemporaryDirectory() as t:
   for path in ['.git/config','src/.git/HEAD','.git']:
    with self.subTest(path=path),self.assertRaises(ValueError):
     build_launch(t,'Inspect',dict(endpoint_url='http://127.0.0.1:1',endpoint_pin='owned',model_contract_id='m',execution_profile_id='p',eos_tokens=[256]),branch='new',read_paths=[path],test_commands=['python3 -m unittest'])
