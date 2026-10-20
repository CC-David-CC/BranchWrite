"""Real prompt-toolkit input: draft preservation and distinct steering/queue keys."""
import asyncio,tempfile,unittest
from pathlib import Path
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput

class Service:
    def __init__(self):self.running=True;self.calls=[];self.stops=0;self.closed=False;self.snapshot={'status':'working','history':[]}
    def start(self,emit):self.emit=emit
    def submit(self,text,*,mode,kind):self.calls.append((text,mode,kind));return 'saved-input'
    def stop(self):self.stops+=1
    def close(self):self.closed=True

class InteractiveTerminalTests(unittest.IsolatedAsyncioTestCase):
    async def test_typing_survives_progress_tab_queues_and_enter_steers(self):
        from branchwrite.interactive_terminal import Terminal
        service=Service()
        with tempfile.TemporaryDirectory() as td,create_pipe_input() as pipe:
            terminal=Terminal(service,Path(td),input=pipe,output=DummyOutput())
            task=asyncio.create_task(terminal.run())
            await asyncio.sleep(.05)
            pipe.send_text('Blue ?')
            await asyncio.sleep(.05)
            service.emit('Checking the page')
            await asyncio.sleep(.05)
            self.assertEqual(terminal.prompt.default_buffer.text,'Blue ?')
            pipe.send_text('\t')
            await asyncio.sleep(.05)
            self.assertEqual(service.calls,[('Blue ?','work','queue')])
            pipe.send_text('Make it bigger\r')
            await asyncio.sleep(.05)
            self.assertEqual(service.calls[-1],('Make it bigger','work','steer'))
            pipe.send_text('/exit\r')
            await asyncio.wait_for(task,2)
            self.assertTrue(service.closed)
    async def test_plan_aside_history_and_unknown_commands_are_not_work_requests(self):
        from branchwrite.interactive_terminal import Terminal
        service=Service();service.running=False
        with tempfile.TemporaryDirectory() as td,create_pipe_input() as pipe:
            terminal=Terminal(service,Path(td),input=pipe,output=DummyOutput())
            task=asyncio.create_task(terminal.run());await asyncio.sleep(.05)
            for text in ['/plan','Explain options','/aside What is a class?','/history','/oops','/exit']:
                pipe.send_text(text+'\r');await asyncio.sleep(.04)
            await asyncio.wait_for(task,2)
            self.assertEqual(service.calls,[('Explain options','plan','send'),('What is a class?','aside','queue')])
    async def test_escape_stops_work_without_erasing_the_draft(self):
        from branchwrite.interactive_terminal import Terminal
        service=Service()
        with tempfile.TemporaryDirectory() as td,create_pipe_input() as pipe:
            terminal=Terminal(service,Path(td),input=pipe,output=DummyOutput())
            task=asyncio.create_task(terminal.run());await asyncio.sleep(.05)
            pipe.send_text('Keep typing');await asyncio.sleep(.05)
            pipe.send_bytes(b'\x1b');await asyncio.sleep(.7)
            self.assertEqual(service.stops,1)
            self.assertEqual(terminal.prompt.default_buffer.text,'Keep typing')
            pipe.send_bytes(b'\x15');pipe.send_text('/exit\r')
            await asyncio.wait_for(task,2)

    async def test_plan_mode_cannot_restore_or_edit_files_via_branch_controls(self):
        from branchwrite.interactive_terminal import Terminal
        service=Service();service.running=False
        with tempfile.TemporaryDirectory() as td,create_pipe_input() as pipe:
            terminal=Terminal(service,Path(td),input=pipe,output=DummyOutput())
            task=asyncio.create_task(terminal.run());await asyncio.sleep(.05)
            for text in ['/plan','/edit 1 Make green','/explore 1 Try green','/switch 1','/work','/edit 1 Make blue','/exit']:
                pipe.send_text(text+'\r');await asyncio.sleep(.04)
            await asyncio.wait_for(task,2)
            self.assertEqual(service.calls,[('1 Make blue','edit','queue')])

    async def test_preview_uses_selected_file_version_without_submitting_work_and_closes(self):
        import re,urllib.request
        from branchwrite.interactive_terminal import Terminal
        from branchwrite.workspace_versions import WorkspaceVersions
        service=Service();service.running=False
        with tempfile.TemporaryDirectory() as td,create_pipe_input() as pipe:
            project=Path(td)/'project';project.mkdir();state=Path(td)/'session'
            (project/'index.html').write_text('<h1>Selected saved website</h1>')
            versions=WorkspaceVersions(project,state/'files')
            commit=versions.capture('saved',context=None,parent=None,source=project)['commit']
            service.project=project;service.snapshot['current']={'file_commit':commit,'workdir':str(project)}
            terminal=Terminal(service,state,input=pipe,output=DummyOutput())
            messages=[];original=terminal.notify
            def notify(text):messages.append(text);original(text)
            terminal.notify=notify
            task=asyncio.create_task(terminal.run());await asyncio.sleep(.05)
            pipe.send_text('/preview\r');await asyncio.sleep(.15)
            links=re.findall(r'http://127\.0\.0\.1:[0-9]+/[^\s]+','\n'.join(messages))
            self.assertEqual(len(links),1,messages);url=links[0]
            with urllib.request.urlopen(url) as response:self.assertEqual(response.read(),b'<h1>Selected saved website</h1>')
            self.assertEqual(service.calls,[])
            pipe.send_text('/exit\r');await asyncio.wait_for(task,3)
            with self.assertRaises(OSError):urllib.request.urlopen(url,timeout=1)

    async def test_missing_preview_is_a_notice_and_does_not_stop_the_session(self):
        from branchwrite.interactive_terminal import Terminal
        service=Service();service.running=False
        with tempfile.TemporaryDirectory() as td,create_pipe_input() as pipe:
            terminal=Terminal(service,Path(td),input=pipe,output=DummyOutput());messages=[]
            terminal.notify=messages.append
            task=asyncio.create_task(terminal.run());await asyncio.sleep(.05)
            pipe.send_text('/preview\r');await asyncio.sleep(.1)
            self.assertTrue(any('No saved website' in v for v in messages),messages)
            pipe.send_text('/exit\r');await asyncio.wait_for(task,2)
            self.assertEqual(service.calls,[])
