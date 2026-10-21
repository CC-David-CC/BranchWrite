"""Responsive terminal presentation; the worker owns workflow and tool execution."""
import asyncio
from pathlib import Path
from prompt_toolkit import PromptSession, print_formatted_text
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.patch_stdout import patch_stdout
from .run_report import terminal_text
from .interactive_preview import Preview, instructions
from .workspace_versions import WorkspaceVersions


class Terminal:
    def __init__(self, service, state, *, input=None, output=None):
        self.service=service;self.state=Path(state);self.mode='work';self.loop=None
        self.preview=Preview()
        self.state.mkdir(parents=True,exist_ok=True,mode=0o700)
        history=self.state/'prompt-history';history.touch(mode=0o600,exist_ok=True)
        keys=KeyBindings()
        @keys.add('tab')
        def queue(event):
            text=event.current_buffer.text.strip()
            if not text:return
            try:self._submit(text,'queue')
            except (ValueError,OSError,RuntimeError) as error:self.notify(str(error));return
            event.current_buffer.append_to_history();event.current_buffer.reset()
        @keys.add('escape')
        @keys.add('c-c')
        def stop(event):
            self.service.stop()
            self.notify('Stopping at a safe boundary. Your draft is still here.')
        @keys.add('escape','enter')
        def newline(event):event.current_buffer.insert_text('\n')
        self.prompt=PromptSession(history=FileHistory(str(history)),key_bindings=keys,
            input=input,output=output,enable_history_search=True,
            bottom_toolbar=lambda:terminal_text(self.mode+' | '+str(self.service.snapshot.get('status','ready'))+' | Enter: send/steer   Tab: queue   Esc: stop   Ctrl-R: history'),
            complete_while_typing=False)
        self.prompt.app.ttimeoutlen=.1
        self.prompt.app.timeoutlen=.3
    def notify(self,text):
        def display():
            print_formatted_text(terminal_text(str(text)),output=self.prompt.app.output)
            self.prompt.app.invalidate()
        if self.loop is not None:self.loop.call_soon_threadsafe(display)
    def _submit(self,text,kind):
        identity=self.service.submit(text,mode=self.mode,kind=kind)
        self.notify('Queued for the next turn.' if kind=='queue' else 'Saved. I will use this at the next safe boundary.' if kind=='steer' else 'Working...')
        return identity
    def command(self,text):
        command,_,rest=text.partition(' ');rest=rest.strip()
        if command in ('/exit','/quit'):return False
        if command in ('/work','/plan','/chat'):
            self.mode=command[1:]
            self.notify({'work':'Work mode: I can edit and test this project.',
                'plan':'Plan mode: I can inspect and explain; files stay unchanged.',
                'chat':'Conversation mode: ask a question or discuss the project.'}[self.mode])
        elif command in ('/stop','/cancel'):self.service.stop()
        elif command=='/help':
            self.notify('Describe what you want in ordinary words. Keep typing while I work.\n'
                'Enter steers current work; Tab queues one combined next turn; Esc stops.\n'
                '/plan  /work  /chat  /aside QUESTION  /history WORDS\n'
                '/edit [NUMBER] NEW REQUEST  /explore [NUMBER] NEW REQUEST  /switch NUMBER\n'
                '/preview [PAGE.html|REPORT.pdf|FILE.txt]  /continue  /exit. Alt-Enter adds a line; Ctrl-R searches prompts.\n'
                'Edit replaces an earlier Work request. Explore keeps these files and uses older context in a separate copy. Switch restores matching files and context.')
        elif command=='/history':
            rows=self.service.snapshot.get('history',[])
            for number,row in enumerate(rows,1):
                message=row['input']['message']
                if not rest or rest.casefold() in message.casefold():
                    status=(row.get('result') or {}).get('status','working')
                    self.notify(str(number)+'  '+row['input']['mode']+'  '+status+'  '+message)
            if not rows:self.notify('No saved turns yet.')
        elif command=='/preview':
            selected=self.service.snapshot.get('current',{}).get('file_commit')
            if not selected:
                self.notify('No saved website or document yet. Ask me to make something first.');return True
            versions=WorkspaceVersions(self.service.project,self.state/'files')
            url=self.preview.show(versions,selected,document=rest or None)
            self.notify(instructions(url,self.preview.port))
        elif command in ('/aside','/edit','/explore','/switch','/continue'):
            if command in ('/edit','/explore','/switch') and self.mode!='work':
                self.notify('Switch to /work before changing saved file versions.');return True
            if command=='/continue' and self.mode!='work' and self.service.snapshot.get('current',{}).get('mode')=='work':
                self.notify('Switch to /work before continuing a workflow that can edit files.');return True
            mode={'/switch':'select'}.get(command,command[1:])
            if not rest and command!='/continue':
                self.notify('Add a question or saved turn after '+command);return True
            self.service.submit(rest or command[1:],mode=mode,kind='queue')
            self.notify('Saved '+command[1:]+' request.')
        else:self.notify('Unknown command. Type /help; nothing was sent.')
        return True
    async def run(self):
        self.loop=asyncio.get_running_loop()
        # TERM=unknown/dumb prints its prompt before prompt-toolkit enters
        # raw mode. Arm input first so an immediate Ctrl+D is not swallowed
        # by the terminal's cooked line discipline before the reader attaches.
        with patch_stdout(), self.prompt.input.raw_mode():
            self.service.start(self.notify)
            self.notify('BranchWrite: keep talking while I work. /help shows the keys.\n'
                        'Work edits this project. /explore tries an idea in a separate copy.')
            try:
                while True:
                    try:text=(await self.prompt.prompt_async('You> ')).strip()
                    except EOFError:break
                    if not text:continue
                    try:
                        if text.startswith('/'):
                            if not self.command(text):break
                        else:self._submit(text,'steer' if self.service.running else 'send')
                    except (ValueError,OSError,RuntimeError) as error:self.notify('Could not submit: '+str(error))
            finally:
                self.service.stop()
                self.notify('Settling current work and saving session state...')
                try:await asyncio.to_thread(self.service.close)
                finally:await asyncio.to_thread(self.preview.close)
        return 0
