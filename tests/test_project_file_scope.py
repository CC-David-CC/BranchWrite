"""Project scope supports new file names while retaining real filesystem boundaries."""
import hashlib,json,os,tempfile,unittest
from pathlib import Path
from branchwrite.execution import Executor,Grant,ToolRejected
from branchwrite.tool_registry import ToolRegistry
from branchwrite.terminal import ShellConfig

class ProjectFileScopeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name);self.source=self.base/'source';self.source.mkdir()
        (self.source/'existing.txt').write_text('before')
        self.executor=Executor.create(self.source,self.base/'world',shell=ShellConfig(timeout=3),project_input=True)
        self.grant=Grant((),False,allow_shell=True,project_files=True)
        self.registry=ToolRegistry(self.executor,self.grant)

    def call(self,tool,args,operation,observations=()):
        plan=self.registry.freeze(json.dumps(dict(tool=tool,arguments=args)),observations=observations)
        return self.registry.execute(plan,operation)

    def test_new_names_can_be_created_read_and_refined_after_admission(self):
        created=self.call('create_text_file',dict(path='pages/new page.html',lines=['first'],line_ending='LF',final_newline=True),'create')
        read=self.call('read_file',dict(path='pages/new page.html'),'read')
        edited=self.call('replace_text_file',dict(path='pages/new page.html',lines=['corrected'],line_ending='LF',final_newline=True),'edit',(read.observation,))
        self.assertEqual((self.executor.workspace/'pages/new page.html').read_bytes(),b'corrected\n')
        self.assertFalse((self.source/'pages').exists())
        self.assertEqual((self.source/'existing.txt').read_text(),'before')

    def test_existing_files_need_actual_read_and_current_hash(self):
        args=dict(path='existing.txt',before='before',after='after')
        with self.assertRaises(ToolRejected):self.registry.freeze(json.dumps(dict(tool='replace',arguments=args)))
        read=self.call('read_file',dict(path='existing.txt'),'observe')
        plan=self.registry.freeze(json.dumps(dict(tool='replace',arguments=args)),observations=(read.observation,))
        (self.executor.workspace/'existing.txt').write_text('another writer')
        with self.assertRaises(ToolRejected):self.registry.execute(plan,'stale')
        self.assertEqual((self.executor.workspace/'existing.txt').read_text(),'another writer')

    def test_project_scope_rejects_escape_git_and_symlink_routes(self):
        outside=self.base/'outside';outside.mkdir();(outside/'keep.txt').write_text('keep')
        (self.executor.workspace/'link').symlink_to(outside,target_is_directory=True)
        for path in ['../outside/keep.txt','/tmp/elsewhere','.git/config','nested/.git/config','link/new.txt']:
            with self.subTest(path=path),self.assertRaises(ToolRejected):
                self.call('create_file',dict(path=path,content='bad'),'escape')
        self.assertEqual((outside/'keep.txt').read_text(),'keep')
        self.assertFalse((outside/'new.txt').exists())

    def test_project_shell_sees_files_created_after_admission(self):
        self.call('create_file',dict(path='new.txt',content='new contents'),'create')
        result=self.call('run_shell',dict(command="cat existing.txt new.txt"),'command')
        self.assertEqual(result.exit_code,0)
        self.assertEqual(result.stdout,b'beforenew contents')
        self.assertTrue(result.metadata['isolation']['worker_exited'])
        self.assertEqual(result.metadata['isolation']['namespace_members_after'],[])

    def test_fixed_grants_do_not_gain_project_access(self):
        grant=Grant((),False,read_paths=('existing.txt',))
        with self.assertRaises(ToolRejected):self.executor.create_file('denied',grant,'new.txt',b'no')
        self.assertEqual(self.executor.read_file('read-fixed',grant,'existing.txt').stdout.read_bytes(),b'before')
        for value in [1,'true',None]:
            with self.subTest(value=value),self.assertRaises(ToolRejected):Grant((),False,project_files=value)

    def test_schema_and_grammar_accept_future_paths_but_host_validates_them(self):
        schema=self.registry.model_schema()
        for variant in schema['oneOf']:
            name=variant['properties']['tool']['enum'][0]
            if name in ['read_file','create_file','replace']:
                rule=variant['properties']['arguments']['properties']['path']
                self.assertEqual(rule['type'],'string');self.assertNotIn('enum',rule)
        self.assertIn('project-path',self.registry.model_gbnf())
        self.registry.parse(json.dumps(dict(tool='read_file',arguments=dict(path='not-known-yet.py'))))
        with self.assertRaises(ToolRejected):self.registry.parse(json.dumps(dict(tool='read_file',arguments=dict(path='../outside'))))

if __name__=='__main__':unittest.main()
